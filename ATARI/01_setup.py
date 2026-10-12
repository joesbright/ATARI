# Kept so the old `python 01_setup.py <data>` usage still works.
# The pipeline itself lives in src/atari/pipeline.py.
import runpy

runpy.run_module('atari.pipeline', run_name='__main__')
