import os
import sys
sys.path.append(os.path.abspath('../utility'))
import general_functions as gf
import write_casa_scripts
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('msname', type=str, nargs=1, help='name of measurement set to calibrate')
parser.add_argument('-bandpass', '--bp', type=str, nargs=1, help='name of bandpass calibrator', required=True)
parser.add_argument('-complexgain', '--cg', type=str, nargs='*', help='name(s) of complex gain calibrator(s)')
parser.add_argument('-target', '--tg', type=str, nargs='*', help='name(s) of target(s)')
parser.add_argument('-check', '--ch', type=str, nargs='*', help='name(s) of check source(s)')
args = parser.parse_args()

myms = args.msname[0]
mybandpass = args.bp[0]
mygaincals = args.cg
mytargets = args.tg
mychecks = args.ch

if len(mygaincals) != len(mytargets):
    print('Need same number of targets and complex gain calibrators')
    exit()

# Fix scans in original measure set
os.system('casa -c ../utility/fix_scans.py ' + myms)

# Fix antenna
unique_antenna = gf.get_unique_ants(myms)
write_casa_scripts.write_mstransform(myms, OUTPUTVIS, unique_antenna, '../scripts/000_FIX_ANTENNA.py')

# GET META INFORMATION FROM THE MEASURE SET
tb.open(OUTPUTVIS + '/SPECTRAL_WINDOW')
bandwidth_hz = tb.getcol('TOTAL_BANDWIDTH')[0]
channel_frequencies_hz = tb.getcol('CHAN_FREQ')[:,0]
N_channels = tb.getcol('NUM_CHAN')[0]
