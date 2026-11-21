# Briggs robust weighting for every image. Chosen from a sweep on 2026-09-18
# p060 (28 antennas, after flagging the calibrated data and statwt; robust 0.3
# to 1.3 in steps of 0.1): 0.7 was within 0-2.6% of the lowest noise at 3, 5
# and 7 GHz, while 0.5 was 1.8-7.6% worse and natural weighting was never best.
# Worth re-checking when the array or its uv coverage changes.
BRIGGS_ROBUST = 0.7


def write_wsclean(vis, 
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
    
    f = open(script_name, 'a')
    f.write('#####' + str(vis) + '#####\n')

    # The target, every flux calibrator (field IDs and names, in the same
    # order; a single one may be given on its own) and the gain calibrator.
    if not isinstance(flux_cals, (list, tuple)):
        flux_cals, flux_cal_names = [flux_cals], [flux_cal_names]
    names = [target_name] + list(flux_cal_names) + [phase_cal_name]
    for i, field in enumerate([target] + list(flux_cals) + [phase_cal]):

        args = 'wsclean '
        args += '-niter 50000 '
        args += '-size ' + str(size) + ' ' + str(size) + ' '
        args += '-scale ' + str(scale) + 'asec '
        args += '-field ' + str(field) + ' '
        args += '-reorder '
        args += '-name ' + outdir + str(names[i]) + '_automask '
        args += '-data-column CORRECTED_DATA '
        args += '-join-channels '
        args += '-channels-out 4 '
        args += '-fit-spectral-pol 2 '
        args += '-weight briggs ' + str(BRIGGS_ROBUST) + ' '
        args += '-mgain 0.7 '
        args += '-local-rms '
        args += '-auto-mask 5 '
        args += '-auto-threshold 1 '
        args += '-multiscale '
        args += '-multiscale-scales 0,3,9 '
        args += vis

        f.write(args + '\n')
    f.close()
        
    return None

def write_deep_image(vislist,
               field,
               script_name,
               size,
               scale,
               outdir,
               target_name):
    
    f = open(script_name, 'a')
    args = 'wsclean '
    args += '-niter 50000 '
    args += '-size ' + str(size) + ' ' + str(size) + ' '
    args += '-scale ' + str(scale) + 'asec '
    args += '-field ' + str(field) + ' '
    args += '-reorder '
    args += '-name ' + outdir + str(target_name) + '_automask '
    args += '-data-column CORRECTED_DATA '
    args += '-join-channels '
    args += '-channels-out 4 '
    args += '-fit-spectral-pol 2 '
    args += '-weight briggs ' + str(BRIGGS_ROBUST) + ' '
    args += '-mgain 0.7 '
    args += '-local-rms '
    args += '-auto-threshold 5 '
    args += '-auto-mask 5 '
    args += '-auto-threshold 1 '
    args += '-multiscale '
    args += '-multiscale-scales 0,3,9 '
    args += ' '.join(vislist)

    f.write(args + '\n')    
    
    return None