import sys
import os
sys.path.insert(0, os.path.abspath('../utility'))
import write_casa_scripts

def first_generation_calibration(myms,
                                 target,
                                 flux_cal,
                                 phase_cal,
                                 script_name, 
                                 outdir):

    # set the flux density scale assuming standard flux calibrators 
    write_casa_scripts.write_setjy(myms, flux_cal, script_name)
    write_casa_scripts.write_gaincal(myms, 'test.G0', flux_cal, '3', 'p', 'inf', script_name, outdir)
    write_casa_scripts.write_gaincal(myms, 'test.K0', flux_cal, '3', 'ap', 'inf', script_name, outdir, gaintable=['test.G0'], gaintype='K')
    write_casa_scripts.write_bandpass(myms, 'test.B0', flux_cal, '3', 'B', 'inf', script_name, outdir, gaintable=['test.G0','test.K0'])
    write_casa_scripts.write_gaincal(myms, 'test.G1', flux_cal, '3', 'p', 'inf', script_name, outdir, gaintable=['test.G0','test.B0','test.K0'])
    write_casa_scripts.write_gaincal(myms, 'test.G1', phase_cal, '3', 'p', 'inf', script_name, outdir, gaintable=['test.G0','test.B0','test.K0'], append='True')
    write_casa_scripts.write_fluxscale(myms, 'test.G1', 'test.fluxscale', flux_cal, [str(phase_cal)], script_name, outdir)
    write_casa_scripts.write_applycal(myms, flux_cal, ['test.fluxscale','test.K0','test.B0','test.G0'], [str(flux_cal), '',''], ['nearest','',''], 'False', script_name, outdir)

    return None

def image_gaincal():
    
    return None