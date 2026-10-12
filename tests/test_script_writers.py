"""Tests for the code that writes the CASA (1GC_.py) and WSClean (image_.sh)
scripts. These build commands by joining strings, so the main risks are
broken quoting and steps in the wrong order."""
import ast

from atari import fgc, write_casa_scripts


def casa_calls(script):
    """Parse a generated CASA script and return its top-level calls as
    (task name, {argument: value}) pairs. Parsing fails if the quoting is
    broken, so a successful parse is itself part of the test."""
    calls = []
    for node in ast.parse(script.read_text()).body:
        # Only CASA task calls such as gaincal(...), not methods like tb.close().
        if (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)):
            kwargs = {kw.arg: literal_or_source(kw.value) for kw in node.value.keywords}
            calls.append((node.value.func.id, kwargs))
    return calls


def literal_or_source(node):
    """The argument's value if it is a constant, otherwise its source text
    (e.g. clipminmax=[0,myclipmax] refers to a variable in the script)."""
    try:
        return ast.literal_eval(node)
    except ValueError:
        return ast.unparse(node)


def test_first_generation_calibration_recipe(tmp_path):
    script = tmp_path / '1GC_.py'
    fgc.write_dependencies(str(script))
    fgc.first_generation_calibration('/obs/target_spw0.ms', 'target', '3c286',
                                     '1331+305', '5', str(script), '/obs/CALIBRATION_TABLES/')

    calls = casa_calls(script)
    assert [name for name, _ in calls] == [
        'flagdata', 'flagdata',              # tfcrop, rflag
        'setjy',
        'gaincal', 'gaincal', 'bandpass',    # G0, K0, B0
        'gaincal', 'gaincal',                # G1 on flux cal, then phase cal
        'fluxscale',
        'applycal', 'applycal', 'applycal',  # flux cal, phase cal, target
        'flagdata', 'flagdata',
    ]

    for name, kwargs in calls:
        assert kwargs['vis'] == '/obs/target_spw0.ms'
        if name in ('gaincal', 'bandpass'):
            assert kwargs['refant'] == '5'
            assert kwargs['caltable'].startswith('/obs/CALIBRATION_TABLES/')

    applied = [kwargs['field'] for name, kwargs in calls if name == 'applycal']
    assert applied == ['3c286', '1331+305', 'target']


def test_flag_u0_script_is_valid_python(tmp_path):
    script = tmp_path / '1GC_.py'
    fgc.flag_u0(['/obs/a.ms', '/obs/b.ms'], str(script))

    clips = [kwargs for name, kwargs in casa_calls(script) if name == 'flagdata']
    # One clip per field (IDs 0-2) per measurement set.
    assert [(c['vis'], c['field']) for c in clips] == [
        ('/obs/a.ms', '0'), ('/obs/a.ms', '1'), ('/obs/a.ms', '2'),
        ('/obs/b.ms', '0'), ('/obs/b.ms', '1'), ('/obs/b.ms', '2'),
    ]


def test_image_all_fields_writes_one_wsclean_command_per_field(tmp_path):
    script = tmp_path / 'image_.sh'
    fgc.image_all_fields('/obs/target_spw0.ms', 2, 0, 1, 'target', '3c286', '1331+305',
                         str(script), 4096, 1.5, '/obs/IMAGES/')

    commands = [line.split() for line in script.read_text().splitlines()
                if not line.startswith('#')]
    assert len(commands) == 3
    for command, field, name in zip(commands, ['2', '0', '1'], ['target', '3c286', '1331+305']):
        assert command[0] == 'wsclean'
        assert command[command.index('-field') + 1] == field
        assert command[command.index('-name') + 1] == '/obs/IMAGES/' + name + '_automask'
        assert command[command.index('-size') + 1:command.index('-size') + 3] == ['4096', '4096']
        assert command[-1] == '/obs/target_spw0.ms'


def test_deep_image_combines_all_measurement_sets(tmp_path):
    script = tmp_path / 'image_.sh'
    fgc.deep_image(['/obs/a.ms', '/obs/b.ms'], 2, str(script), 4096, 1.5,
                   '/obs/DEEP_IMAGE/', 'target')

    command = script.read_text().split()
    assert command[0] == 'wsclean'
    assert command[-2:] == ['/obs/a.ms', '/obs/b.ms']


def test_flag_antennas_command_is_valid(tmp_path):
    # Issue #7: the path was written without quotes, so the command was not
    # valid Python and CASA never flagged anything.
    script = tmp_path / 'flag_command.py'
    write_casa_scripts.write_flag_antennas('/obs/master_ms.ms', '0,5', str(script))

    assert casa_calls(script) == [
        ('flagdata', {'vis': '/obs/master_ms.ms', 'mode': 'manual', 'antenna': '0,5'})]
