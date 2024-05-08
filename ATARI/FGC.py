import sys
import os
sys.path.insert(0, os.path.abspath('../utility'))
import write_casa_scripts
import write_wsclean_scripts

def first_generation_calibration(myms,
                                 target,
                                 flux_cal,
                                 phase_cal,
                                 script_name, 
                                 outdir):
    
    G0_table = str(flux_cal) + '.G0'
    K0_table = str(flux_cal) + '.K0'
    B0_table = str(flux_cal) + '.B0'
    G1_table = str(flux_cal) + '.G1'
    flux_table = str(flux_cal) + '.fluxscale'

    # set the flux density scale assuming standard flux calibrators 
    write_casa_scripts.write_flagdata(myms, script_name)
    write_casa_scripts.write_setjy(myms, flux_cal, script_name)
    write_casa_scripts.write_gaincal(myms, G0_table, flux_cal, '3', 'p', 'int', script_name, outdir)
    write_casa_scripts.write_gaincal(myms, K0_table, flux_cal, '3', 'ap', 'inf', script_name, outdir, gaintable=[G0_table], gaintype='K')
    write_casa_scripts.write_bandpass(myms, B0_table, flux_cal, '3', 'B', 'inf', script_name, outdir, gaintable=[G0_table,K0_table])
    write_casa_scripts.write_gaincal(myms, G1_table, flux_cal, '3', 'ap', 'inf', script_name, outdir, gaintable=[G0_table,B0_table,K0_table])
    write_casa_scripts.write_gaincal(myms, G1_table, phase_cal, '3', 'ap', 'inf', script_name, outdir, gaintable=[G0_table,B0_table,K0_table], append='True')
    write_casa_scripts.write_fluxscale(myms, G1_table, flux_table, flux_cal, [str(phase_cal)], script_name, outdir)
    write_casa_scripts.write_applycal(myms, flux_cal, [flux_table,K0_table,B0_table,G0_table], [str(flux_cal), '',''], ['nearest','',''], 'False', script_name, outdir)
    write_casa_scripts.write_applycal(myms, phase_cal, [flux_table,K0_table,B0_table,G0_table], [str(phase_cal), '',''], ['nearest','',''], 'False', script_name, outdir)
    write_casa_scripts.write_applycal(myms, target, [flux_table,K0_table,B0_table,G0_table], [str(phase_cal), '',''], ['linear','',''], 'False', script_name, outdir)
    write_casa_scripts.write_flagdata(myms, script_name)

    return None

def image_all_fields(myms,
                  target,
                  flux_cal,
                  phase_cal,
                  script_name,
                  size,
                  scale,
                  outdir):
    
    write_wsclean_scripts.write_wsclean(myms, target, flux_cal, phase_cal, script_name, size, scale, outdir)
    
    return None

def deep_image(vislist,
               field,
               script_name,
               imsize,
               cell,
               outdir):
    
    write_wsclean_scripts.write_deep_image(vislist, field, script_name, imsize, cell, outdir)
    
    return None