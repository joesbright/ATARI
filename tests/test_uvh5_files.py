import glob
import shutil
from pathlib import Path

import numpy as np
import pytest

from atari import uvh5_files

UVH5 = Path(__file__).parent / 'data' / 'uvh5'


def test_find_time_ids_lists_each_scan_once():
    # Each scan has 7 LoC tuning folders. Listing a scan once per file made
    # several workers convert it at the same time and crash.
    assert uvh5_files.find_time_ids(str(UVH5)) == [
        '61317_11988_5522216', '61317_13265_5561187', '61317_13928_5581420']


def test_converted_ms_are_listed_in_a_fixed_order(tmp_path, monkeypatch):
    # CASA concat numbers spectral windows in the order it receives the LOs
    # of each scan, so the order must not depend on how the filesystem lists
    # files. Make glob return them reversed, which a filesystem might do.
    names = ['uvh5_61317_11988_5522216_3c48_0001_Lo' + lo + '.ms' for lo in 'ABCD']
    for name in names:
        (tmp_path / name).mkdir()
    real_glob = glob.glob
    monkeypatch.setattr(glob, 'glob', lambda pattern: sorted(real_glob(pattern), reverse=True))

    found = uvh5_files.find_converted_ms(str(tmp_path))

    assert [Path(p).name for p in found] == names


def test_find_time_ids_skips_stay_put_scans(tmp_path):
    # Issue #5: Stay_put scans are recorded while the sources are below the
    # horizon, so they are not converted at all. The field name can contain
    # underscores, so it is everything between the time ID and the _0001.
    for scan in ['uvh5_61317_11988_5522216_3c48_0001',
                 'uvh5_61317_53798_6798156_Stay_put_0001']:
        tuning = tmp_path / scan / 'LoC.C0352'
        tuning.mkdir(parents=True)
        (tuning / (scan + '.uvh5')).touch()

    assert uvh5_files.find_time_ids(str(tmp_path)) == ['61317_11988_5522216']


def test_tuning_files_are_listed_in_a_fixed_order(tmp_path, monkeypatch):
    # Issue #12: the tunings of one LO are passed to pyuvdata together, so
    # list them in a fixed order rather than the filesystem's.
    folder = tmp_path / 'uvh5_61317_11988_5522216_3c48_0001'
    names = []
    for tuning in ['LoA.C0352', 'LoA.C0544', 'LoA.C0736']:
        (folder / tuning).mkdir(parents=True)
        (folder / tuning / (folder.name + '.uvh5')).touch()
        names.append(tuning)
    (folder / 'LoB.C0352').mkdir()
    (folder / 'LoB.C0352' / (folder.name + '.uvh5')).touch()
    real_glob = glob.glob
    monkeypatch.setattr(glob, 'glob', lambda pattern: sorted(real_glob(pattern), reverse=True))

    found = uvh5_files.find_tuning_files(str(folder) + '/', 'LoA')

    assert [Path(p).parent.name for p in found] == names


TUNINGS = ['C0352', 'C0544', 'C0736', 'C0928', 'C1120', 'C1312', 'C1504']
SCAN = 'uvh5_61317_13928_5581420_AT2026yeh_0001'


def test_observation_tunings_are_found_across_all_los():
    # LoD has only 5 tunings in the test data, but the other LOs have all 7
    # and every LO uses the same tuning names.
    assert uvh5_files.observation_tunings(str(UVH5)) == TUNINGS


def tuning_flags(uvd, tunings, channels_per_tuning=32):
    """For each tuning in frequency order, whether all its data is flagged."""
    flags = uvd.flag_array.all(axis=(0, 2))
    return [bool(flags[i * channels_per_tuning:(i + 1) * channels_per_tuning].all())
            for i in range(len(tunings))]


def test_tunings_missing_from_the_whole_observation_are_filled_with_flags():
    # Issue #10: LoD lacks C0544 and C0736 in every scan, so it had fewer
    # channels than the other LOs and CASA concat crashed.
    lod = uvh5_files.read_lo(str(UVH5 / SCAN) + '/', 'LoD', TUNINGS)
    loa = uvh5_files.read_lo(str(UVH5 / SCAN) + '/', 'LoA', TUNINGS)

    assert lod.Nfreqs == loa.Nfreqs == 7 * 32
    # The filled tunings sit where LoD's C0544 and C0736 would be: the same
    # offsets from C0352 as in LoA.
    assert np.allclose(lod.freq_array - lod.freq_array[0], loa.freq_array - loa.freq_array[0])
    assert tuning_flags(lod, TUNINGS) == [False, True, True, False, False, False, False]
    assert np.all(lod.data_array[:, 32:96] == 0)
    assert np.all(lod.nsample_array[:, 32:96] == 0)


def test_tuning_dropped_partway_through_is_filled_with_flags(tmp_path):
    # Issue #11: a recording node dropping out partway through leaves one
    # scan without a tuning the others have. CASA then made a new spectral
    # window for that scan. Filling it keeps the layout identical.
    data = tmp_path / 'uvh5'
    shutil.copytree(UVH5, data)
    shutil.rmtree(data / SCAN / 'LoA.C0736')
    tunings = uvh5_files.observation_tunings(str(data))

    dropped = uvh5_files.read_lo(str(data / SCAN) + '/', 'LoA', tunings)
    complete = uvh5_files.read_lo(str(UVH5 / SCAN) + '/', 'LoA', TUNINGS)

    assert np.allclose(dropped.freq_array, complete.freq_array)
    assert np.allclose(dropped.channel_width, complete.channel_width)
    assert tuning_flags(dropped, TUNINGS) == [False, False, True, False, False, False, False]
    # The data of the tunings that were recorded is unchanged.
    kept = np.r_[0:64, 96:224]
    assert np.array_equal(dropped.data_array[:, kept], complete.data_array[:, kept])


def test_lo_that_was_not_recorded_is_skipped(tmp_path):
    data = tmp_path / 'uvh5'
    shutil.copytree(UVH5, data)
    for tuning in (data / SCAN).glob('LoB.*'):
        shutil.rmtree(tuning)

    assert uvh5_files.read_lo(str(data / SCAN) + '/', 'LoB', TUNINGS) is None


@pytest.mark.parametrize('dropped', [
    ['C0352'],                                       # start
    ['C1504'],                                       # end
    ['C0928'],                                       # middle
    ['C0352', 'C1504'],                              # start and end
    ['C0352', 'C0544', 'C1312', 'C1504'],            # both ends, two deep
    ['C0544', 'C0928', 'C1312'],                     # scattered
    ['C0352', 'C0736', 'C1120', 'C1504'],            # alternating, from the start
    ['C0352', 'C0544', 'C0736', 'C0928', 'C1120', 'C1312'],  # all but the last
    ['C0544', 'C0736', 'C0928', 'C1120', 'C1312', 'C1504'],  # all but the first
])
def test_missing_tunings_are_filled_at_their_true_frequencies(tmp_path, dropped):
    # Delete tunings from a complete LO, fill them, and compare with the
    # complete LO: the filled tunings must have exactly the frequencies the
    # real ones had, wherever the gaps are.
    scan = tmp_path / SCAN
    shutil.copytree(UVH5 / SCAN, scan)
    for tuning in dropped:
        shutil.rmtree(scan / ('LoA.' + tuning))

    filled = uvh5_files.read_lo(str(scan) + '/', 'LoA', TUNINGS)
    complete = uvh5_files.read_lo(str(UVH5 / SCAN) + '/', 'LoA', TUNINGS)

    assert np.array_equal(filled.freq_array, complete.freq_array)
    assert np.array_equal(filled.channel_width, complete.channel_width)
    assert tuning_flags(filled, TUNINGS) == [t in dropped for t in TUNINGS]
    kept = np.concatenate([np.arange(i * 32, (i + 1) * 32)
                           for i, t in enumerate(TUNINGS) if t not in dropped])
    assert np.array_equal(filled.data_array[:, kept], complete.data_array[:, kept])
    assert np.array_equal(filled.flag_array[:, kept], complete.flag_array[:, kept])


def test_tuning_whose_name_does_not_match_its_frequencies_is_an_error(tmp_path):
    # Missing tunings are placed using the tuning names, so check the names
    # against the recorded frequencies rather than fill in the wrong place.
    scan = tmp_path / SCAN
    shutil.copytree(UVH5 / SCAN, scan)
    shutil.rmtree(scan / 'LoA.C0736')
    (scan / 'LoA.C0544').rename(scan / 'LoA.C0560')

    with pytest.raises(ValueError, match='LoA.C0560'):
        uvh5_files.read_lo(str(scan) + '/', 'LoA', TUNINGS + ['C0560'])
