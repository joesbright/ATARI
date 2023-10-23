import os
import sys
sys.path.append(os.path.abspath('../utility'))
import general_functions as gf
import write_casa_scripts
import argparse
import astropy
import pyrap.tables as table
import pyuvdata
import logging
import numpy as np


parser = argparse.ArgumentParser()
parser.add_argument('input name', type=str, nargs=1, help='name of data set to calibrate, can be a single measurement set, or folder conatining uvh5 files')
args = parser.parse_args()

mydata = args.msname
if len(mydata) != 1:
    logging.error('Only one dataset should be given. Exiting.')
mydata = mydata[0]

# different file managing depending on input, but we want to end up with a measurement set
# with a consistent file structure.
if os.path.isfile(mydata) == True:
    # convert to measurement set & concat
    # fix scans, check data

elif mydata.endswith('.ms'):
    # fix scans, check data

else:
    logging.error('Unexpected input data type.')

myms = 

while table(myms + '/DATA_DESCRIPTION/'):
    spw_ids = table.getcol('SPECTRAL_WINDOW_ID')
while table(myms + '/SPECTRAL_WINDOW/'):
    spw_freqs = table.getcol('SPECTRAL_WINDOW_ID') / 1.e9
spws = dict(zip(spw_ids, spw_freqs))
while table(myms + '/FIELD/'):
    field_ids = table.getcol('SOURCE_ID')
    field_names = table.getcol('NAMES')
fields = dict(zip(field_ids, field_names))
while table(myms):
    antenna_names = table.getcol('ANTENNA1')
    tstart = np.min(table.getcol('TIME'))
    tend = np.max(table.getcol('TIME'))
    tmean = np.average(table.getcol('TIME'))




# Fix scans in original measure set
os.system('casa -c ../utility/fix_scans.py ' + myms)

# Fix antenna
unique_antenna = gf.get_unique_ants(myms)
write_casa_scripts.write_mstransform(myms, OUTPUTVIS, unique_antenna, '../scripts/000_FIX_ANTENNA.py')
