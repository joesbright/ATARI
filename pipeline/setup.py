import os
import sys
sys.path.append(os.path.abspath('../utility'))
import general_functions as gf
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('msname', type=str, nargs=1, help='name of measurement set to calibrate')
parser.add_argument('-bandpass', '--bp', type=str, nargs=1, help='name of bandpass calibrator', required=True)
parser.add_argument('-complexgain', '--cg', type=str, nargs='*', help='name(s) of complex gain calibrator(s)')
parser.add_argument('-target', '--tg', type=str, nargs='*', help='name(s) of target(s)')
parser.add_argument('-check', '--ch', type=str, nargs='*', help='name(s) of check source(s)')
args = parser.parse_args()
print(args)

myms = args.msname[0]
mybandpass = args.bp[0]
mygaincals = args.cg
mytargets = args.tg
mychecks = args.ch

print(myms, mybandpass, mygaincals, mytargets, mychecks)

if len(mygaincals) != len(mytargets):
    print('Need same number of targets and complex gain calibrators')
    exit()

# Fix scans
os.system('casa -c ../utility/fix_scans.py ' + myms)

# Fix antenna and remove autocorrelations
unique_antenna = gf.get_unique_ants(myms)
os.system('python ../pipeline/')

# GET META INFORMATION FROM THE MEASUER SET

