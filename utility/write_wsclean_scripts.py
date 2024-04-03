def write_wsclean(vis, 
                target,
                flux_cal,
                phase_cal, 
                script_name,
                size,
                scale,
                outdir):
    
    f = open(script_name, 'a')
    f.write('#####' + str(vis) + '#####\n')

    for field in [target, flux_cal, phase_cal]:

        args = 'wsclean '
        args += '-auto-mask 5 '
        args += '-niter 10000 '
        args += '-size ' + str(size) + ' ' + str(size) + ' '
        args += '-scale ' + str(scale) + 'asec '
        args += '-field ' + str(field) + ' '
        args += '-reorder '
        args += '-name ' + outdir + str(field) + '_automask '
        args += '-data-column CORRECTED_DATA '
        args += vis

        f.write(args + '\n')
    f.close()
        
    return None