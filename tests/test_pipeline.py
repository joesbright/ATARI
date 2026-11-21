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
import ast
import os
import re
import shutil
from pathlib import Path

import pytest

pytest.importorskip('casacore', reason='python-casacore is not installed')

from casacore.tables import table  # noqa: E402  (needs casacore)

from atari.pipeline import main  # noqa: E402  (needs casacore)

DATA = Path(__file__).parent / 'data'
UVH5 = DATA / 'uvh5'
TEST_MS = DATA / 'master_ms.ms'
EXPECTED = DATA / 'expected'
OUTPUTS = ['1GC_.py', '1GC_.sh', 'image_.sh']

# Generated scripts contain absolute paths to the data. They are replaced
# with this placeholder so the comparison works in any folder.
PLACEHOLDER = '{WORKDIR}'

# Set ATARI_CASAPATH if casa is not on the PATH under that name (e.g. it is a
# shell alias, which other programs cannot see).
CASA = os.environ.get('ATARI_CASAPATH') or shutil.which('casa')


def generated(workdir, name):
    text = (workdir / name).read_text()
    if name == '1GC_.py':
        # 1GC_.py runs each split's own calibration script (<split>/1GC.py) in
        # turn. Rebuild the full recipe from them, so that the comparison with
        # expected/1GC_.py checks the calibration commands themselves.
        lines = []
        for line in text.splitlines(keepends=True):
            run = re.fullmatch(r"exec\(open\('(.+)'\)\.read\(\)\)\n", line)
            lines.append(Path(run.group(1)).read_text() if run else line)
        text = ''.join(lines)
    if name == '1GC_.sh':
        # The CASA path differs between the two routes (--casapath).
        text = re.sub(r'^CASA=.*$', 'CASA={CASA}', text, flags=re.M)
    return text


def check_outputs(workdir, datadir):
    for name in OUTPUTS:
        actual = generated(workdir, name).replace(str(datadir), PLACEHOLDER)
        if os.environ.get('ATARI_UPDATE_EXPECTED'):
            EXPECTED.mkdir(exist_ok=True)
            (EXPECTED / name).write_text(actual)
        assert actual == (EXPECTED / name).read_text(), name


def assert_no_unflagged_zeros(folder):
    # Dead antennas, feeds and LOs are recorded as exact zeros; they must be
    # flagged before calibration, or they count as measurements.
    splits = sorted(folder.glob('*_spw[0-9]/*_spw[0-9].ms'))
    assert splits
    for split in splits:
        with table(str(split), ack=False) as t:
            unflagged_zeros = ((t.getcol('DATA') == 0) & ~t.getcol('FLAG')).sum()
        assert unflagged_zeros == 0, split.name


@pytest.mark.skipif(not TEST_MS.exists(), reason='tests/data/master_ms.ms is missing')
def test_setup_from_measurement_set(tmp_path, monkeypatch):
    # The pipeline edits the measurement set and writes folders beside it,
    # so work on a copy.
    ms = tmp_path / TEST_MS.name
    shutil.copytree(TEST_MS, ms)
    monkeypatch.chdir(tmp_path)

    main([str(ms), '--casapath', 'casa', '--refant', '3'])

    check_outputs(tmp_path, tmp_path)
    assert_no_unflagged_zeros(tmp_path)

    # Each split has its own calibration script, so the splits can be
    # calibrated in parallel (1GC_.sh); 1GC_.py only runs them one by one.
    split_scripts = sorted(tmp_path.glob('*_spw[0-9]/1GC.py'))
    assert len(split_scripts) == len(sorted(tmp_path.glob('*_spw[0-9]/*_spw[0-9].ms'))) > 0
    runs = [line for line in (tmp_path / '1GC_.py').read_text().splitlines()
            if line and not line.startswith(('import', '#'))]
    assert runs == ["exec(open('%s').read())" % path for path in split_scripts]
    assert all(str(path) in (tmp_path / '1GC_.sh').read_text() for path in split_scripts)

    # The old "u=0" clip (each field's calibrated amplitudes above their 99th
    # percentile) flagged nothing on 2026-09-18 p060, would bias bright
    # calibrators if it did, and is covered by flagging the corrected data.
    script = (tmp_path / '1GC_.py').read_text()
    assert "mode='clip'" not in script
    assert 'tb.open' not in script


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


def add_second_flux_calibrator(ms, name='3C147'):
    # Many tracks observe a flux calibrator at each end (e.g. 3C48 then
    # 3C147). Make such an observation from the test MS by adding a copy of
    # its 3c48 scan, renamed, after the last scan: enough to check which
    # fields atari-setup selects and what it writes, not to calibrate.
    with table(str(ms), readonly=False, ack=False) as t:
        last = t.getcol('TIME').max()
        scan = t.query('FIELD_ID == 0')
        scan.copy(str(ms) + '_scan', deep=True).close()
        scan.close()
        copy = table(str(ms) + '_scan', readonly=False, ack=False)
        new_field = table(str(ms) + '/FIELD', ack=False).nrows()
        shift = last - copy.getcol('TIME').min() + 600  # 10 min after the target
        copy.putcol('TIME', copy.getcol('TIME') + shift)
        copy.putcol('TIME_CENTROID', copy.getcol('TIME_CENTROID') + shift)
        copy.putcol('FIELD_ID', [new_field] * copy.nrows())
        copy.putcol('SCAN_NUMBER', [t.getcol('SCAN_NUMBER').max() + 1] * copy.nrows())
        copy.copyrows(t)
        copy.close()
    shutil.rmtree(str(ms) + '_scan')
    with table(str(ms) + '/FIELD', readonly=False, ack=False) as f:
        source_id = f.getcol('SOURCE_ID').max() + 1
        f.copyrows(f, startrowin=0, nrow=1)
        f.putcell('NAME', f.nrows() - 1, name)
        f.putcell('SOURCE_ID', f.nrows() - 1, source_id)
    with table(str(ms) + '/SOURCE', readonly=False, ack=False) as s:
        rows = [i for i, sid in enumerate(s.getcol('SOURCE_ID')) if sid == 0]
        for i in rows:
            s.copyrows(s, startrowin=i, nrow=1)
            s.putcell('NAME', s.nrows() - 1, name)
            s.putcell('SOURCE_ID', s.nrows() - 1, source_id)
    return new_field


def casa_calls(script):
    # The CASA task calls in a generated script, in order, as
    # (task, {argument: value}).
    calls = []
    for statement in ast.parse(script.read_text()).body:
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            call = statement.value
            calls.append((call.func.id, {k.arg: ast.literal_eval(k.value) for k in call.keywords}))
    return calls


def field_set(selection):
    # A CASA field selection ('3c48,3C147' or a list) as a set of names.
    if isinstance(selection, str):
        selection = selection.split(',')
    return {name.strip() for name in selection if name.strip()}


@pytest.mark.skipif(not TEST_MS.exists(), reason='tests/data/master_ms.ms is missing')
def test_two_flux_calibrators_are_both_used(tmp_path, monkeypatch):
    # Issue #44. With a flux calibrator at each end of the track, both must be
    # in every split, both given their own model, and both used for the
    # bandpass (one solution per scan, interpolated in time), gains and flux
    # scale; each is imaged so it can be checked against its model.
    ms = tmp_path / TEST_MS.name
    shutil.copytree(TEST_MS, ms)
    second = add_second_flux_calibrator(ms)
    monkeypatch.chdir(tmp_path)

    main([str(ms), '--casapath', 'casa', '--refant', '3'])

    flux = {'3c48', '3C147'}
    gain = '0038+416'
    # Every problem is collected, so one run shows the whole picture.
    problems = []
    splits = sorted(tmp_path.glob('*_spw[0-9]/*_spw[0-9].ms'))
    assert splits
    for split in splits:
        name = split.parent.name
        with table(str(split), ack=False) as t:
            ids = set(t.getcol('FIELD_ID'))
        with table(str(split) + '/FIELD', ack=False) as f:
            present = {f.getcol('NAME')[i] for i in ids}
        if not flux <= present:
            problems.append(name + ': split has fields ' + str(sorted(present)))

        calls = casa_calls(split.parent / '1GC.py')
        setjy = set().union(*[field_set(a['field']) for task, a in calls if task == 'setjy'])
        if setjy != flux:
            problems.append(name + ': setjy on ' + str(sorted(setjy)))
        for task, a in calls:
            if task in ('gaincal', 'bandpass') and field_set(a['field']) != {gain} and field_set(a['field']) != flux:
                problems.append(name + ': ' + task + ' (' + os.path.basename(a['caltable']) + ') solved on '
                                + str(sorted(field_set(a['field']))))
        for task, a in calls:
            if task == 'fluxscale' and field_set(a['reference']) != flux:
                problems.append(name + ': fluxscale reference ' + str(sorted(field_set(a['reference']))))
        for source in flux:
            if not any(task == 'applycal' and a['field'] == source and a['gainfield'][0] == source
                       for task, a in calls):
                problems.append(name + ': no applycal of ' + source + ' with its own solutions')

    image = (tmp_path / 'image_.sh').read_text()
    for split in splits:
        line = re.search(r'^wsclean .*-name ' + re.escape(str(split.parent)) + r'/IMAGES/3C147_automask .*$',
                         image, flags=re.M)
        if not line or ' -field ' + str(second) + ' ' not in line.group(0):
            problems.append(split.parent.name + ': 3C147 not imaged')

    assert not problems, '\n'.join(problems)


@pytest.mark.skipif(CASA is None or shutil.which('aoflagger') is None,
                    reason='needs CASA and aoflagger (set ATARI_CASAPATH if casa is an alias)')
def test_setup_from_uvh5(tmp_path, monkeypatch, capfd):
    data = tmp_path / 'uvh5'
    shutil.copytree(UVH5, data)
    monkeypatch.chdir(tmp_path)

    main([str(data), '--casapath', CASA, '--refant', '3'])

    # Beside the combined MS, inside the uvh5 folder; nothing in the folder
    # atari-setup was run from.
    check_outputs(data, data)
    assert_no_unflagged_zeros(data)
    assert [p.name for p in tmp_path.iterdir()] == ['uvh5']

    # CASA, aoflagger and pyuvdata write to log files, not the terminal.
    captured = capfd.readouterr()
    terminal = captured.out + captured.err
    assert '\tINFO\t' not in terminal  # CASA log lines
    assert 'phased-up' not in terminal  # pyuvdata's warning, once per file
    logs = data / 'logs'
    # Each LO is combined, flagged and averaged on its own (in parallel, issue
    # #40), then the averaged LOs are combined into the final MS.
    names = ['atari_setup.log', 'casa_combine.log']
    for lo in ['LoA', 'LoB', 'LoC', 'LoD']:
        names += ['casa_concat_' + lo + '.log', 'aoflagger_' + lo + '.log', 'casa_average_' + lo + '.log']
    for name in names:
        assert (logs / name).stat().st_size > 0, name
    # Once per conversion process, not once per file.
    assert 1 <= (logs / 'atari_setup.log').read_text().count('phased-up') <= os.cpu_count()
    assert 'virtualenv' not in (logs / 'casa_concat_LoA.log').read_text()
    assert not list(data.glob('*_tmp*.ms')), 'temporary per-LO measurement sets left behind'
    # The final measurement set is named after the first scan's MJD and the
    # target, and the converted per-scan, per-LO files it was combined from
    # are deleted.
    assert (data / '61317_AT2026yeh.ms').is_dir()
    assert not (data / 'master_ms.ms').exists()
    assert not list(data.glob('uvh5_*_Lo?.ms'))
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
