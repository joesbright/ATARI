import os
import sys
sys.path.append(os.path.abspath('../utility'))
import general_functions as gf
import write_casa_scripts
import argparse
import astropy
from pyrap.tables import table
import pyuvdata
import logging
import numpy as np
import find_phase_calibrator


def match_calibrators(source):
    iscal = False
    if source in open('../data/calibrator_names.dat').read():
        iscal = True
       
    return(iscal)


cwd = os.getcwd()
logging.info('Working from ' + str(cwd))

parser = argparse.ArgumentParser()
parser.add_argument('msname', type=str, nargs=1, help='name of data set to calibrate, can be a single measurement set, or folder conatining uvh5 files')
args = parser.parse_args()

mydata = args.msname
if len(mydata) != 1:
    logging.error('Only one dataset should be given. Exiting.')
mydata = mydata[0]

# different file managing depending on input, but we want to end up with a measurement set
# with a consistent file structure.
if os.path.isdir(mydata) == True:
    logging.info('Starting with folder')

elif mydata.endswith('.ms'):
    logging.info('Starting with measurement set.')

else:
    logging.error('Unexpected input data type.')

myms = mydata

with table(myms + '/DATA_DESCRIPTION/') as t:
    spw_ids = t.getcol('SPECTRAL_WINDOW_ID')
with table(myms + '/SPECTRAL_WINDOW/') as t:
    spw_freqs = t.getcol('REF_FREQUENCY') / 1.e9 # in GHz
spws = dict(zip(spw_ids, spw_freqs))
with table(myms + '/FIELD/') as t:
    field_ids = t.getcol('SOURCE_ID')
    field_names = t.getcol('NAME')
fields = dict(zip(field_ids, field_names))
with table(myms) as t:
    antenna_names = t.getcol('ANTENNA1')
    tstart = np.min(t.getcol('TIME'))
    tend = np.max(t.getcol('TIME'))
    tmean = np.average(t.getcol('TIME'))

# determine flux calibrators, phase calibrators, sources
for key in fields:
    if fields[key] in {'3c286', '3c48', '3c147'}:
        fields[key] = [fields[key], 'FLUX_CAL']
    elif match_calibrators(fields[key]) == True:
        fields[key] = [fields[key], 'PHASE_CAL']
    else:
        fields[key] = [fields[key], 'TARGET']

print(fields)



# Fix scans in original measure set
# os.system('casa -c ../utility/fix_scans.py ' + myms)

# Fix antenna
# unique_antenna = gf.get_unique_ants(myms)
# write_casa_scripts.write_mstransform(myms, OUTPUTVIS, unique_antenna, '../scripts/000_FIX_ANTENNA.py')
