# Allen Telescope Array Radio Imaging (ATARI)
Calibration pipeline for reducing and imaging correlator data taken with the Allen Telescope Array (ATA)

Requirements:
Python >= 3.8\
casa\
wasclean\
casacore

# Installation

# Example Usage
In the current iteration of ATARI the following steps are taken:
1. Clone this git repository to a machine of your choice.
2. Move a measurement set from the ATA to a folder in the `data` repository.
3. Run `python 01_setup.py <PATH_TO_YOUR_MEASUREMENT_SET>`. This will create the `1GC_.py` and `image_.sh` files.
4. Run `casa -c 1GC_.py`. This will split your data by spectral window, target field, with matching calibrators. Note, you might have to add the name of your calibrator to the `calibrator_names.dat` file in `data`.
5. Run `. image_.sh`. This will create images of all fields per spectral window, and a combined image of the target field with all spectral windows.

Alternatively, if you are running the pipeline on the ATA compute nodes, you can instead create a symlink (`ln -s <PATH_TO_DATA> <PATH_TO_SYMLINK`) and use `python 01_setup.py <PATH_TO_YOUR_SYMLINK>` and ATARI will handle the conversion from uvh5 to measurement set format. If you are running it on the ATA machines you need to pass the `--casapath` flag giving the path to casa.

One can inspect the contents of `1GC_.py` and `image_.sh` to see exactly what they have done. The first contains a series of CASA commands whereas the second contains a series of WSClean commands.

Note: ATARI relies on the `data/calibrator_names.dat` file to identify the complex gain calibrator (sometimes called the gain calibratior, or phase calibrator). If your complex gain calibrator is not listed, you can add it to the list manually.

# Outputs
ATARI will make folders per source and per spectral window in the `data` folder, which will contain calibration tables, IMAGES, and plots, as well as the calibrated measurement set, for the specific source/spectral window. ATARI will match sources with complex gain calibrators based on the calibrator list and the target position. The assumption is that the closest calibrator to the target is the complex gain calibrator.

# Software and References

# Feedback and Future Developments
Please feel free to open issues on the github with bugs, errors, and feature suggestions.

## Planned changes

1. Include singularity containerisation to avoid version issues.
2. Include automated self-calibration.
3. Smart combining of spectral windows for deep imaging.