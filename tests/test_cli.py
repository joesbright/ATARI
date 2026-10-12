"""Command-line parsing for atari-setup. Needs no casacore."""
from atari.cli import parse_args


def test_defaults_are_whole_strings():
    # Issue #4: with nargs=1, a string default was indexed with [0], so
    # --casapath defaulted to 'c'.
    args = parse_args(['data.ms'])
    assert args.casapath == 'casa'
    assert args.chanbin == '8'


def test_given_values_are_whole_strings():
    args = parse_args(['data.ms', '--casapath', '/opt/casa/bin/casa', '--chanbin', '16'])
    assert args.casapath == '/opt/casa/bin/casa'
    assert args.chanbin == '16'
