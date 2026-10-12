import pytest

from atari.calibrators import classify_field, match_calibrators


def test_known_gain_calibrator_is_matched():
    assert match_calibrators('1331+305') is True


def test_unknown_source_is_not_matched():
    assert match_calibrators('my_target') is False


def test_extra_calibrators_file_is_added_to_builtin_list(tmp_path):
    extra = tmp_path / 'my_calibrators.dat'
    extra.write_text('my_gaincal\n')

    assert match_calibrators('my_gaincal') is False
    assert match_calibrators('my_gaincal', str(extra)) is True
    # The built-in list is still used alongside the extra file.
    assert match_calibrators('1331+305', str(extra)) is True


@pytest.mark.parametrize('name, kind', [
    ('3c48', 'FLUX_CAL'),
    ('1331+305', 'PHASE_CAL'),
    ('AT2026yeh', 'TARGET'),
])
def test_fields_are_classified(name, kind):
    assert classify_field(name) == kind


@pytest.mark.parametrize('name', ['Stay_put', 'stay_put', 'STAY_PUT'])
def test_stay_put_is_skipped(name):
    # Issue #5: Stay_put scans are recorded while the sources are below the
    # horizon, so they must not be calibrated or imaged as targets.
    assert classify_field(name) == 'SKIP'


def test_only_the_exact_stay_put_name_is_skipped():
    assert classify_field('Stay_put_field') == 'TARGET'
