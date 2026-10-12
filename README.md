# Allen Telescope Array Radio Imaging (ATARI)
Calibration pipeline for reducing and imaging correlator data taken with the Allen Telescope Array (ATA)

![image](https://github.com/user-attachments/assets/739ec7e0-c5f0-4b7f-bb47-1c7aceb0775a)

Requirements:
- [uv](https://docs.astral.sh/uv/), which installs Python >= 3.10 and the Python libraries ATARI needs
- [CASA](https://casa.nrao.edu/)
- [WSClean](https://wsclean.readthedocs.io/)
- [aoflagger](https://aoflagger.readthedocs.io/) (only needed for uvh5 input)

# Installation
ATARI's Python dependencies are listed in `pyproject.toml` and pinned to exact versions in `uv.lock`. To set them up, clone this repository and run, from the repository folder:

```bash
uv sync
```

This creates a `.venv` folder containing a suitable Python and the exact library versions in `uv.lock`. CASA, WSClean and aoflagger are separate programs and must be installed separately.

`python-casacore` only has ready-made builds on PyPI for Linux on x86_64 (such as the ATA compute nodes). On other systems, including macOS, `uv sync` tries to compile it and needs the casacore C++ library installed first. The easier route on macOS (including Apple Silicon) is [conda-forge](https://conda-forge.org/), which has ready-made builds: `conda install -c conda-forge python-casacore`, or the same with `micromamba`.

# Example Usage
In the current iteration of ATARI the following steps are taken:
1. Clone this git repository to a machine of your choice.
2. Move a measurement set from the ATA to a folder in the `data` repository.
3. From anywhere inside the repository, run `uv run atari-setup <PATH_TO_YOUR_MEASUREMENT_SET> --refant <ANTENNA>`. `--refant` is required and sets the reference antenna for calibration, either by name (e.g. `1c`) or by its index in the measurement set's ANTENNA table (e.g. `3`). This will create the `1GC_.py` and `image_.sh` files in the folder you ran it from. (The old `cd ATARI; uv run python 01_setup.py <PATH>` still works. If you activate the environment with `source .venv/bin/activate`, plain `atari-setup` works from any folder.)
4. Run `casa -c 1GC_.py`. This will split your data by spectral window, target field, with matching calibrators. Note, you might have to tell ATARI about your gain calibrator (see below).
5. Run `. image_.sh`. This will create images of all fields per spectral window, and a combined image of the target field with all spectral windows.

Alternatively, if you are running the pipeline on the ATA compute nodes, you can instead create a symlink (`ln -s <PATH_TO_DATA> <PATH_TO_SYMLINK`) and use `uv run atari-setup <PATH_TO_YOUR_SYMLINK> --refant <ANTENNA>` and ATARI will handle the conversion from uvh5 to measurement set format. If you are running it on the ATA machines you need to pass the `--casapath` flag giving the path to casa.

One can inspect the contents of `1GC_.py` and `image_.sh` to see exactly what they have done. The first contains a series of CASA commands whereas the second contains a series of WSClean commands.

Note: ATARI relies on a built-in list of calibrator names (`src/atari/data/calibrator_names.dat`) to identify the complex gain calibrator (sometimes called the gain calibrator, or phase calibrator). If your complex gain calibrator is not listed, put its name in a text file, one name per line, and pass it with `--calibrators <FILE>`. It is used alongside the built-in list.

Scans named `Stay_put` (in any capitalisation) are recorded while the sources are below the horizon, and are skipped completely: they are not converted, calibrated or imaged.

## Options
| Option | Required | Meaning |
|---|---|---|
| `--refant <ANTENNA>` | yes | Reference antenna for calibration, by name (e.g. `1c`) or by index in the measurement set's ANTENNA table (e.g. `3`). It must not also be in `--flagants`. |
| `--casapath <PATH>` | no | The CASA program to run (default `casa`). Needed when `casa` is a shell alias, as on the ATA compute nodes. |
| `--flagants <NAMES>` | no | Comma-separated antenna names to remove, e.g. `1a,2b`. For uvh5 input they are dropped from the data; for a measurement set they are flagged. |
| `--chanbin <N>` | no | Number of 0.5 MHz channels to average together when converting uvh5 input (default `8`). |
| `--calibrators <FILE>` | no | Extra gain calibrator names, one per line, used alongside the built-in list. |

# Outputs
ATARI will make folders per source and per spectral window in the `data` folder, which will contain calibration tables, IMAGES, and plots, as well as the calibrated measurement set, for the specific source/spectral window. ATARI will match sources with complex gain calibrators based on the calibrator list and the target position. The assumption is that the closest calibrator to the target is the complex gain calibrator.

# Testing
```bash
uv run pytest -rs
```

The quick tests check the generated CASA and WSClean commands and run anywhere. `tests/test_pipeline.py` runs `atari-setup` on a small ATA observation and compares the generated scripts with known-good copies in `tests/data/expected/`, by two routes:
- from the measurement set `tests/data/master_ms.ms`, which needs python-casacore;
- from the uvh5 files in `tests/data/uvh5/`, which also needs CASA and aoflagger. If `casa` is a shell alias, give the path with `ATARI_CASAPATH`, e.g. on the ATA nodes:

```bash
ATARI_CASAPATH=/home/sonata/src/casa-6.6.0-20/bin/casa uv run pytest -rs
```

Tests whose requirements are missing are skipped and listed by `-rs`. GitHub Actions runs the suite on Linux for every push and pull request; there the uvh5 route is skipped.

# Software and References

# Feedback and Future Developments
Please feel free to open issues on the github with bugs, errors, and feature suggestions.

## Planned changes

1. Include singularity containerisation to avoid version issues.
2. Include automated self-calibration.
3. Smart combining of spectral windows for deep imaging.