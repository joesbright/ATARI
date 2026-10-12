import glob
import os

import numpy as np
from pyuvdata import UVData

from atari.calibrators import skip_field

# Each LO is 672 MHz recorded as 7 tunings of 96 MHz, each in its own
# LoX.CXXXX folder. A tuning's name is its first channel in 0.5 MHz
# channels, and every LO uses the same names, though each LO's centre
# frequency (and recording) is independent.
TUNINGS = ['C0352', 'C0544', 'C0736', 'C0928', 'C1120', 'C1312', 'C1504']


def find_time_ids(mydata):
    # Each scan has several LoC tuning folders, so the time ID must be
    # collected once per scan, not once per file. Duplicates made the
    # conversion pool convert the same scan in several workers at once, which
    # fails when the second worker finds the first one's MS already written.
    timeIDs = set()
    for file in glob.glob(mydata + '/uvh5*/LoC*/' + '*.uvh5'):
        parts = file.split('/')[-1].split('_')
        # The field name can contain underscores (Stay_put), so it is
        # everything between the time ID and the trailing _0001.
        if skip_field('_'.join(parts[4:-1])):
            continue
        timeIDs.add(parts[1] + '_' + parts[2] + '_' + parts[3])

    return sorted(timeIDs)


def find_converted_ms(mydata):
    # The per-scan, per-LO measurement sets written by parallel_file_conversion,
    # in the order they are passed to CASA concat. concat sorts scans by time
    # but keeps the given order of LOs within a scan, and numbers spectral
    # windows in that order, so sort by name (LoA, LoB, ...) rather than rely
    # on the order the filesystem lists them.
    return sorted(glob.glob(mydata + '/*.ms'))


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
