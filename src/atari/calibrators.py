from importlib.resources import files


def match_calibrators(source, extra_calibrators=None):
    # The built-in list ships with the package. extra_calibrators is an
    # optional file of the user's own additions, in the same format.
    names = files('atari').joinpath('data/calibrator_names.dat').read_text()
    if extra_calibrators is not None:
        with open(extra_calibrators) as f:
            names += '\n' + f.read()

    iscal = False
    if source in names:
        iscal = True

    return(iscal)
