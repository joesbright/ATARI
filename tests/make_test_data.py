"""Make the small uvh5 test dataset in tests/data/uvh5/ from a full ATA
observation.

Run it where the observation lives (e.g. an ATA node). It needs numpy and
h5py, plus pyuvdata for the check at the end.

The folder layout and file names are kept exactly as they are, because the
pipeline finds files and reads the time ID and field name from them. Within
each file only a few antennas, integrations and channels are kept.

The files are cut with h5py rather than rewritten with pyuvdata, so they keep
the same internal layout as the originals: different pyuvdata versions write
different layouts, and older versions cannot read newer ones. After trimming,
each file is checked by reading the same selection from the original with
pyuvdata and comparing.

Example:
    python make_test_data.py /mnt/primary/ata/projects/p060/2026-10-04-03:16:44 \\
        ~/atari_test_uvh5 61317_11988_5522216 61317_13265_5561187 61317_13928_5581420
"""
import argparse
import glob
import os

import h5py
import numpy as np

# Header datasets that have a frequency axis. Other datasets are matched by
# shape: a first axis of length Nblts means one entry per baseline-time.
FREQ_HEADER_DATASETS = ('freq_array', 'channel_width', 'flex_spw_id_array')
DATA_DATASETS = ('visdata', 'flags', 'nsamples')


def scalar(group, name):
    return group[name][()]


def set_scalar(group, name, value):
    dtype = group[name].dtype
    del group[name]
    group.create_dataset(name, data=np.asarray(value, dtype=dtype))


def write_like(group, name, source, data):
    """Create group[name] holding data, with the same type, compression and
    attributes as the source dataset."""
    kwargs = {}
    if source.compression is not None:
        kwargs = dict(compression=source.compression, compression_opts=source.compression_opts,
                      shuffle=source.shuffle, chunks=True)
    out = group.create_dataset(name, data=data, dtype=source.dtype, **kwargs)
    for key, value in source.attrs.items():
        out.attrs[key] = value


def select_freq(data, nfreqs, chans):
    """Select channels along the axis whose length is Nfreqs. A dataset with
    no such axis (e.g. a scalar channel_width) is returned unchanged."""
    axes = [i for i, n in enumerate(data.shape) if n == nfreqs]
    if not axes:
        return data
    if len(axes) > 1:
        raise ValueError('more than one axis of length Nfreqs in shape ' + str(data.shape))
    return np.take(data, chans, axis=axes[0])


def trim_file(infile, outfile, n_ants, n_times, n_chans, report=False):
    """Write a trimmed copy of infile and return the selection (antenna
    numbers, times, channel indices) so it can be checked."""
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    with h5py.File(infile, 'r') as src, h5py.File(outfile, 'w') as dst:
        header = src['Header']
        nblts = int(scalar(header, 'Nblts'))
        nfreqs = int(scalar(header, 'Nfreqs'))
        if nblts == nfreqs:
            raise ValueError('Nblts equals Nfreqs, so axes cannot be told apart by length')

        ant1 = header['ant_1_array'][()]
        ant2 = header['ant_2_array'][()]
        times = header['time_array'][()]

        # Keep the lowest-numbered antennas (at least 4: the regression tests
        # use --refant 3), the first integrations and channels from the middle.
        ants = np.union1d(ant1, ant2)[:n_ants]
        keep_times = np.unique(times)[:n_times]
        blts = np.nonzero(np.isin(ant1, ants) & np.isin(ant2, ants) & np.isin(times, keep_times))[0]
        start = max(0, nfreqs // 2 - n_chans // 2)
        chans = np.arange(start, min(start + n_chans, nfreqs))

        for key, value in src.attrs.items():
            dst.attrs[key] = value

        # Header: cut per-baseline-time and per-frequency arrays and copy
        # everything else (including subgroups) unchanged.
        out_header = dst.create_group('Header')
        for key, value in header.attrs.items():
            out_header.attrs[key] = value
        trimmed = []
        for name, item in header.items():
            if isinstance(item, h5py.Group):
                src.copy(item, out_header, name=name)
            elif name in FREQ_HEADER_DATASETS:
                write_like(out_header, name, item, select_freq(item[()], nfreqs, chans))
                trimmed.append(name)
            elif item.shape and item.shape[0] == nblts:
                write_like(out_header, name, item, item[()][blts])
                trimmed.append(name)
            else:
                src.copy(item, out_header, name=name)

        new_ant1 = ant1[blts]
        new_ant2 = ant2[blts]
        set_scalar(out_header, 'Nblts', len(blts))
        set_scalar(out_header, 'Nfreqs', len(chans))
        set_scalar(out_header, 'Ntimes', len(np.unique(times[blts])))
        set_scalar(out_header, 'Nbls', len({(a, b) for a, b in zip(new_ant1, new_ant2)}))
        set_scalar(out_header, 'Nants_data', len(np.union1d(new_ant1, new_ant2)))

        # Data: cut the baseline-time axis (always the first) and the
        # frequency axis.
        out_data = dst.create_group('Data')
        for key, value in src['Data'].attrs.items():
            out_data.attrs[key] = value
        for name, item in src['Data'].items():
            if name not in DATA_DATASETS:
                raise ValueError('unexpected dataset Data/' + name)
            write_like(out_data, name, item, select_freq(item[blts], nfreqs, chans))
            trimmed.append('Data/' + name)

        for name in src:
            if name not in ('Header', 'Data'):
                src.copy(src[name], dst, name=name)

    if report:
        print('  cut along baseline-time or frequency:', ', '.join(trimmed))
    return ants, np.unique(times[blts]), chans


def check_file(infile, outfile, ants, times, chans):
    """Read the same selection from the original with pyuvdata and check it
    matches the trimmed file exactly."""
    from pyuvdata import UVData

    expected = UVData()
    expected.read(infile, antenna_nums=ants, times=times, freq_chans=chans, fix_old_proj=False)
    actual = UVData()
    actual.read(outfile, fix_old_proj=False)
    # pyuvdata records the selection in the history, and the file name
    # differs; neither is part of the data.
    expected.history = actual.history
    if hasattr(expected, 'filename'):
        expected.filename = actual.filename
    if expected != actual:
        raise RuntimeError('trimmed file does not match the original selection: ' + outfile)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('obsdir', help='observation folder containing the uvh5_* scan folders')
    parser.add_argument('outdir', help='where to write the trimmed copy')
    parser.add_argument('timeids', nargs='+', help='time IDs of the scans to keep, e.g. 61317_11988_5522216')
    parser.add_argument('--ants', type=int, default=6, help='number of antennas to keep (at least 4)')
    parser.add_argument('--times', type=int, default=3, help='number of integrations to keep')
    parser.add_argument('--chans', type=int, default=32, help='number of channels to keep, from the middle of the band')
    parser.add_argument('--no-check', action='store_true', help='skip comparing each trimmed file with the original')
    args = parser.parse_args()

    if args.ants < 4:
        parser.error('--ants must be at least 4 because the regression tests use --refant 3')

    first = True
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
            selection = trim_file(infile, outfile, args.ants, args.times, args.chans, report=first)
            if not args.no_check:
                check_file(infile, outfile, *selection)
                print('  matches the original')
            first = False


if __name__ == '__main__':
    main()
