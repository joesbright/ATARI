# general useful functions

def get_unique_ants(msname):
    tb.open(msname)
    antenna = tb.getcol('ANTENNA1')
    unique_antenna = list(set(tb.getcol('ANTENNA1')))
    unique_antenna = [str(i) for i in unique_antenna]
    return ','.join(unique_antenna)
