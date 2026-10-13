import pytest

from atari.calibrators import calibrator_problems, classify_field, match_calibrators


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


@pytest.mark.parametrize('name', ['3c48', '3C48', '3c286', '3C286', '3c147', '3C147'])
def test_flux_calibrators_are_matched_in_any_case(name):
    # The p060 2026-10-11 observation names its flux calibrator 3C48.
    assert classify_field(name) == 'FLUX_CAL'


def test_only_exact_flux_calibrator_names_are_matched():
    assert classify_field('3C48_offset') != 'FLUX_CAL'


def test_no_problems_with_flux_and_gain_calibrators():
    assert calibrator_problems(['3C48', '0038+416', 'AT2026yeh']) == []


def test_missing_flux_calibrator_is_a_problem():
    problems = calibrator_problems(['0038+416', 'AT2026yeh'])
    assert len(problems) == 1
    assert 'flux calibrator' in problems[0]


def test_missing_gain_calibrator_is_a_problem():
    problems = calibrator_problems(['3c48', 'AT2026yeh'])
    assert len(problems) == 1
    assert '--calibrators' in problems[0]


def test_gain_calibrator_from_extra_file_counts(tmp_path):
    extra = tmp_path / 'my_calibrators.dat'
    extra.write_text('my_gaincal\n')
    assert calibrator_problems(['3c48', 'my_gaincal', 'AT2026yeh'], str(extra)) == []
