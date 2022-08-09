def write_mstransform(vis, outputvis, antenna, script_name):
    f = open(script_name, 'w')

    args = 'vis='
    args += vis + ','
    args += 'outputvis'

    f.write('mstransform(' + args + ')')
    f.close()
    return
