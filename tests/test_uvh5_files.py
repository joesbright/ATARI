import glob
from pathlib import Path

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
