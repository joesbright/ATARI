from importlib.resources import files

# Compared in lower case, since observations name them e.g. 3c48 or 3C48.
FLUX_CALIBRATORS = {'3c286', '3c48', '3c147'}

# Scans that are not calibrated or imaged at all, compared in lower case.
# Stay_put scans are recorded while the sources are below the horizon.
SKIP_FIELDS = {'stay_put'}


def skip_field(source):
    return source.lower() in SKIP_FIELDS


def classify_field(source, extra_calibrators=None):
    # One of 'FLUX_CAL', 'PHASE_CAL', 'TARGET' or 'SKIP'.
    if skip_field(source):
        return 'SKIP'
    if source.lower() in FLUX_CALIBRATORS:
        return 'FLUX_CAL'
    if match_calibrators(source, extra_calibrators):
        return 'PHASE_CAL'
    return 'TARGET'


def calibrator_problems(sources, extra_calibrators=None):
    # What is missing for calibration among the observed sources, as
    # messages for the user. Empty if there is a flux and a gain calibrator.
    kinds = [classify_field(source, extra_calibrators) for source in sources]
    problems = []
    if 'FLUX_CAL' not in kinds:
        problems.append('No flux calibrator found (looked for '
                        + ', '.join(sorted(FLUX_CALIBRATORS)) + ', in any case).')
    if 'PHASE_CAL' not in kinds:
        problems.append('No gain calibrator found in the calibrator list. '
                        'If one was observed, give its name in a file with --calibrators.')
    return problems


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
