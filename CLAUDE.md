# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

ATARI (Allen Telescope Array Radio Imaging) is research code that calibrates and images ATA correlator data. Input is either the ATA's default uvh5 recordings or an existing measurement set. There is no packaging, no test suite, no linter and no environment file.

## Running the pipeline

Everything must be run from inside `ATARI/`: modules are found via `sys.path.insert(0, '../utility')` and data files are opened as `../data/...`.

```bash
cd ATARI
python 01_setup.py <PATH_TO_MS_OR_UVH5_FOLDER> [--casapath <casa>] [--chanbin 8] [--flagants ant1,ant2]
casa -c 1GC_.py      # first-generation calibration
. image_.sh          # WSClean imaging
```

On the ATA compute nodes, symlink the data folder and pass the symlink; `--casapath` is needed there.

Dependencies (none are pinned):
- **Python ≥3.8**: numpy, scipy, astropy, pyuvdata (must accept `fix_old_proj=`), python-casacore, termcolor, pandas.
- **External programs**: CASA (run as a subprocess and used to run `1GC_.py`), aoflagger (uvh5 path only), WSClean.

## Architecture

`01_setup.py` is a top-level script with no `main()`. It mostly **writes scripts rather than running calibration**: it inspects the MS with `casacore.tables` and appends text to `1GC_.py` (CASA) and `image_.sh` (WSClean) in the current folder. It deletes those files at startup.

Flow:
1. **uvh5 input**:
   - A `multiprocessing.Pool` runs `parallel_file_conversion` once per time ID. It converts each LO (`LoA`–`LoD`, hard-coded) to MS via pyuvdata and calls `fix_scans.fix_spw`.
   - CASA (via generated temp scripts run with `os.system`) concatenates the MSs and optionally drops antennas.
   - aoflagger flags, `fix_scans.fix_scans` renumbers scans, and CASA channel-averages into `<input>/master_ms.ms`.
   - Expected layout: `<dir>/uvh5*<timeID>*0001/Lo?*/*.uvh5`. The time ID and field name come from fixed `_`-separated positions in the filename.
2. **Field classification**:
   - 3C286, 3C48 or 3C147 → flux calibrator (hard-coded).
   - Name substring-matched in `data/calibrator_names.dat` → gain calibrator.
   - Anything else → target.
   - Each target is paired with its nearest gain calibrator.
3. **Per target and SPW**: a TaQL query splits out `<target>_spwN/<target>_spwN.ms`, containing the target, its gain calibrator and the flux calibrator, with `IMAGES/`, `CALIBRATION_TABLES/` and `PLOTS/` subfolders. These are written beside the input; `os.mkdir` fails on a re-run if they already exist. For each split:
   - `FGC.first_generation_calibration` writes the CASA recipe: tfcrop/rflag → setjy → G0 → K0 → B0 → G1 → fluxscale → applycal.
   - `FGC.image_all_fields` writes three WSClean commands.
4. **Final steps**: a deep WSClean image over all splits is written to `DEEP_IMAGE/`. `FGC.flag_u0` adds a 99th-percentile amplitude clip to `1GC_.py`.

Layering: `01_setup.py` → `ATARI/FGC.py` (defines the recipe order) → `utility/write_casa_scripts.py` / `utility/write_wsclean_scripts.py`. These two build CASA task calls and WSClean commands by string concatenation, so check quoting carefully when editing them. `utility/fix_scans.py` edits MS tables in place.

Legacy or one-off code that `01_setup.py` does not depend on:
- `uvh5_to_ms.py`, `concat_all_{b,c}.py` (old `seti-node*` layout)
- `general_functions.py` (needs CASA's `tb`)
- `find_phase_calibrator.py`: still imported by `01_setup.py`, and it **runs a test print and reads `../data/calibrator_names.dat` when imported**.

## Gotchas

- Hard-coded assumptions:
  - `refant='3'`
  - `STATE/OBS_MODE` is overwritten with exactly 5 rows.
  - The u=0 clip assumes field IDs 0–2.
  - The deep image uses the `imsize`/`cell` of the last SPW processed.
- The multiprocessing `__name__ == '__main__'` guard sits mid-script. That works on Linux (fork) but re-runs module-level code in workers on macOS (spawn).
- If a gain calibrator is missing from `data/calibrator_names.dat`, add it there. The file is tracked in git even though `.gitignore` lists it.
