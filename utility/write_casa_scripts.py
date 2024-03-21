def write_mstransform(vis, 
                      outputvis, 
                      antenna, 
                      script_name):
    
    f = open(script_name, 'a')

    args = 'vis='
    args += vis + ','
    args += 'outputvis'

    f.write('mstransform(' + args + ')')
    f.close()
    return


def write_setjy(vis, 
                field, 
                script_name):
    
    f = open(script_name, 'a')
    f.write('#####' + str(vis) + '#####\n')

    args = 'vis=\''
    args += vis + '\','
    args += 'field=\''
    args += str(field) + '\','
    args += 'standard='
    args += '\'Perley-Butler 2017\','
    args += 'usescratch='
    args += 'True'

    f.write('setjy(' + args + ')\n')
    f.close()
    return


def write_gaincal(vis, 
                  caltable, 
                  field, 
                  refant, 
                  calmode, 
                  solint, 
                  script_name,
                  outdir,
                  gaintype='G', 
                  gaintable=[], 
                  append=False,):
    
    f = open(script_name, 'a')

    args = 'vis=\''
    args += vis + '\','
    args += 'field=\''
    args += str(field) + '\','
    args += 'refant=\''
    args += refant + '\','
    args += 'calmode=\''
    args += calmode + '\','
    args += 'solint=\''
    args += solint + '\','
    args += 'gaintype=\''
    args += gaintype + '\','
    args += 'caltable=\''
    args += outdir + caltable + '\','  
    args += 'gaintable=['
    if len(gaintable) == 0:
        args += '],'
    else:
        for i, item in enumerate(gaintable):
            if i == len(gaintable) - 1:
                args += '\'' + outdir + str(item) + '\'],'
            else:
                args += '\'' + outdir + str(item) + '\','  
    args += 'append='
    args += str(append) + ''

    f.write('gaincal(' + args + ')\n')
    f.close()
    return

def write_bandpass(vis, 
                   caltable, 
                   field, 
                   refant, 
                   calmode, 
                   solint, 
                   script_name,
                   outdir,
                   gaintype='G', 
                   gaintable=[], 
                   bandtype='B'):
    
    f = open(script_name, 'a')

    args = 'vis=\''
    args += vis + '\','
    args += 'field=\''
    args += str(field) + '\','
    args += 'refant=\''
    args += refant + '\','
    args += 'solint=\''
    args += solint + '\','
    args += 'caltable=\''
    args += outdir + caltable + '\','
    args += 'gaintable=['
    for i, item in enumerate(gaintable):
        if i == len(gaintable) - 1:
            args += '\'' + outdir + str(item) + '\'],'
        else:
            args += '\'' + outdir + str(item) + '\','
    args += 'bandtype=\''
    args += bandtype + '\''

    f.write('bandpass(' + args + ')\n')
    f.close()
    return

def write_fluxscale(vis, caltable, fluxtable, reference, transfer, script_name, outdir):

    f = open(script_name, 'a')

    args = 'vis=\''
    args += vis + '\','
    args += 'caltable=\''
    args += outdir + caltable + '\','
    args += 'fluxtable=' + '\''
    args += outdir + fluxtable + '\','
    args += 'reference=' + '\''
    args += str(reference) + '\','
    args += 'transfer=' + ''
    args += str(transfer) + ''

    f.write('fluxscale(' + args + ')\n')
    f.close()

    return

def write_applycal(vis, field, gaintable, gainfield, interp, calwt, script_name, outdir):

    f = open(script_name, 'a')

    args = 'vis=\''
    args += vis + '\','
    args += 'field=\''
    args += str(field) + '\','
    args += 'gaintable=['
    for i, item in enumerate(gaintable):
        if i == len(gaintable) - 1:
            args += '\'' + outdir + str(item) + '\'],'
        else:
            args += '\'' + outdir + str(item) + '\','
    args += 'gainfield='
    args += str(gainfield) + ','
    args += 'interp='
    args += str(interp) + ','
    args += 'calwt='
    args += calwt + ''



    f.write('applycal(' + args + ')\n')
    f.close()
