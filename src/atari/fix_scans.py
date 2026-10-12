from casacore.tables import table
import numpy as np


def fix_scans(myms):
    with table(myms, readonly=False) as t:
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
    with table(myms + '/SOURCE', readonly=False) as t:
        default_ids = t.getcol('SPECTRAL_WINDOW_ID')
        new_ids = np.zeros(len(default_ids))

        t.putcol('SPECTRAL_WINDOW_ID', new_ids)

    return()