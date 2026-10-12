import os
import sys
import logging
import numpy as np
from astropy.coordinates import SkyCoord
from astropy import units as u
from casacore.tables import table
import casacore.tables
from atari import fgc as FGC
import scipy as sp
import math
from atari import fix_scans
from atari.calibrators import classify_field
from atari.cli import parse_args, resolve_refant
from atari.uvh5_files import find_converted_ms, find_time_ids, read_lo
from atari.write_casa_scripts import channel_selection, write_flag_antennas
import glob
from functools import partial
from termcolor import colored
import multiprocessing


def antenna_ids(ant_names, flagants):
    # The row numbers of the named antennas, as CASA's antenna selection
    # expects, e.g. '0,5'. Empty if none of them are in the MS.
    return ','.join(str(i) for i in range(len(ant_names)) if ant_names[i] in flagants)


def flagged_everywhere(myms):
    # For each channel, whether it is flagged in every row and polarisation
    # of myms (which holds a single spw). Read in chunks of rows, since FLAG
    # for a full observation is large.
    with table(myms) as t:
        flagged = None
        for start in range(0, t.nrows(), 100000):
            chunk = t.getcol('FLAG', startrow=start, nrow=100000).all(axis=(0, 2))
            flagged = chunk if flagged is None else flagged & chunk
    return flagged


def parallel_file_conversion(timeID, mydata):

    for folder in glob.glob(mydata + '/uvh5*' + timeID + '*0001/'):

        # LoA-LoD become spw0-spw3 in this order (see find_converted_ms).
        for lo in ['LoA', 'LoB', 'LoC', 'LoD']:
            msname = folder.rstrip('/') + '_' + lo + '.ms'
            if os.path.isdir(msname):
                continue
            uvd = read_lo(folder, lo)
            if uvd is None:
                # This LO was not recorded.
                continue
            uvd.write_ms(msname)
            fix_scans.fix_spw(msname)

    return None


def main(argv=None):
    cwd = os.getcwd()
    logging.info('Working from ' + str(cwd))

    # clean up previous run
    os.system('rm 1GC_.py')
    os.system('rm image_.sh')
    os.system('rm avg_command.py')
    os.system('rm concat_command.py')
    os.system('rm concat_avg_commands.py')

    args = parse_args(argv)

    mydata = args.msname
    casapath = args.casapath
    chanbin = args.chanbin
    flagants = args.flagants

    if len(mydata) != 1:
        print(colored('Only one dataset should be given. Exiting.', 'red'))
    mydata = mydata[0]

    # different file managing depending on input, but we want to end up with a measurement set
    # with a consistent file structure.
    if os.path.isdir(mydata) == True and mydata.endswith('.ms') == False and mydata.endswith('.ms/') == False:
        print(colored('Starting with folder: ' + mydata + '.', 'red'))
        # CONVERT TO MEASUREMENT SET FIRST
        timeIDs = find_time_ids(mydata)

        with multiprocessing.Pool() as pool:
            results = pool.map(partial(parallel_file_conversion, mydata=mydata), timeIDs)

        final_concat = find_converted_ms(mydata)

        print(colored('Combining spectral chunks.', 'red'))

        with table(final_concat[0] + '/ANTENNA/') as t:
            ant_names = t.getcol('NAME')

        flagants = antenna_ids(ant_names, flagants)

        f = open('concat_command.py', 'w')
        f.write('concat(vis=' + str(final_concat) + ', concatvis=\'' + mydata + '/master_ms_tmp.ms\')')
        if flagants != '':
            f.write('\n')
            f.write('mstransform(vis=\'' + mydata + '/master_ms_tmp.ms\', outputvis=\'' + mydata + '/master_ms_tmp2.ms\', antenna=\'!' + flagants + '\', datacolumn=\'DATA\')')
        f.close()
        os.system(casapath + ' --nologger --log2term --nologfile -c concat_command.py')

        if flagants != '':
            os.system('aoflagger ' + mydata + '/master_ms_tmp2.ms')
        else:
            os.system('aoflagger ' + mydata + '/master_ms_tmp.ms')

        if flagants != '':
            fix_scans.fix_scans(mydata + '/master_ms_tmp2.ms')
        else:
            fix_scans.fix_scans(mydata + '/master_ms_tmp.ms')

        f = open('avg_command.py', 'w')
        if flagants != '':
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

        flagants = antenna_ids(ant_names, flagants)

        if flagants != '':
            # write_flag_antennas appends, so start from an empty file.
            os.system('rm -f flag_command.py')
            write_flag_antennas(mydata, flagants, 'flag_command.py')
            os.system(casapath + ' --nologger --log2term --nologfile -c flag_command.py')
            os.system('rm flag_command.py')
        print(colored('Starting with measurement set: ' + mydata + '.', 'red'))

    else:
        logging.error('Unexpected input data type.')

    myms = mydata

    # Look the reference antenna up in the measurement set that is
    # calibrated, i.e. after any --flagants antennas were removed.
    with table(myms + '/ANTENNA/') as t:
        ant_names = t.getcol('NAME')
    try:
        refant = resolve_refant(args.refant, ant_names, args.flagants)
    except ValueError as e:
        sys.exit(colored(str(e), 'red'))
    print(colored('Reference antenna: ' + ant_names[int(refant)] + ' (index ' + refant + ').', 'red'))

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
        kind = classify_field(fields[key], args.calibrators)
        fields[key] = [fields[key], kind]
        if kind == 'FLUX_CAL':
            fcal_name = fields[key][0]
            print(colored('The flux calibrator is ' + str(fcal_name) + '.', 'red'))
            myintents.append('#FCAL')
        elif kind == 'PHASE_CAL':
            myintents.append('#GCAL')
        elif kind == 'TARGET':
            myintents.append('#TARGET')
        else:
            print(colored('Skipping field ' + fields[key][0] + '.', 'red'))

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
                                                     refant,
                                                     '1GC_.py',
                                                     newdir + 'CALIBRATION_TABLES/',
                                                     g1_spw=channel_selection(x, flagged_everywhere(outfile)))

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


if __name__ == '__main__':
    main()
