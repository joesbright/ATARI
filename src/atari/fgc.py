from atari import write_casa_scripts
from atari.calibrators import flux_reference
from atari import write_wsclean_scripts

# Data above this elevation (degrees) are flagged before calibration (issue
# #48): the ATA antennas cannot point above 87 degrees (confirmed with ATA
# staff, 2026-11-23; not in the published literature, which gives only the
# 17 degree lower limit). On 2026-11-06 p060 a gain-calibrator scan at
# 88-89 degrees lost the source on every antenna, and its bad gains spoiled
# the target scans either side through the interpolation in time.
ELEVATION_LIMIT = 87


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
                                 flux_cals,
                                 phase_cal,
                                 refant,
                                 script_name, 
                                 outdir,
                                 g1_spw=''):
    # g1_spw (from write_casa_scripts.channel_selection) leaves channels
    # with no data out of the G1 solves: fluxscale reports each spw's flux
    # density at the centre of G1's selected channels, flagged or not.
    
    # flux_cals: the flux calibrators' names, in field order. Many tracks
    # observe one at each end (e.g. 3C286 then 3C147; issue #44) so that the
    # bandpass is calibrated at both ends of a long track: each gets its own
    # model (setjy), and the delays and bandpass are solved on all of them,
    # once per scan, and interpolated in time (on 2026-10-27 and 11-06 p060
    # the bandpass shape changed by 1.5-4% rms in amplitude and ~2 deg in
    # phase between the two ends). The bandpass is normalised (solnorm), so it
    # carries only the shape and G1 all the amplitude; the flux scale then
    # comes from fluxscale alone, referenced to the most stable flux
    # calibrator (calibrators.flux_reference). The others are fluxscale
    # transfer fields: a check of their models. Their G1 was solved against
    # their own model, not 1 Jy, so the "flux density" fluxscale logs for them
    # is measured / model (1.0 = the model is right; 3C147 gave 0.95-1.19 on
    # 2026-10-27 and 11-06 p060).
    if isinstance(flux_cals, str):
        flux_cals = [flux_cals]
    flux_cals = [str(name) for name in flux_cals]
    flux_selection = ','.join(flux_cals)
    reference = flux_reference(flux_cals)
    transfer = [str(phase_cal)] + [name for name in flux_cals if name != reference]
    # Named after the flux calibrators: e.g. 3c48.G0, or 3C48_3C147.G0.
    stem = '_'.join(flux_cals)
    G0_table = stem + '.G0'
    K0_table = stem + '.K0'
    B0_table = stem + '.B0'
    G1_table = stem + '.G1'
    flux_table = stem + '.fluxscale'

    # B0 is solved once per flux-calibrator scan (combine='') and applied with
    # linear interpolation in time, so a bandpass that drifts over a long
    # track is followed rather than averaged (issue #30). With a single
    # flux-calibrator scan this is the same as before.

    write_casa_scripts.write_elevation_flag(myms, ELEVATION_LIMIT, script_name)
    # set the flux density scale assuming standard flux calibrators 
    write_casa_scripts.write_flagdata(myms, script_name)
    for flux_cal in flux_cals:
        write_casa_scripts.write_setjy(myms, flux_cal, script_name)
    write_casa_scripts.write_gaincal(myms, G0_table, flux_selection, refant, 'p', 'int', script_name, outdir)
    write_casa_scripts.write_gaincal(myms, K0_table, flux_selection, refant, 'ap', 'inf', script_name, outdir, gaintable=[G0_table], gaintype='K')
    write_casa_scripts.write_bandpass(myms, B0_table, flux_selection, refant, 'B', 'inf', script_name, outdir, gaintable=[G0_table,K0_table], combine='', solnorm=True)
    write_casa_scripts.write_gaincal(myms, G1_table, flux_selection, refant, 'ap', 'inf', script_name, outdir, gaintable=[G0_table,B0_table,K0_table], spw=g1_spw)
    write_casa_scripts.write_gaincal(myms, G1_table, phase_cal, refant, 'ap', 'inf', script_name, outdir, gaintable=[G0_table,B0_table,K0_table], append='True', spw=g1_spw)
    write_casa_scripts.write_fluxscale(myms, G1_table, flux_table, reference, transfer, script_name, outdir)
    # Each flux calibrator with its own gain solutions.
    for flux_cal in flux_cals:
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
                  flux_cals,
                  phase_cal,
                  target_name,
                  flux_cal_names,
                  phase_cal_name,
                  script_name,
                  size,
                  scale,
                  outdir):
    
    write_wsclean_scripts.write_wsclean(myms, target, flux_cals, phase_cal, target_name, flux_cal_names, phase_cal_name, script_name, size, scale, outdir)
    
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
