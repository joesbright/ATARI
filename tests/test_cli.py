"""Command-line parsing for atari-setup. Needs no casacore."""
import pytest

from atari.cli import parse_args, resolve_refant


def test_defaults_are_whole_strings():
    # Issue #4: with nargs=1, a string default was indexed with [0], so
    # --casapath defaulted to 'c'.
    args = parse_args(['data.ms', '--refant', '3'])
    assert args.casapath == 'casa'
    assert args.chanbin == '8'


def test_given_values_are_whole_strings():
    args = parse_args(['data.ms', '--refant', '3', '--casapath', '/opt/casa/bin/casa', '--chanbin', '16'])
    assert args.casapath == '/opt/casa/bin/casa'
    assert args.chanbin == '16'


def test_flagants_is_empty_when_not_given():
    # Issue #7: the default was one empty name, which could match antennas
    # whose name is empty and start a CASA flagging run for nothing.
    assert parse_args(['data.ms', '--refant', '3']).flagants == []


def test_flagants_is_a_list_of_names():
    assert parse_args(['data.ms', '--refant', '3', '--flagants', '1a,2b']).flagants == ['1a', '2b']


def test_refant_is_required():
    with pytest.raises(SystemExit):
        parse_args(['data.ms'])


ANTENNAS = ['1a', '1c', '1h', '2a', '2b']


@pytest.mark.parametrize('refant, index', [('3', '3'), ('0', '0'), ('2a', '3'), ('1c', '1')])
def test_refant_can_be_an_index_or_a_name(refant, index):
    # CASA is always given the index, as the hard-coded '3' was.
    assert resolve_refant(refant, ANTENNAS) == index


@pytest.mark.parametrize('refant', ['5', '9a'])
def test_refant_must_be_in_the_measurement_set(refant):
    with pytest.raises(ValueError, match=refant):
        resolve_refant(refant, ANTENNAS)


@pytest.mark.parametrize('refant', ['2a', '3'])
def test_refant_must_not_be_flagged(refant):
    with pytest.raises(ValueError, match='--flagants'):
        resolve_refant(refant, ANTENNAS, ['2a'])
