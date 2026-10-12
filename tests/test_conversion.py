"""Test the first stage of the uvh5 route: converting each LO of each scan
to a measurement set with pyuvdata, then fix_scans.fix_spw. This is the part
most likely to break when pyuvdata changes. It needs python-casacore."""
import glob
import shutil
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip('casacore', reason='python-casacore is not installed')

from casacore.tables import table  # noqa: E402
from atari.pipeline import find_time_ids, parallel_file_conversion  # noqa: E402

UVH5 = Path(__file__).parent / 'data' / 'uvh5'

SCANS = {
    # time ID: field name
    '61317_11988_5522216': '3c48',
    '61317_13265_5561187': '0038+416',
    '61317_13928_5581420': 'AT2026yeh',
}

# Number of channels and lowest frequency (MHz) of each LO in the test data.
# LoD has 5 tunings, the others 7, with 32 channels kept per tuning.
LOS = {'LoA': (224, 2704.0), 'LoB': (224, 4704.0), 'LoC': (224, 6704.0), 'LoD': (160, 8704.0)}


def test_find_time_ids_lists_each_scan_once():
    # Each scan has 7 LoC tuning folders. Listing a scan once per file made
    # several workers convert it at the same time and crash.
    assert find_time_ids(str(UVH5)) == sorted(SCANS)


@pytest.fixture(scope='module')
def converted(tmp_path_factory):
    """Convert a copy of the test observation once and share it between the
    tests in this file, since conversion is the slow part."""
    data = tmp_path_factory.mktemp('conversion') / 'uvh5'
    shutil.copytree(UVH5, data)
    for timeid in SCANS:
        parallel_file_conversion(timeid, str(data))
    return data


def ms_path(data, timeid, lo):
    scans = glob.glob(str(data / ('uvh5*' + timeid + '*0001')))
    assert len(scans) == 1
    return scans[0] + '_' + lo + '.ms'


@pytest.mark.parametrize('timeid', SCANS)
@pytest.mark.parametrize('lo', LOS)
def test_one_measurement_set_per_scan_and_lo(converted, timeid, lo):
    ms = ms_path(converted, timeid, lo)
    nchan, fmin = LOS[lo]

    with table(ms + '/FIELD') as t:
        assert list(t.getcol('NAME')) == [SCANS[timeid]]
    with table(ms + '/SPECTRAL_WINDOW') as t:
        assert list(t.getcol('NUM_CHAN')) == [nchan]
        assert t.getcol('CHAN_FREQ').min() / 1e6 == pytest.approx(fmin)
    with table(ms + '/SOURCE') as t:
        # fix_spw sets every source's spectral window to 0, so the LOs can
        # be concatenated later.
        assert np.all(t.getcol('SPECTRAL_WINDOW_ID') == 0)
    with table(ms) as t:
        antennas = np.union1d(t.getcol('ANTENNA1'), t.getcol('ANTENNA2'))
        assert len(antennas) == 6
        assert len(np.unique(t.getcol('TIME'))) == 3


def test_conversion_skips_existing_measurement_sets(converted):
    # parallel_file_conversion only converts LOs whose MS does not exist yet,
    # so a re-run after an interruption does not redo finished work.
    ms = ms_path(converted, '61317_11988_5522216', 'LoA')
    marker = Path(ms) / 'not_overwritten'
    marker.touch()
    parallel_file_conversion('61317_11988_5522216', str(converted))
    assert marker.exists()
