def write_wsclean(vis, 
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
    
    f = open(script_name, 'a')
    f.write('#####' + str(vis) + '#####\n')

    names = [target_name, flux_cal_name, phase_cal_name]
    for i, field in enumerate([target, flux_cal, phase_cal]):

        args = 'wsclean '
        args += '-niter 5000 '
        args += '-size ' + str(size) + ' ' + str(size) + ' '
        args += '-scale ' + str(scale) + 'asec '
        args += '-field ' + str(field) + ' '
        args += '-reorder '
        args += '-name ' + outdir + str(names[i]) + '_automask '
        args += '-data-column CORRECTED_DATA '
        args += '-join-channels '
        args += '-channels-out 4 '
        args += '-fit-spectral-pol 2 '
        args += '-weight briggs 0.5 '
        args += '-mgain 0.7 '
        args += '-local-rms '
        args += '-auto-threshold 5 '
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
    args += '-niter 1000 '
    args += '-size ' + str(size) + ' ' + str(size) + ' '
    args += '-scale ' + str(scale) + 'asec '
    args += '-field ' + str(field) + ' '
    args += '-reorder '
    args += '-name ' + outdir + str(target_name) + '_automask '
    args += '-data-column CORRECTED_DATA '
    args += '-join-channels '
    args += '-channels-out 4 '
    args += '-fit-spectral-pol 2 '
    args += '-weight briggs 0.5 '
    args += '-mgain 0.7 '
    args += '-local-rms '
    args += '-auto-threshold 5 '
    args += ' '.join(vislist)

    f.write(args + '\n')    
    
    return None