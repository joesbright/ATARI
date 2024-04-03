# Allen Telescope Array Radio Imaging
Calibration pipeline for reducing and imaging correlator data taken with the Allen Telescope Array (ATA)\

Requirements:
Python >= 3.8\
pyuvdata\
casa\
wasclean\
casacore\

# Installation

# Example Usage
In the current iteration of ATARI the following steps are taken:\
1. Clone this git repository to a machine of your choice.
2. Move a measurement set from the ATA to the `data` repository.
3. Run `python 01_setup.py <PATH_TO_YOUR_MEASUREMENT_SET>`. This will create the `1GC_.py` and `image_.sh` files.
4. Run `casa -c 1GC_.py`. This will split your data by spectral window, target field, with matching calibrators. Note, you might have to add the name of your calibrator to the `calibrator_names.dat` file in `data`.
5. Run `. image_.sh`. This will create images of all fields per spectral window, and a combined image of the target field with all spectral windows.

# Outputs

# Software and References