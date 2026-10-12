"""Command-line arguments for atari-setup. Kept free of casacore so it can be
tested anywhere."""
import argparse


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('msname', type=str, nargs=1, help='name of data set to calibrate, can be a single measurement set, or folder conatining uvh5 files (only measurement sets currently implemented).')
    parser.add_argument('--casapath', type=str, help='Path to CASA. Needs this if an alias is used.', default='casa')
    parser.add_argument('--chanbin', type=str, help='number of 0.5 MHz channels to average together', default='8')
    parser.add_argument('--flagants', type=str, help='comma separated list of antennas to flag', default='')
    parser.add_argument('--calibrators', type=str, help='file of extra gain calibrator names, one per line, added to the built-in list', default=None)
    return parser.parse_args(argv)
