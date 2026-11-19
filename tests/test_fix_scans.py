"""Tests of the in-place measurement set edits in atari.fix_scans."""
import shutil
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip('casacore', reason='python-casacore is not installed')

from casacore.tables import table  # noqa: E402  (needs casacore)

from atari import fix_scans  # noqa: E402

TEST_MS = Path(__file__).parent / 'data' / 'master_ms.ms'


@pytest.mark.skipif(not TEST_MS.exists(), reason='tests/data/master_ms.ms is missing')
def test_flag_zero_visibilities_flags_exactly_the_zeros(tmp_path):
    # Dead antennas, feeds and LOs are recorded as exact zeros but not
    # flagged; calibration and imaging would treat them as measurements.
    ms = tmp_path / TEST_MS.name
    shutil.copytree(TEST_MS, ms)
    with table(str(ms), ack=False) as t:
        data = t.getcol('DATA')
        before = t.getcol('FLAG')
    zero = data == 0
    assert (zero & ~before).any(), 'the test MS should have unflagged zeros'

    fraction = fix_scans.flag_zero_visibilities(str(ms))

    with table(str(ms), ack=False) as t:
        after = t.getcol('FLAG')
        assert np.array_equal(t.getcol('DATA'), data)
    # Zeros are flagged, existing flags kept, nothing else touched.
    assert np.array_equal(after, before | zero)
    assert fraction == pytest.approx((zero & ~before).mean())
