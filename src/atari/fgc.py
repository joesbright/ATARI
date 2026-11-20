from atari import write_casa_scripts
from atari import write_wsclean_scripts


def write_comments(script_name, target, spw):

    f = open(script_name, 'a')
    f.write('##### ' + str(target) + ' : Spectral Window ' + str(spw) + ' ######\n')
    f.close()


def write_dependencies(script_name):

    f = open(script_name, 'a')
    f.write('import numpy as np\n\n')
    f.close()


def first_generation_calibration(myms,
                                 target,
                                 flux_cal,
                                 phase_cal,
                                 refant,
                                 script_name, 
                                 outdir,
                                 g1_spw=''):
    # g1_spw (from write_casa_scripts.channel_selection) leaves channels
    # with no data out of the G1 solves: fluxscale reports each spw's flux
    # density at the centre of G1's selected channels, flagged or not.
    
    G0_table = str(flux_cal) + '.G0'
    K0_table = str(flux_cal) + '.K0'
    B0_table = str(flux_cal) + '.B0'
    G1_table = str(flux_cal) + '.G1'
    flux_table = str(flux_cal) + '.fluxscale'

    # B0 is solved once per flux-calibrator scan (combine='') and applied with
    # linear interpolation in time, so a bandpass that drifts over a long
    # track is followed rather than averaged (issue #30). With a single
    # flux-calibrator scan this is the same as before.

    # set the flux density scale assuming standard flux calibrators 
    write_casa_scripts.write_flagdata(myms, script_name)
    write_casa_scripts.write_setjy(myms, flux_cal, script_name)
    write_casa_scripts.write_gaincal(myms, G0_table, flux_cal, refant, 'p', 'int', script_name, outdir)
    write_casa_scripts.write_gaincal(myms, K0_table, flux_cal, refant, 'ap', 'inf', script_name, outdir, gaintable=[G0_table], gaintype='K')
    write_casa_scripts.write_bandpass(myms, B0_table, flux_cal, refant, 'B', 'inf', script_name, outdir, gaintable=[G0_table,K0_table], combine='')
    write_casa_scripts.write_gaincal(myms, G1_table, flux_cal, refant, 'ap', 'inf', script_name, outdir, gaintable=[G0_table,B0_table,K0_table], spw=g1_spw)
    write_casa_scripts.write_gaincal(myms, G1_table, phase_cal, refant, 'ap', 'inf', script_name, outdir, gaintable=[G0_table,B0_table,K0_table], append='True', spw=g1_spw)
    write_casa_scripts.write_fluxscale(myms, G1_table, flux_table, flux_cal, [str(phase_cal)], script_name, outdir)
    write_casa_scripts.write_applycal(myms, flux_cal, [flux_table,K0_table,B0_table,G0_table], [str(flux_cal), '',''], ['nearest','','linear'], 'False', script_name, outdir)
    write_casa_scripts.write_applycal(myms, phase_cal, [flux_table,K0_table,B0_table,G0_table], [str(phase_cal), '',''], ['nearest','','linear'], 'False', script_name, outdir)
    write_casa_scripts.write_applycal(myms, target, [flux_table,K0_table,B0_table,G0_table], [str(phase_cal), '',''], ['linear','','linear'], 'False', script_name, outdir)
    # Flag the calibrated data, which is what gets imaged (on 2026-09-18 p060
    # this lowered the image noise 1.8-2.9x; flux scale unchanged).
    write_casa_scripts.write_flagdata(myms, script_name, datacolumn='corrected')
    # Last, after all calibration and flagging: weight the target's
    # visibilities by their measured noise (on 2026-09-18 p060 this lowered
    # the image noise a further 8-36%, with fluxes unchanged to 0.1%).
    write_casa_scripts.write_statwt(myms, target, script_name)

    return None


def image_all_fields(myms,
                  target,
                  flux_cal,
                  phase_cal,
                  target_name,
                  flux_cal_name,
                  phase_cal_name,
                  script_name,
                  size,
                  scale,
                  outdir):
    
    write_wsclean_scripts.write_wsclean(myms, target, flux_cal, phase_cal, target_name, flux_cal_name, phase_cal_name, script_name, size, scale, outdir)
    
    return None


def deep_image(vislist,
               field,
               script_name,
               imsize,
               cell,
               outdir,
               target_name):
    
    write_wsclean_scripts.write_deep_image(vislist, field, script_name, imsize, cell, outdir, target_name)
    
    return None
