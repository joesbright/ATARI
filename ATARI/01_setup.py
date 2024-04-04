import os
import sys
sys.path.insert(0, os.path.abspath('../utility'))
import general_functions as gf
import write_casa_scripts
import argparse
import astropy
from pyrap.tables import table
import pyuvdata
import logging
import numpy as np
import find_phase_calibrator
from astropy.coordinates import SkyCoord
from astropy import units as u
import casacore
import json
import FGC
import scipy as sp
import math
import fix_scans
import glob
from pyuvdata import UVData


def match_calibrators(source):
    iscal = False
    if source in open('../data/calibrator_names.dat').read():
        iscal = True
       
    return(iscal)

os.system('rm -r ../data/SWIFT*spw*')
os.system('rm -r ../data/GRS*spw*')
os.system('rm -r ../data/sn2023*spw*')
os.system('rm -r ../data/sn2024*spw*')

cwd = os.getcwd()
logging.info('Working from ' + str(cwd))

parser = argparse.ArgumentParser()
parser.add_argument('msname', type=str, nargs=1, help='name of data set to calibrate, can be a single measurement set, or folder conatining uvh5 files (only measurement sets currently implemented).')
args = parser.parse_args()

mydata = args.msname
if len(mydata) != 1:
    logging.error('Only one dataset should be given. Exiting.')
mydata = mydata[0]

# different file managing depending on input, but we want to end up with a measurement set
# with a consistent file structure.
if os.path.isdir(mydata) == True and mydata.endswith('.ms') == False and mydata.endswith('.ms/') == False:
    logging.info('Starting with folder')
    # CONVERT TO MEASUREMENT SET FIRST
    myuvfiles_C = glob.glob('mydata/LoC*/' + '*.uvh5')
    myuvfiles_B = glob.glob('mydata/LoB*/' + '*.uvh5')

    uvd_C = UVData()
    uvd_C.read(myuvfiles_C, fix_old_proj=False)
    print("Writing LoC ms file")
    uvd_C.write_ms(mydata + "LO_C.ms")

    uvd_B = UVData()
    uvd_B.read(myuvfiles_B, fix_old_proj=False)
    print("Writing LoB ms file")
    uvd_B.write_ms(mydata + "LO_B.ms")

    casacore.tables.msconcat([mydata + "LO_C.ms", mydata + "LO_B.ms"], 'master_ms.ms')

    mydata = 'master_ms.ms'

    fix_scans.fix_scans(mydata)

elif mydata.endswith('.ms') or mydata.endswith('.ms/'):
    logging.info('Starting with measurement set.')
    fix_scans.fix_scans(mydata)

else:
    logging.error('Unexpected input data type.')

myms = mydata

with table(myms) as t:
    scan_numbers = t.getcol('SCAN_NUMBER')

print(scan_numbers)

if len(set(scan_numbers)) == 1:
    print('I EXPECT THAT THE SCAN NUMBERS HAVE NOT BEEN FIXED. FIXING.')
    fix_scans.fix_scans(myms)
else:
    print('SCANS ARE FINE. CONTINUE.')

with table(myms + '/DATA_DESCRIPTION/') as t:
    spw_ids = t.getcol('SPECTRAL_WINDOW_ID')
with table(myms + '/SPECTRAL_WINDOW/') as t:
    spw_freqs = t.getcol('REF_FREQUENCY') / 1.e9 # in GHz
spws = dict(zip(spw_ids, spw_freqs))
with table(myms + '/FIELD/') as t:
    field_ids = t.getcol('SOURCE_ID')
    field_names = t.getcol('NAME')
    field_ras = t.getcol('DELAY_DIR').squeeze()
    field_decs = t.getcol('DELAY_DIR').squeeze()
fields = dict(zip(field_ids, field_names))
field_ras = dict(zip(field_ids, field_ras))
field_decs = dict(zip(field_ids, field_decs))
with table(myms) as t:
    antenna_names = t.getcol('ANTENNA1')
    tstart = np.min(t.getcol('TIME'))
    tend = np.max(t.getcol('TIME'))
    tmean = np.average(t.getcol('TIME'))
    
# determine flux calibrators, phase calibrators, sources
myintents = []
for key in fields:
    if fields[key] in {'3c286', '3c48', '3c147'}:
        fields[key] = [fields[key], 'FLUX_CAL']
        myintents.append('#FCAL')
    elif match_calibrators(fields[key]) == True:
        fields[key] = [fields[key], 'PHASE_CAL']
        myintents.append('#GCAL')
    else:
        fields[key] = [fields[key], 'TARGET']
        myintents.append('#TARGET')

ordered_target_fields = []
ordered_pcal_fields = []
fcal_field = []

for key in fields:
    if fields[key][1] == 'TARGET':
        source_skycoords = SkyCoord(str(field_ras[key][0]) + ' ' + str(field_decs[key][1]), unit=(u.rad, u.rad))
        for key2 in fields:
            separation = np.inf
            if fields[key2][1] == 'PHASE_CAL':
                phase_skycoords = SkyCoord(str(field_ras[key2][0]) + ' ' + str(field_decs[key2][1]), unit=(u.rad, u.rad))
                if source_skycoords.separation(phase_skycoords).deg < separation:
                    separation = source_skycoords.separation(phase_skycoords).deg
                    print(fields[key2][0] + ' is the phase calibrator for ' + fields[key][0])
                    ordered_target_fields.append(fields[key][0])
                    ordered_pcal_fields.append(key2)
    if fields[key][1] == 'FLUX_CAL':
        fcal_field.append(key)

myintents = np.array(myintents)
myintents = np.asarray(['AMPLITUDE'])
with table(mydata, readonly=False) as t:
    mystates = t.getcol('STATE_ID')
    t.putcol('STATE_ID', np.zeros(len(mystates)) + 1)

with table(mydata + '/STATE', readonly=False) as t:
    t.putcol('OBS_MODE', ['TEST','TEST','TEST', 'TEST', 'TEST'])

field_matching = dict(zip(np.asarray(ordered_target_fields), np.asarray(ordered_pcal_fields)))

os.system('rm 1GC_.py')
os.system('rm image_.sh')
os.system('rm *.fits')

vislist = []
for key in fields:
    if fields[key][1] == 'TARGET':
        tm = table(mydata)
        t = table(mydata + '/SOURCE')
        for i, item in enumerate(t.getcol('NAME')):
            if item == fields[key][0]:
                print(i, item, t.getcol('SPECTRAL_WINDOW_ID'))
                x = t.getcol('SPECTRAL_WINDOW_ID')[i]
                y = [key, field_matching[fields[key][0]], fcal_field[0]]
                t1 = casacore.tables.taql('SELECT FROM $tm WHERE (DATA_DESC_ID IN [SELECT SPECTRAL_WINDOW_ID FROM ::DATA_DESCRIPTION WHERE SPECTRAL_WINDOW_ID == $x])')
                t2 = casacore.tables.taql('SELECT FROM $t1 WHERE FIELD_ID IN $y')
                newdir  = '../data/' + fields[key][0] + '_' + 'spw' + str(x) + '/'
                outfile = newdir + fields[key][0] + '_' + 'spw' + str(x) + '.ms'
                vislist.append(outfile)
                os.mkdir(newdir)
                os.mkdir(newdir + 'IMAGES')
                os.mkdir(newdir + 'CALIBRATION_TABLES')
                os.mkdir(newdir + 'PLOTS')
                t3 = t2.copy(outfile, True)
                t1.close()
                t2.close()
                t3.close()

                cell = ((sp.constants.c / (spws[x] * 1.e9)) / 300.) * (180. / sp.constants.pi) * 60. * 60. / 8.
                imsize = ((sp.constants.c / (spws[x] * 1.e9)) / 6.1) * (180. / sp.constants.pi) * 60. * 60. / cell
                imsize = int(2. ** (math.ceil(np.log2(imsize)) + 1))
                

                FGC.first_generation_calibration(outfile,
                                                 key,
                                                 fcal_field[0],
                                                 field_matching[fields[key][0]],
                                                 '1GC_.py',
                                                 newdir + 'CALIBRATION_TABLES/')

                FGC.image_all_fields(outfile,
                                     key,
                                     fcal_field[0],
                                     field_matching[fields[key][0]],
                                     'image_.sh',
                                     imsize,
                                     cell,
                                     newdir + 'IMAGES/')

        t.close()
        tm.close()

FGC.deep_image(
    vislist,
    2,
    'image_.sh',
    imsize,
    cell,
    newdir + 'IMAGES/')

