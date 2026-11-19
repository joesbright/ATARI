from casacore.tables import table
import numpy as np


def flag_zero_visibilities(myms):
    # Flag every sample whose DATA is exactly zero, keeping existing flags,
    # and return the fraction of samples newly flagged. Dead antennas, feeds
    # and LOs are recorded as zeros without being flagged; calibration and
    # imaging would otherwise treat them as measurements. Read in chunks of
    # rows, since DATA for a full observation is large.
    newly = total = 0
    with table(myms, readonly=False, ack=False) as t:
        step = 50000
        for start in range(0, t.nrows(), step):
            data = t.getcol('DATA', startrow=start, nrow=step)
            flag = t.getcol('FLAG', startrow=start, nrow=step)
            zero = (data == 0) & ~flag
            newly += zero.sum()
            total += flag.size
            if zero.any():
                t.putcol('FLAG', flag | zero, startrow=start, nrow=step)
    return newly / total if total else 0.0


def fix_scans(myms):
    with table(myms, readonly=False, ack=False) as t:
        default_field = t.getcol('FIELD_ID')
        default_scans = t.getcol('SCAN_NUMBER')
        scans = default_scans

        scan_count = 0
        for i in range(len(default_field)):
            if i == 0:
                scans[i] = scan_count
            elif default_field[i] != default_field[i-1]:
                scan_count = scan_count + 1
                scans[i] = scan_count
            else:
                scans[i] = scan_count
        t.putcol('SCAN_NUMBER', scans)

    return()

def fix_spw(myms):
    with table(myms + '/SOURCE', readonly=False, ack=False) as t:
        default_ids = t.getcol('SPECTRAL_WINDOW_ID')
        new_ids = np.zeros(len(default_ids))

        t.putcol('SPECTRAL_WINDOW_ID', new_ids)

    return()