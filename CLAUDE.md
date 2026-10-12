# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

ATARI (Allen Telescope Array Radio Imaging) is research code that calibrates and images ATA correlator data. Input is either the ATA's default uvh5 recordings or an existing measurement set. It is a uv-managed package (`pyproject.toml`, `uv.lock`): the distribution is `ata-atari`, the import name is `atari`, and the code is in `src/atari/`. There is no linter.

## Running the pipeline

```bash
uv sync              # once; installs ATARI in editable mode
uv run atari-setup <PATH_TO_MS_OR_UVH5_FOLDER> [--casapath <casa>] [--chanbin 8] [--flagants ant1,ant2] [--calibrators extra.dat]
casa -c 1GC_.py      # first-generation calibration
. image_.sh          # WSClean imaging
```

`1GC_.py` and `image_.sh` are written to the current folder. `ATARI/01_setup.py` is a thin wrapper that calls `atari.pipeline.main` for the old usage. On the ATA compute nodes, symlink the data folder and pass the symlink; `--casapath` is needed there.

Dependencies:
- **Python ≥3.10**, declared in `pyproject.toml` and locked in `uv.lock`: numpy, scipy, astropy, pyuvdata (must accept `fix_old_proj=`), python-casacore, termcolor. pytest is in the `dev` dependency group.
  - python-casacore only ships Linux x86_64 wheels. Elsewhere (including macOS) it builds from source and needs the casacore C++ library; `uv sync --no-install-package python-casacore` installs everything else. With casacore missing, use `uv run --no-sync`, because plain `uv run` re-syncs and tries to build it.
- **External programs**: CASA (run as a subprocess and used to run `1GC_.py`), aoflagger (uvh5 path only), WSClean.

## Tests

`uv run pytest -rs`. GitHub Actions (`.github/workflows/tests.yml`) runs them on ubuntu for Python 3.10 and 3.13.
- `tests/test_calibrators.py` and `tests/test_script_writers.py` need no casacore. The script-writer tests parse the generated CASA script with `ast`, which catches broken quoting.
- `tests/test_pipeline.py` is a regression test. It runs `main()` on a copy of `tests/data/test.ms` and compares `1GC_.py`/`image_.sh` with `tests/data/expected/`, with the temp path replaced by `{WORKDIR}`. It skips if casacore or the data is missing. Regenerate with `ATARI_UPDATE_EXPECTED=1` only for intended behaviour changes, and review the diff.

## Architecture

`atari/pipeline.py` `main()` mostly **writes scripts rather than running calibration**: it inspects the MS with `casacore.tables` and appends text to `1GC_.py` (CASA) and `image_.sh` (WSClean) in the current folder. It deletes those files at startup.

Flow:
1. **uvh5 input**:
   - A `multiprocessing.Pool` runs `parallel_file_conversion` once per time ID. It converts each LO (`LoA`–`LoD`, hard-coded) to MS via pyuvdata and calls `fix_scans.fix_spw`.
   - CASA (via generated temp scripts run with `os.system`) concatenates the MSs and optionally drops antennas.
   - aoflagger flags, `fix_scans.fix_scans` renumbers scans, and CASA channel-averages into `<input>/master_ms.ms`.
   - Expected layout: `<dir>/uvh5*<timeID>*0001/Lo?*/*.uvh5`. The time ID and field name come from fixed `_`-separated positions in the filename.
2. **Field classification**:
   - 3c286, 3c48 or 3c147 (lowercase) → flux calibrator (hard-coded).
   - Name substring-matched by `atari.calibrators.match_calibrators` against `src/atari/data/calibrator_names.dat` plus the optional `--calibrators` file → gain calibrator.
   - Anything else → target.
   - Each target is paired with its nearest gain calibrator.
3. **Per target and SPW**: a TaQL query splits out `<target>_spwN/<target>_spwN.ms`, containing the target, its gain calibrator and the flux calibrator, with `IMAGES/`, `CALIBRATION_TABLES/` and `PLOTS/` subfolders. These are written beside the input; `os.mkdir` fails on a re-run if they already exist. For each split:
   - `fgc.first_generation_calibration` writes the CASA recipe: tfcrop/rflag → setjy → G0 → K0 → B0 → G1 → fluxscale → applycal.
   - `fgc.image_all_fields` writes three WSClean commands.
4. **Final steps**: a deep WSClean image over all splits is written to `DEEP_IMAGE/`. `fgc.flag_u0` adds a 99th-percentile amplitude clip to `1GC_.py`.

Layering: `pipeline.py` → `fgc.py` (defines the recipe order; imported as `FGC`) → `write_casa_scripts.py` / `write_wsclean_scripts.py`. These two build CASA task calls and WSClean commands by string concatenation, so check quoting carefully when editing them. `fix_scans.py` edits MS tables in place. `calibrators.py` is kept free of casacore so it can be tested anywhere.

`legacy/` holds code the pipeline does not use and that is not packaged: `uvh5_to_ms.py`, `concat_all_{b,c}.py` (old `seti-node*` layout), `general_functions.py` (needs CASA's `tb`), and `find_phase_calibrator.py` (a one-off that generated `calibrator_names.dat`; it runs code on import).

## Gotchas

- Hard-coded assumptions:
  - `refant='3'`
  - `STATE/OBS_MODE` is overwritten with exactly 5 rows.
  - The u=0 clip assumes field IDs 0–2.
  - The deep image uses the `imsize`/`cell` of the last SPW processed.
- TaQL queries refer to Python variables as `$name` (e.g. `$y`, `$tm`), so linters report those variables as unused. Don't remove them.
- `.gitignore` anchors `/data/` to the repo root on purpose. An unanchored `data/` would hide `src/atari/data/` and `tests/data/` from git and from the wheel.
