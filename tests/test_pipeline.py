"""Regression tests: run atari-setup on the small test observation and check
that the generated 1GC_.py and image_.sh match known-good copies in
tests/data/expected/. Those copies were made with the code as it was before
the package restructure, so any difference means behaviour has changed.

There are two routes into the pipeline:
- from the uvh5 files, which also needs CASA and aoflagger, so it only runs
  where they are installed (e.g. the ATA nodes);
- from tests/data/master_ms.ms, the measurement set the uvh5 route produces,
  which only needs python-casacore and also runs on GitHub Actions.
Both should produce the same scripts.

If a change is meant to alter the generated scripts, regenerate the copies
with
    ATARI_UPDATE_EXPECTED=1 uv run pytest tests/test_pipeline.py
and review the difference with `git diff tests/data/expected` before
committing it.
"""
import os
import shutil
from pathlib import Path

import pytest

pytest.importorskip('casacore', reason='python-casacore is not installed')

from atari.pipeline import main  # noqa: E402  (needs casacore)

DATA = Path(__file__).parent / 'data'
UVH5 = DATA / 'uvh5'
TEST_MS = DATA / 'master_ms.ms'
EXPECTED = DATA / 'expected'
OUTPUTS = ['1GC_.py', 'image_.sh']

# Generated scripts contain absolute paths to the data. They are replaced
# with this placeholder so the comparison works in any folder.
PLACEHOLDER = '{WORKDIR}'

# Set ATARI_CASAPATH if casa is not on the PATH under that name (e.g. it is a
# shell alias, which other programs cannot see).
CASA = os.environ.get('ATARI_CASAPATH') or shutil.which('casa')


def check_outputs(workdir, datadir):
    for name in OUTPUTS:
        actual = (workdir / name).read_text().replace(str(datadir), PLACEHOLDER)
        if os.environ.get('ATARI_UPDATE_EXPECTED'):
            EXPECTED.mkdir(exist_ok=True)
            (EXPECTED / name).write_text(actual)
        assert actual == (EXPECTED / name).read_text(), name


@pytest.mark.skipif(not TEST_MS.exists(), reason='tests/data/master_ms.ms is missing')
def test_setup_from_measurement_set(tmp_path, monkeypatch):
    # The pipeline edits the measurement set and writes folders beside it,
    # so work on a copy.
    ms = tmp_path / TEST_MS.name
    shutil.copytree(TEST_MS, ms)
    monkeypatch.chdir(tmp_path)

    main([str(ms), '--casapath', 'casa', '--refant', '3'])

    check_outputs(tmp_path, tmp_path)


@pytest.mark.skipif(not TEST_MS.exists(), reason='tests/data/master_ms.ms is missing')
def test_scripts_are_written_beside_the_data(tmp_path, monkeypatch):
    # Each dataset keeps its own scripts, next to logs/ and the per-target
    # folders, and the folder atari-setup is run from is left alone (here it
    # holds another dataset's script, which must survive).
    data = tmp_path / 'data'
    data.mkdir()
    ms = data / TEST_MS.name
    shutil.copytree(TEST_MS, ms)
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    (elsewhere / '1GC_.py').write_text('# another dataset\n')
    monkeypatch.chdir(elsewhere)

    main([str(ms), '--casapath', 'casa', '--refant', '3'])

    check_outputs(data, data)
    assert [p.name for p in elsewhere.iterdir()] == ['1GC_.py']
    assert (elsewhere / '1GC_.py').read_text() == '# another dataset\n'


@pytest.mark.skipif(not TEST_MS.exists(), reason='tests/data/master_ms.ms is missing')
def test_relative_data_path_gives_absolute_paths_in_scripts(tmp_path, monkeypatch):
    # The scripts are run from other folders than the one they are in, so
    # they need absolute paths even when atari-setup was given a relative one.
    data = tmp_path / 'data'
    data.mkdir()
    shutil.copytree(TEST_MS, data / TEST_MS.name)
    monkeypatch.chdir(tmp_path)

    main(['data/' + TEST_MS.name, '--casapath', 'casa', '--refant', '3'])

    check_outputs(data, data)


@pytest.mark.skipif(not TEST_MS.exists(), reason='tests/data/master_ms.ms is missing')
def test_existing_scripts_stop_the_run(tmp_path, monkeypatch, capfd):
    # A folder that already holds scripts holds an earlier run: stop before
    # doing anything, rather than delete its scripts.
    ms = tmp_path / TEST_MS.name
    shutil.copytree(TEST_MS, ms)
    (tmp_path / 'image_.sh').write_text('# earlier run\n')
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit):
        main([str(ms), '--casapath', 'casa', '--refant', '3'])

    assert 'already contains image_.sh' in capfd.readouterr().out
    assert (tmp_path / 'image_.sh').read_text() == '# earlier run\n'
    assert not (tmp_path / '1GC_.py').exists()
    assert not (tmp_path / 'DEEP_IMAGE').exists()


@pytest.mark.skipif(not TEST_MS.exists(), reason='tests/data/master_ms.ms is missing')
def test_terminal_shows_key_information_only(tmp_path, monkeypatch, capfd):
    ms = tmp_path / TEST_MS.name
    shutil.copytree(TEST_MS, ms)
    monkeypatch.chdir(tmp_path)

    main([str(ms), '--casapath', 'casa', '--refant', '3'])

    # capfd also catches what casacore's C++ code prints.
    captured = capfd.readouterr()
    terminal = captured.out + captured.err
    assert 'Flux calibrator: 3c48' in terminal
    assert 'Gain calibrator for AT2026yeh: 0038+416' in terminal
    assert 'Reference antenna: 1c (index 3)' in terminal
    assert 'Successful' not in terminal  # casacore's table-open messages
    assert 'No such file' not in terminal  # cleaning up a previous run
    logfile = tmp_path / 'logs' / 'atari_setup.log'
    assert 'Flux calibrator: 3c48' in logfile.read_text()


@pytest.mark.skipif(CASA is None or shutil.which('aoflagger') is None,
                    reason='needs CASA and aoflagger (set ATARI_CASAPATH if casa is an alias)')
def test_setup_from_uvh5(tmp_path, monkeypatch, capfd):
    data = tmp_path / 'uvh5'
    shutil.copytree(UVH5, data)
    monkeypatch.chdir(tmp_path)

    main([str(data), '--casapath', CASA, '--refant', '3'])

    # Beside master_ms.ms, inside the uvh5 folder; nothing in the folder
    # atari-setup was run from.
    check_outputs(data, data)
    assert [p.name for p in tmp_path.iterdir()] == ['uvh5']

    # CASA, aoflagger and pyuvdata write to log files, not the terminal.
    captured = capfd.readouterr()
    terminal = captured.out + captured.err
    assert '\tINFO\t' not in terminal  # CASA log lines
    assert 'phased-up' not in terminal  # pyuvdata's warning, once per file
    logs = data / 'logs'
    for name in ['atari_setup.log', 'casa_concat.log', 'aoflagger.log', 'casa_average.log']:
        assert (logs / name).stat().st_size > 0, name
    # Once per conversion process, not once per file.
    assert 1 <= (logs / 'atari_setup.log').read_text().count('phased-up') <= os.cpu_count()
    assert 'virtualenv' not in (logs / 'casa_concat.log').read_text()
    # CASA runs in logs/, so its <task>.last files land there.
    assert (logs / 'concat.last').exists()
    assert (logs / 'mstransform.last').exists()


def test_missing_flux_calibrator_stops_before_conversion(tmp_path, monkeypatch, capfd):
    # Found from the file names, so the slow conversion isn't run for nothing.
    data = tmp_path / 'uvh5'
    for name in ['uvh5_61325_20007_8530487_0038+416_0001', 'uvh5_61325_20679_8550994_AT2026yeh_0001']:
        tuning = data / name / 'LoC.C0352'
        tuning.mkdir(parents=True)
        (tuning / (name + '.uvh5')).touch()  # empty: reading it would fail
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit):
        main([str(data), '--refant', '3'])

    out = capfd.readouterr().out
    assert 'No flux calibrator' in out
    assert 'Fields found: 0038+416, AT2026yeh' in out
    assert not list(data.glob('*.ms'))
