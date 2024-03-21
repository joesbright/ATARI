# name of measurement set as input
myms = 'myms'
mybpcal = 'mybpcal'

# need to consider pairs of target/calibrator/per spw etc. WANT TO DO THIS PER SPW

# flag top and bottom 5% of each SPW to account for the rolloff

# generic autoflagging? Flag known RFI bands?

setjy(vis=myms, field=mybpcal, standard='Perley-Butler 2017', usescratch=True)

 # solve for gain variations over time before solving for the bandpass to avoid de-correlation
gaincal(vis=myvis, caltable=bpcal+'.G0', field=bpcal, refant=myrefant, calmode='p', solint='inf')
gaincal(vis=myvis, caltable=bpcal+'.K0', field=bpcal, refant=myrefant, gaintype='K', solint='inf', combine='scan', gaintable=[bpcal+'.G0'])
bandpass(vis=myvis, caltable=bpcal+'.B0', field=bpcal, refant=myrefant, combine='scan', solint='inf', bandtype='B', gaintable=[bpcal+'.K0', bpcal+'.G0'])
gaincal(vis=myvis, caltable=bpcal+'.G1', field=bpcal, refant=myrefant, solint='inf', calmode='ap', gaintable=[bpcal+'.K0', bpcal+'.B0', bpcal+'.G0'])

# LOOP OVER TARGET/CAL PAIRS to calibrate this next step

# gaincal(vis=myvis, caltable=bpcal+'.G1', field=pcal, refant=myrefant, solint='inf', calmode='ap', gaintable=[bpcal+'.K0', bpcal+'.B0', bpcal+'.G0'], append=True)
#if 'fluxtable' in dosteps:
 #   fluxscale(vis=myvis, caltable=bpcal+'.G1', fluxtable=bpcal+'.fluxscale', reference=bpcal, transfer=[pcal])