import numpy as np


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


def write_setjy(vis, 
                field, 
                script_name):
    
    f = open(script_name, 'a')

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


def write_flagdata(vis, script_name):

    f = open(script_name, 'a')

    args = 'vis=\''
    args += vis + '\','
    args += 'mode=\'tfcrop\''

    f.write('flagdata(' + args + ')\n')


    args = 'vis=\''
    args += vis + '\','
    args += 'mode=\'rflag\''

    f.write('flagdata(' + args + ')\n')
    f.close()


def write_u0_flag(vislist, script_name):
    
    for myms in vislist:

        f = open(script_name, 'a')

        for myfield in range(3):
            f.write('tb.open(\'' + str(myms)+ '\')\n')
            f.write('tmp_table = tb.query(\'FIELD_ID==' + str(myfield) + '\')\n')
            f.write('visdata = tmp_table.getcol(\'CORRECTED_DATA\')\n')
            f.write('tb.close()\n')
            f.write('tmp_table.close()\n')
            f.write('xx_amp = abs(visdata[0,:,:])\n')
            f.write('xx_99 = np.percentile(xx_amp, 99)\n')
            f.write('yy_amp = abs(visdata[3,:,:])\n')
            f.write('yy_99 = np.percentile(yy_amp, 99)\n')
            f.write('myclipmax = np.min([xx_99, yy_99])\n')

            args = 'vis=\''
            args += myms + '\','
            args += 'mode=\'clip\','
            args += 'clipoutside=True,'
            args += 'clipminmax=[0,myclipmax],'
            args += 'datacolumn=\'CORRECTED\','
            args += 'field=\'' + str(myfield) + '\''

            f.write('flagdata(' + args + ')\n')
        f.close()
        