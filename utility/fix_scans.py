from pyrap.tables import table

def fix_scans(myms):
    with table(myms, nomodify=False) as t:
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

    return()