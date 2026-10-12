"""Make the small uvh5 test dataset in tests/data/uvh5/ from a full ATA
observation.

Run it where the observation lives (e.g. an ATA node). It only needs numpy and
pyuvdata. The folder layout and file names are kept exactly as they are,
because the pipeline finds files and reads the time ID and field name from
them. Within each file only a few antennas, integrations and channels are kept.

Example:
    python make_test_data.py /mnt/primary/ata/projects/p060/2026-10-04-03:16:44 \\
        ~/atari_test_uvh5 61317_11988_5522216 61317_13265_5561187 61317_13928_5581420
"""
import argparse
import glob
import os

import numpy as np
from pyuvdata import UVData


def trim_file(infile, outfile, n_ants, n_times, n_chans):
    # Read the metadata first to choose what to keep, then read only that.
    meta = UVData()
    meta.read(infile, read_data=False, fix_old_proj=False)

    # Keep the lowest-numbered antennas. The CASA recipe uses refant='3', so
    # keep at least 4.
    ants = np.unique(np.concatenate([meta.ant_1_array, meta.ant_2_array]))[:n_ants]
    times = np.unique(meta.time_array)[:n_times]
    start = max(0, meta.Nfreqs // 2 - n_chans // 2)
    chans = np.arange(start, min(start + n_chans, meta.Nfreqs))

    uvd = UVData()
    uvd.read(infile, antenna_nums=ants, times=times, freq_chans=chans, fix_old_proj=False)
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    uvd.write_uvh5(outfile)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('obsdir', help='observation folder containing the uvh5_* scan folders')
    parser.add_argument('outdir', help='where to write the trimmed copy')
    parser.add_argument('timeids', nargs='+', help='time IDs of the scans to keep, e.g. 61317_11988_5522216')
    parser.add_argument('--ants', type=int, default=6, help='number of antennas to keep (at least 4)')
    parser.add_argument('--times', type=int, default=3, help='number of integrations to keep')
    parser.add_argument('--chans', type=int, default=32, help='number of channels to keep, from the middle of the band')
    args = parser.parse_args()

    if args.ants < 4:
        parser.error('--ants must be at least 4 because the CASA recipe uses refant 3')

    for timeid in args.timeids:
        scans = glob.glob(os.path.join(args.obsdir, 'uvh5*' + timeid + '*0001'))
        if len(scans) != 1:
            parser.error('expected one scan folder for ' + timeid + ', found ' + str(len(scans)))
        scan = scans[0]
        files = sorted(glob.glob(os.path.join(scan, 'Lo*', '*.uvh5')))
        if not files:
            parser.error('no Lo*/*.uvh5 files in ' + scan)
        for infile in files:
            outfile = os.path.join(args.outdir, os.path.relpath(infile, args.obsdir))
            print('trimming', os.path.relpath(infile, args.obsdir))
            trim_file(infile, outfile, args.ants, args.times, args.chans)


if __name__ == '__main__':
    main()
