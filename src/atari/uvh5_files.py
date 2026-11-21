import glob
import os

import numpy as np
from pyuvdata import UVData

from atari.calibrators import classify_field, skip_field

# Each LO is 672 MHz recorded as 7 tunings of 96 MHz, each in its own
# LoX.CXXXX folder. A tuning's name is its first channel in 0.5 MHz
# channels, and every LO uses the same names, though each LO's centre
# frequency (and recording) is independent.
TUNINGS = ['C0352', 'C0544', 'C0736', 'C0928', 'C1120', 'C1312', 'C1504']


def _scans(mydata):
    # (time ID, field name) of each LoC file's scan, leaving out skipped
    # fields.
    for file in glob.glob(mydata + '/uvh5*/LoC*/' + '*.uvh5'):
        parts = file.split('/')[-1].split('_')
        # The field name can contain underscores (Stay_put), so it is
        # everything between the time ID and the trailing _0001.
        field = '_'.join(parts[4:-1])
        if not skip_field(field):
            yield parts[1] + '_' + parts[2] + '_' + parts[3], field


def find_time_ids(mydata):
    # Each scan has several LoC tuning folders, so the time ID must be
    # collected once per scan, not once per file. Duplicates made the
    # conversion pool convert the same scan in several workers at once, which
    # fails when the second worker finds the first one's MS already written.
    return sorted({timeID for timeID, field in _scans(mydata)})


def find_fields(mydata):
    # The observed fields, from the file names, so they can be checked
    # before the slow conversion.
    return sorted({field for timeID, field in _scans(mydata)})


def find_converted_ms(mydata):
    # The per-scan, per-LO measurement sets written by parallel_file_conversion,
    # in the order they are passed to CASA concat. concat sorts scans by time
    # but keeps the given order of LOs within a scan, and numbers spectral
    # windows in that order, so sort by name (LoA, LoB, ...) rather than rely
    # on the order the filesystem lists them. Only the converted files'
    # pattern is matched: the final MS and CASA's temporary ones are made in
    # the same folder.
    return sorted(glob.glob(mydata + '/uvh5_*_Lo?.ms'))


def group_by_lo(paths):
    # The converted per-scan, per-LO measurement sets grouped by LO (LoA,
    # LoB, ...), each group in time order: names start with the time ID,
    # whose fixed-width fields sort in time order.
    groups = {}
    for path in sorted(paths):
        groups.setdefault(os.path.basename(path)[-6:-3], []).append(path)
    return dict(sorted(groups.items()))


def flagging_jobs(sizes, available, fraction=0.75, need=0.8):
    # How many aoflagger runs (one per LO MS, sizes in bytes) may run at once.
    # aoflagger reads a whole MS into memory when it fits, needing about
    # `need` x its size (the visibilities; 31.8 GB for a 40 GB LO on
    # 2026-09-18), and each process checks free memory only for itself when
    # it starts, so only as many as fit in `fraction` of the available memory
    # run together (at least one: if one doesn't fit, aoflagger reads it from
    # disk instead). Threads are left to aoflagger (all cores each) and shared
    # by the system, so a job left running alone gets every core.
    fit = int(fraction * available // (need * max(sizes))) if sizes else 1
    return max(1, min(len(sizes), fit))


def final_ms_name(mydata, extra_calibrators=None):
    # <MJD>_<targets>.ms for the combined, flagged and averaged measurement
    # set: the MJD of the first scan, so an observation running past midnight
    # UTC keeps its start date, and every target in alphabetical order,
    # joined with underscores. Skipped scans count for neither. The MJD is the
    # first part of the time ID (e.g. 61317 in 61317_11988_5522216).
    scans = list(_scans(mydata))
    first = min(tuple(int(part) for part in timeID.split('_')[:2]) for timeID, field in scans)
    targets = sorted({field for timeID, field in scans if classify_field(field, extra_calibrators) == 'TARGET'})
    return str(first[0]) + '_' + '_'.join(targets) + '.ms'


def find_tuning_files(folder, lo):
    # The tunings of one LO (e.g. LoA.C0352 ... LoA.C1504) are read by
    # pyuvdata together, so list them in frequency order rather than the
    # order the filesystem gives.
    return sorted(glob.glob(folder + lo + '*/*.uvh5'))


def tuning_name(path):
    # 'C0352' from '.../LoA.C0352/<file>.uvh5'.
    return os.path.basename(os.path.dirname(path)).split('.')[-1]


def read_lo(folder, lo):
    # Read one scan's LO, with any of its 7 tunings that were not recorded (a
    # recording node dropped) filled in as flagged data. Every LO of every
    # scan then has the same channels, so CASA concat neither makes an extra
    # spectral window for some scans nor crashes on LOs with different
    # channel counts. Returns None if the LO was not recorded at all.
    files = find_tuning_files(folder, lo)
    if not files:
        return None

    uvd = UVData()
    uvd.read(files, fix_old_proj=False)

    recorded = [tuning_name(f) for f in files]
    for tuning in recorded:
        if tuning not in TUNINGS:
            raise ValueError(folder + lo + '.' + tuning + ' is not one of the expected tunings ('
                             + ', '.join(TUNINGS) + '), so missing tunings cannot be placed.')
    missing = [t for t in TUNINGS if t not in recorded]
    if missing:
        # The tuning name is its first channel number in 0.5 MHz channels,
        # so a missing tuning's frequencies are a recorded tuning's shifted
        # by the difference in channel numbers.
        template = UVData()
        template.read(files[0], fix_old_proj=False)
        width = template.channel_width[0]
        # Check that assumption on the tunings that were recorded, rather
        # than fill in the wrong place.
        for file, tuning in zip(files, recorded):
            header = UVData()
            header.read(file, read_data=False, fix_old_proj=False)
            start = template.freq_array[0] + (int(tuning[1:]) - int(recorded[0][1:])) * width
            if not np.isclose(header.freq_array[0], start, rtol=0, atol=abs(width) / 100):
                raise ValueError(folder + lo + '.' + tuning + ' does not start at the frequency its name '
                                 'implies, so its missing tunings cannot be placed.')
        for tuning in missing:
            fill = template.copy()
            shift = (int(tuning[1:]) - int(recorded[0][1:])) * width
            fill.freq_array = template.freq_array + shift
            fill.data_array[:] = 0
            fill.nsample_array[:] = 0
            fill.flag_array[:] = True
            uvd += fill
        uvd.reorder_freqs(channel_order='freq')

    return uvd
