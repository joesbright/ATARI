import numpy as np


def channel_selection(spw_id, flagged):
    # A CASA spw selection such as '3:0~3;12~27' that leaves out the channels
    # flagged in every row (flagged[i] is True for those), e.g. tunings filled
    # in by uvh5_files.read_lo. Empty if there are none to leave out, or if
    # every channel is flagged.
    flagged = np.asarray(flagged, dtype=bool)
    if not flagged.any() or flagged.all():
        return ''
    ranges = []
    start = None
    for i, f in enumerate(list(flagged) + [True]):
        if not f and start is None:
            start = i
        elif f and start is not None:
            ranges.append(str(start) + '~' + str(i - 1))
            start = None
    return str(spw_id) + ':' + ';'.join(ranges)


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
                  append=False,
                  spw=''):
    
    f = open(script_name, 'a')

    args = 'vis=\''
    args += vis + '\','
    args += 'field=\''
    args += str(field) + '\','
    if spw != '':
        args += 'spw=\''
        args += spw + '\','
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
                   bandtype='B',
                   combine=None):
    # combine=None leaves CASA's default (combine='scan': one bandpass
    # averaged over every scan); combine='' solves once per scan.
    
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
    if combine is not None:
        args += ',combine=\'' + combine + '\''

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


def write_flagdata(vis, script_name, datacolumn=None):
    # tfcrop then rflag on all fields. datacolumn=None leaves CASA's default
    # (DATA, the uncalibrated data); 'corrected' flags the calibrated data,
    # where antenna gain and bandpass differences no longer hide outliers.
    column = '' if datacolumn is None else ',datacolumn=\'' + datacolumn + '\''

    f = open(script_name, 'a')

    args = 'vis=\''
    args += vis + '\','
    args += 'mode=\'tfcrop\''

    f.write('flagdata(' + args + column + ')\n')


    args = 'vis=\''
    args += vis + '\','
    args += 'mode=\'rflag\''

    f.write('flagdata(' + args + column + ')\n')
    f.close()


def write_flag_antennas(vis, antenna, script_name):

    f = open(script_name, 'a')

    args = 'vis=\''
    args += vis + '\','
    args += 'mode='
    args += '\'manual\','
    args += 'antenna=\''
    args += antenna + '\''

    f.write('flagdata(' + args + ')\n')
    f.close()
