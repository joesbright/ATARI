# Kept so the old `python 01_setup.py <data>` usage still works.
# The pipeline itself lives in src/atari/pipeline.py; once installed it can
# also be run from any folder as `atari-setup <data>`.
from atari.pipeline import main

if __name__ == '__main__':
    main()
