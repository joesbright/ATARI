import os
import sys
sys.path.insert(0, os.path.abspath('../utility'))
import general_functions as gf
import write_casa_scripts
import argparse
import astropy
import pyuvdata
import logging
import numpy as np
import find_phase_calibrator
from astropy.coordinates import SkyCoord
from astropy import units as u
from casacore.tables import table
import casacore.tables
import FGC
import scipy as sp
import math
import fix_scans
import glob
from pyuvdata import UVData
from termcolor import colored
import multiprocessing


def parallel_file_conversion(field):

    for folder in glob.glob(mydata + '/uvh5*' + field + '*0001/'):
        if os.path.isdir(folder.rstrip('/') + '_LoC.ms') == False:
            uvd_C = UVData()
            uvd_C.read(glob.glob(folder + 'LoC*/*.uvh5'), fix_old_proj=False)
            uvd_C.write_ms(folder.rstrip('/') + '_LoC.ms')
            fix_scans.fix_spw(folder.rstrip('/') + '_LoC.ms')

        if os.path.isdir(folder.rstrip('/') + '_LoB.ms') == False:
            uvd_B = UVData()
            uvd_B.read(glob.glob(folder + 'LoB*/*.uvh5'), fix_old_proj=False)
            uvd_B.write_ms(folder.rstrip('/') + '_LoB.ms')
            fix_scans.fix_spw(folder.rstrip('/') + '_LoB.ms')

    return None


def match_calibrators(source):
    iscal = False
    if source in open('../data/calibrator_names.dat').read():
        iscal = True
       
    return(iscal)

cwd = os.getcwd()
logging.info('Working from ' + str(cwd))

# clean up previous run
os.system('rm 1GC_.py')
os.system('rm image_.sh')
os.system('rm avg_command.py')
os.system('rm concat_command.py')
os.system('rm concat_avg_commands.py')

parser = argparse.ArgumentParser()
parser.add_argument('msname', type=str, nargs=1, help='name of data set to calibrate, can be a single measurement set, or folder conatining uvh5 files (only measurement sets currently implemented).')
parser.add_argument('--casapath', type=str, nargs=1, help='Path to CASA. Needs this if an alias is used.', default='casa')
parser.add_argument('--chanbin', type=str, nargs=1, help='number of 0.5 MHz channels to average together', default='8')
parser.add_argument('--flagants', type=str, help='comma separated list of antennas to flag', default='')
args = parser.parse_args()

mydata = args.msname
casapath = args.casapath[0]
chanbin = args.chanbin[0]
flagants = args.flagants.split(',')

if len(mydata) != 1:
    print(colored('Only one dataset should be given. Exiting.', 'red'))
mydata = mydata[0]

# different file managing depending on input, but we want to end up with a measurement set
# with a consistent file structure.
if os.path.isdir(mydata) == True and mydata.endswith('.ms') == False and mydata.endswith('.ms/') == False:
    print(colored('Starting with folder: ' + mydata + '.', 'red'))
    # CONVERT TO MEASUREMENT SET FIRST
    myuvfiles_C = glob.glob(mydata + '/uvh5*/LoC*/' + '*.uvh5')
    myuvfiles_B = glob.glob(mydata + '/uvh5*/LoB*/' + '*.uvh5')

    fields = []
    for file in myuvfiles_C:
        fields.append(file.split('/')[-1].split('_')[4])
    unique_fields = list(set(fields))

    if __name__ == '__main__':
        with multiprocessing.Pool() as pool:
            results = pool.map(parallel_file_conversion, unique_fields)

    final_concat = glob.glob(mydata + '/*.ms')

    print(colored('Combining spectral chunks.', 'red'))

    with table(final_concat[0] + '/ANTENNA/') as t:
        ant_names = t.getcol('NAME')

    if flagants != ['']:
        flagants = [i for i in range(len(ant_names)) if ant_names[i] in flagants]
        flagants = [str(x) for x in flagants]
        flagants = ','.join(flagants)

    f = open('concat_command.py', 'w')
    f.write('concat(vis=' + str(final_concat) + ', concatvis=\'' + mydata + '/master_ms_tmp.ms\')')
    if flagants != ['']:
        f.write('\n')
        f.write('mstransform(vis=\'' + mydata + '/master_ms_tmp.ms\', outputvis=\'' + mydata + '/master_ms_tmp2.ms\', antenna=\'!' + flagants + '\', datacolumn=\'DATA\')')
    f.close()
    os.system(casapath + ' --nologger --log2term --nologfile -c concat_command.py')

    if flagants != ['']:
        os.system('aoflagger ' + mydata + '/master_ms_tmp2.ms')
    else:
        os.system('aoflagger ' + mydata + '/master_ms_tmp.ms')

    if flagants != ['']:
        fix_scans.fix_scans(mydata + '/master_ms_tmp2.ms')
    else:
        fix_scans.fix_scans(mydata + '/master_ms_tmp.ms')

    f = open('avg_command.py', 'w')
    if flagants != ['']:
        f.write('mstransform(vis=\'' + mydata + '/master_ms_tmp2.ms\', outputvis=\'' + mydata + '/master_ms.ms\', chanaverage=True, chanbin=' + chanbin + ' , datacolumn=\'DATA\')')
    else:
        f.write('mstransform(vis=\'' + mydata + '/master_ms_tmp.ms\', outputvis=\'' + mydata + '/master_ms.ms\', chanaverage=True, chanbin=' + chanbin + ' , datacolumn=\'DATA\')')
    f.close()

    print(colored('Averaging data.', 'red'))
    os.system(casapath + ' --nologger --log2term --nologfile -c avg_command.py')
    os.system('rm -r ' + mydata + '/master_ms_tmp.ms')
    os.system('rm -r ' + mydata + '/master_ms_tmp2.ms')
    os.system('rm avg_command.py')
    os.system('rm concat_command.py')
    os.system('rm concat_avg_commands.py')

    mydata = mydata + '/master_ms.ms'

elif mydata.endswith('.ms') or mydata.endswith('.ms/'):
    with table(mydata + '/ANTENNA/') as t:
        ant_names = t.getcol('NAME')
    
    flagants = [i for i in range(len(ant_names)) if ant_names[i] in flagants]
    flagants = [str(x) for x in flagants]
    flagants = ','.join(flagants)
    
    if flagants != '':
        f = open('flag_command.py', 'w')
        f.write('flagdata(vis=' + mydata + ', mode=\'manual\', antenna=\'' + flagants + '\')')
        f.close()
        os.system(casapath + ' --nologger --log2term --nologfile -c flag_command.py')
        os.system('rm flag_command.py')
    print(colored('Starting with measurement set: ' + mydata + '.', 'red'))

else:
    logging.error('Unexpected input data type.')

myms = mydata

with table(myms) as t:
    scan_numbers = t.getcol('SCAN_NUMBER')

if len(set(scan_numbers)) == 1:
    print(colored('I suspect that the scan numbers have not been fixed. Fixing.', 'red'))
    fix_scans.fix_scans(myms)
else:
    print(colored('Scan numbers are incremented correctly, continuing.', 'red'))

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
        fcal_name = fields[key][0]
        print(colored('The flux calibrator is ' + str(fcal_name) + '.', 'red'))
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
                    print(colored(fields[key2][0] + ' is the phase calibrator for ' + fields[key][0], 'red'))
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

FGC.write_dependencies('1GC_.py')

vislist = []
for key in fields:
    if fields[key][1] == 'TARGET':
        target_field_id = key
        tm = table(mydata)
        t = table(mydata + '/SOURCE')
        for i, item in enumerate(t.getcol('NAME')):
            if item == fields[key][0]:
                target_name = item
                x = t.getcol('SPECTRAL_WINDOW_ID')[i]
                y = [key, field_matching[fields[key][0]], fcal_field[0]]
                t1 = casacore.tables.taql('SELECT FROM $tm WHERE (DATA_DESC_ID IN [SELECT SPECTRAL_WINDOW_ID FROM ::DATA_DESCRIPTION WHERE SPECTRAL_WINDOW_ID == $x])')
                t2 = casacore.tables.taql('SELECT FROM $t1 WHERE FIELD_ID IN $y')
                newdir  = '/'.join(mydata.split('/')[:-1]) + '/' + fields[key][0] + '_' + 'spw' + str(x) + '/'
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
                imsize = int(2. ** (math.ceil(np.log2(imsize)) + 2))

                FGC.write_comments('1GC_.py', item, x)

                FGC.first_generation_calibration(outfile,
                                                 item,
                                                 fcal_name,
                                                 fields[field_matching[item]][0],
                                                 '1GC_.py',
                                                 newdir + 'CALIBRATION_TABLES/')

                FGC.image_all_fields(outfile,
                                     key,
                                     fcal_field[0],
                                     field_matching[fields[key][0]],
                                     item,
                                     fcal_name,
                                     fields[field_matching[item]][0],
                                     'image_.sh',
                                     imsize,
                                     cell,
                                     newdir + 'IMAGES/')

        t.close()
        tm.close()

deep_dir = '/'.join(mydata.split('/')[:-1]) + '/' + '/DEEP_IMAGE/'
os.mkdir(deep_dir)

FGC.deep_image(
    vislist,
    target_field_id,
    'image_.sh',
    imsize,
    cell,
    deep_dir,
    target_name)

FGC.flag_u0(
    vislist,
    '1GC_.py')
