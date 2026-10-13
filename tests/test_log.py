"""Tests for atari.log: key messages go to the terminal, everything goes to
the log file, and external programs' output goes to their own log files.
Needs no casacore."""
import logging
import warnings

import pytest

from atari import log


@pytest.fixture
def logdir(tmp_path):
    yield tmp_path / 'logs'
    log.close_logging()


def test_terminal_shows_key_messages_and_file_has_everything(logdir, capsys):
    logfile = log.setup_logging(logdir)
    log.logger.info('Flux calibrator: 3c48')
    log.logger.debug('Cell size for spw0: 9.52 arcsec')

    out = capsys.readouterr().out
    assert 'Flux calibrator: 3c48' in out
    assert '9.52' not in out
    text = logfile.read_text()
    assert 'Flux calibrator: 3c48' in text
    assert 'Cell size for spw0: 9.52 arcsec' in text


def test_verbose_shows_details_in_the_terminal(logdir, capsys):
    log.setup_logging(logdir, verbose=True)
    log.logger.debug('Cell size for spw0: 9.52 arcsec')

    assert 'Cell size for spw0: 9.52 arcsec' in capsys.readouterr().out


def test_warnings_and_errors_are_labelled(logdir, capsys):
    log.setup_logging(logdir)
    log.logger.warning('Field X has no gain calibrator.')
    log.logger.error('Reference antenna 9z is not in the measurement set.')

    out = capsys.readouterr().out
    assert 'Warning: Field X has no gain calibrator.' in out
    assert 'Error: Reference antenna 9z is not in the measurement set.' in out


def test_other_libraries_only_go_to_the_file(logdir, capsys):
    # e.g. pyuvdata's warnings about the old phasing method, one per file.
    logfile = log.setup_logging(logdir)
    warnings.warn('The data are phased-up using the old phase method')
    logging.getLogger('pyuvdata').warning('Telescope ATA is not in known_telescopes')

    captured = capsys.readouterr()
    assert 'phased-up' not in captured.out + captured.err
    assert 'known_telescopes' not in captured.out + captured.err
    text = logfile.read_text()
    assert 'phased-up' in text
    assert 'known_telescopes' in text


def test_a_rerun_starts_a_new_log(logdir):
    log.setup_logging(logdir)
    log.logger.info('first run')
    logfile = log.setup_logging(logdir)
    log.logger.info('second run')

    text = logfile.read_text()
    assert 'first run' not in text
    assert text.count('second run') == 1


def test_worker_processes_log_to_the_file(logdir, capsys):
    # Pool workers (uvh5 conversion) only write to the log file.
    logfile = log.setup_logging(logdir)
    log.setup_worker(logfile)
    warnings.warn('The data are phased-up using the old phase method')
    log.logger.info('Converted LoA')

    captured = capsys.readouterr()
    assert captured.out + captured.err == ''
    text = logfile.read_text()
    assert 'phased-up' in text
    assert 'Converted LoA' in text


def test_run_sends_program_output_to_its_log(logdir, capfd):
    log.setup_logging(logdir)
    steplog = logdir / 'casa_concat.log'
    log.run('echo lots of CASA output', steplog, 'Combining spectral chunks')

    out = capfd.readouterr().out
    assert 'Combining spectral chunks' in out
    assert 'lots of CASA output' not in out
    assert 'lots of CASA output' in steplog.read_text()


def test_run_stops_if_the_program_fails(logdir, capfd):
    log.setup_logging(logdir)
    steplog = logdir / 'aoflagger.log'
    with pytest.raises(SystemExit):
        log.run('echo something broke; exit 3', steplog, 'Flagging with aoflagger')

    out = capfd.readouterr().out
    assert 'Flagging with aoflagger failed' in out
    assert 'something broke' in out  # the end of the log
    assert str(steplog) in out


def test_run_stops_if_the_output_is_missing(logdir, tmp_path, capfd):
    # CASA exits normally even when a task fails, so check what it made.
    log.setup_logging(logdir)
    missing = tmp_path / 'master_ms_tmp.ms'
    with pytest.raises(SystemExit):
        log.run('true', logdir / 'casa_concat.log', 'Combining spectral chunks', outputs=[missing])

    assert str(missing) in capfd.readouterr().out


def test_repeated_warnings_are_logged_once(logdir):
    # pyuvdata warns about the old phasing method for every file it reads.
    logfile = log.setup_logging(logdir)
    with warnings.catch_warnings():
        warnings.simplefilter('always')
        for _ in range(5):
            warnings.warn('The data are phased-up using the old phase method')
    warnings.warn('A different warning')

    text = logfile.read_text()
    assert text.count('phased-up') == 1
    assert 'A different warning' in text


def test_warnings_say_what_and_where(logdir, monkeypatch):
    # pyuvdata replaces warnings.formatwarning with one that leaves out the
    # category and where the warning came from.
    monkeypatch.setattr(warnings, 'formatwarning', lambda message, *args, **kwargs: str(message) + '\n')
    logfile = log.setup_logging(logdir)
    warnings.warn('invalid value encountered in power', RuntimeWarning)

    line = [line for line in logfile.read_text().splitlines() if 'power' in line][0]
    assert 'RuntimeWarning: invalid value encountered in power (' in line
    assert 'test_log.py:' in line


def test_run_hides_the_virtual_environment(logdir, monkeypatch):
    # uv run sets VIRTUAL_ENV, which CASA's own Python (IPython) warns about.
    monkeypatch.setenv('VIRTUAL_ENV', '/home/user/ATARI/.venv')
    log.setup_logging(logdir)
    steplog = logdir / 'casa_concat.log'
    log.run('echo "VIRTUAL_ENV=[$VIRTUAL_ENV]"', steplog, 'Combining spectral chunks')

    assert 'VIRTUAL_ENV=[]' in steplog.read_text()
