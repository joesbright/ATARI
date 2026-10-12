import glob


def find_time_ids(mydata):
    # Each scan has several LoC tuning folders, so the time ID must be
    # collected once per scan, not once per file. Duplicates made the
    # conversion pool convert the same scan in several workers at once, which
    # fails when the second worker finds the first one's MS already written.
    timeIDs = set()
    for file in glob.glob(mydata + '/uvh5*/LoC*/' + '*.uvh5'):
        parts = file.split('/')[-1].split('_')
        timeIDs.add(parts[1] + '_' + parts[2] + '_' + parts[3])

    return sorted(timeIDs)


def find_converted_ms(mydata):
    # The per-scan, per-LO measurement sets written by parallel_file_conversion,
    # in the order they are passed to CASA concat. concat sorts scans by time
    # but keeps the given order of LOs within a scan, and numbers spectral
    # windows in that order, so sort by name (LoA, LoB, ...) rather than rely
    # on the order the filesystem lists them.
    return sorted(glob.glob(mydata + '/*.ms'))
