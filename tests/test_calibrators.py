from atari.calibrators import match_calibrators


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
