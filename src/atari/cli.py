"""Command-line arguments for atari-setup. Kept free of casacore so it can be
tested anywhere."""
import argparse


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('msname', type=str, nargs=1, help='name of data set to calibrate, can be a single measurement set, or folder conatining uvh5 files (only measurement sets currently implemented).')
    parser.add_argument('--casapath', type=str, help='Path to CASA. Needs this if an alias is used.', default='casa')
    parser.add_argument('--refant', type=str, required=True, help='reference antenna for calibration, as a name (e.g. 1c) or an index into the ANTENNA table of the measurement set (e.g. 3)')
    parser.add_argument('--chanbin', type=str, help='number of 0.5 MHz channels to average together', default='8')
    parser.add_argument('--flagants', type=str, help='comma separated list of antennas to flag', default='')
    parser.add_argument('--calibrators', type=str, help='file of extra gain calibrator names, one per line, added to the built-in list', default=None)
    args = parser.parse_args(argv)
    # A list of antenna names, empty if none were given.
    args.flagants = [name for name in args.flagants.split(',') if name]
    return args


def resolve_refant(refant, ant_names, flagants=()):
    # The reference antenna's index in ant_names, as a string for CASA.
    # refant is an index if it is all digits (ATA names always contain a
    # letter) and a name otherwise.
    if refant in flagants:
        raise ValueError('Reference antenna ' + refant + ' is also in --flagants.')
    if refant.isdigit():
        index = int(refant)
        if index >= len(ant_names):
            raise ValueError('Reference antenna index ' + refant + ' is out of range: the measurement set has '
                             + str(len(ant_names)) + ' antennas.')
    elif refant in ant_names:
        index = list(ant_names).index(refant)
    else:
        raise ValueError('Reference antenna ' + refant + ' is not in the measurement set. Antennas: '
                         + ', '.join(ant_names) + '.')
    if ant_names[index] in flagants:
        raise ValueError('Reference antenna ' + refant + ' (' + ant_names[index] + ') is also in --flagants.')
    return str(index)
