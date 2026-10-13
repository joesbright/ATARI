# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

ATARI (Allen Telescope Array Radio Imaging) is research code that calibrates and images ATA correlator data. Input is either the ATA's default uvh5 recordings or an existing measurement set. It is a uv-managed package (`pyproject.toml`, `uv.lock`): the distribution is `ata-atari`, the import name is `atari`, and the code is in `src/atari/`. There is no linter.

## Running the pipeline

```bash
uv sync              # once; installs ATARI in editable mode
uv run atari-setup <PATH_TO_MS_OR_UVH5_FOLDER> --refant <name_or_index> [--casapath <casa>] [--chanbin 8] [--flagants ant1,ant2] [--calibrators extra.dat]
casa -c 1GC_.py      # first-generation calibration
. image_.sh          # WSClean imaging
```

`1GC_.py` and `image_.sh` are written to the current folder. `ATARI/01_setup.py` is a thin wrapper that calls `atari.pipeline.main` for the old usage. On the ATA compute nodes, symlink the data folder and pass the symlink; `--casapath` is needed there.

Dependencies:
- **Python ≥3.10**, declared in `pyproject.toml` and locked in `uv.lock`: numpy, scipy, astropy, pyuvdata (must accept `fix_old_proj=`), python-casacore, termcolor. pytest is in the `dev` dependency group.
  - python-casacore only ships Linux x86_64 wheels. Elsewhere (including macOS) it builds from source and needs the casacore C++ library; `uv sync --no-install-package python-casacore` installs everything else. With casacore missing, use `uv run --no-sync`, because plain `uv run` re-syncs and tries to build it. On macOS (including arm64), conda-forge ships python-casacore 3.8.1: a conda/micromamba env with it plus the other packages at their `uv.lock` versions (`uv export --frozen --no-hashes --no-emit-project --group dev --no-emit-package python-casacore`, then `pip install -r` and `pip install --no-deps -e .`) runs every test except the uvh5 route, which stays on the ATA nodes (no aoflagger build for macOS, and its CASA version differs).
- **External programs**: CASA (run as a subprocess and used to run `1GC_.py`), aoflagger (uvh5 path only), WSClean.

## Tests

`uv run pytest -rs` (92 tests). GitHub Actions (`.github/workflows/tests.yml`) runs them on ubuntu for Python 3.10 and 3.13; there the uvh5-route test is skipped. On an ATA node (e.g. comp-node9) all 92 run:

```bash
ATARI_CASAPATH=/home/sonata/src/casa-6.6.0-20/bin/casa uv run pytest -rs
```

- Need no casacore (run on macOS): `test_calibrators.py`, `test_cli.py`, `test_log.py`, `test_script_writers.py` (parses the generated CASA script with `ast`, which catches broken quoting), `test_uvh5_files.py`.
- `test_conversion.py`: uvh5 → per-LO MS conversion of the test observation with the locked pyuvdata.
- `test_pipeline.py`: regression tests. They compare `1GC_.py`/`image_.sh` with `tests/data/expected/` (temp path replaced by `{WORKDIR}`), from two routes:
  - `tests/data/master_ms.ms` (needs casacore only);
  - `tests/data/uvh5/` (also needs CASA and aoflagger; `ATARI_CASAPATH` if casa is an alias).
- Test data: `tests/data/uvh5/` is three scans of p060 2026-10-04 (3c48, 0038+416, AT2026yeh), cut with `tests/make_test_data.py` (h5py, so the raw files' old uvh5 layout is kept). LoD has only 5 tunings because recording nodes dropped; that is deliberate and realistic. Each tuning is cut to its middle 32 channels, so the test LOs have gaps between tunings (real tunings have 192 channels and abut).
- Changing expected outputs (only for intended behaviour changes): on a node, run the uvh5 test with `ATARI_UPDATE_EXPECTED=1 ... --basetemp=/tmp/atari_regen`, clean its `master_ms.ms` (`/tmp/atari_regen/test_setup_from_uvh50/uvh5/master_ms.ms`) with `tests/make_test_ms.py`, copy both back (the nodes can't push to GitHub, so `scp` them to a machine that can), and check the old → new diff is exactly the intended change before committing.

## Architecture

`atari/pipeline.py` `main()` mostly **writes scripts rather than running calibration**: it inspects the MS with `casacore.tables` and appends text to `1GC_.py` (CASA) and `image_.sh` (WSClean) in the current folder. It deletes those files at startup.

Flow:
1. **uvh5 input**:
   - `uvh5_files.find_time_ids` lists each scan once, leaving out skipped fields (below), and a `multiprocessing.Pool` runs `parallel_file_conversion` per time ID. It converts each LO (`LoA`–`LoD`, hard-coded) to MS via `uvh5_files.read_lo` and pyuvdata's `write_ms`, and calls `fix_scans.fix_spw`. An LO with no files in a scan was not recorded and is skipped.
   - CASA (via generated temp scripts run with `log.run`) concatenates the MSs, listed in sorted order by `uvh5_files.find_converted_ms` so LoA–LoD become spw0–spw3, and optionally drops antennas.
   - aoflagger flags, `fix_scans.fix_scans` renumbers scans, and CASA channel-averages into `<input>/master_ms.ms`.
   - Expected layout: `<dir>/uvh5*<timeID>*0001/Lo?*/*.uvh5`. The time ID comes from fixed `_`-separated positions in the filename; the field name is everything between it and the trailing `_0001`, since it can contain underscores.
2. **Field classification** (`atari.calibrators.classify_field`):
   - `Stay_put` (any case; `SKIP_FIELDS`) → skipped completely. These scans are recorded while the sources are below the horizon.
   - 3c286, 3c48 or 3c147 (lowercase) → flux calibrator (hard-coded).
   - Name substring-matched by `atari.calibrators.match_calibrators` against `src/atari/data/calibrator_names.dat` plus the optional `--calibrators` file → gain calibrator.
   - Anything else → target.
   - Each target is paired with its nearest gain calibrator.
   - `--refant` (required) is looked up in the final MS's ANTENNA table by `cli.resolve_refant`: all digits → index, otherwise name. CASA always gets the index.
3. **Per target and SPW**: a TaQL query splits out `<target>_spwN/<target>_spwN.ms`, containing the target, its gain calibrator and the flux calibrator, with `IMAGES/`, `CALIBRATION_TABLES/` and `PLOTS/` subfolders. These are written beside the input; `os.mkdir` fails on a re-run if they already exist. For each split:
   - `fgc.first_generation_calibration` writes the CASA recipe: tfcrop/rflag → setjy → G0 → K0 → B0 → G1 → fluxscale → applycal.
   - `fgc.image_all_fields` writes three WSClean commands.
4. **Final steps**: a deep WSClean image over all splits is written to `DEEP_IMAGE/`. `fgc.flag_u0` adds a 99th-percentile amplitude clip to `1GC_.py`.

Layering: `pipeline.py` → `fgc.py` (defines the recipe order; imported as `FGC`) → `write_casa_scripts.py` / `write_wsclean_scripts.py`. These two build CASA task calls and WSClean commands by string concatenation, so check quoting carefully when editing them. `fix_scans.py` edits MS tables in place. `calibrators.py`, `cli.py`, `log.py` and `uvh5_files.py` are kept free of casacore so they can be tested anywhere.

`legacy/` holds code the pipeline does not use and that is not packaged: `uvh5_to_ms.py`, `concat_all_{b,c}.py` (old `seti-node*` layout), `general_functions.py` (needs CASA's `tb`), and `find_phase_calibrator.py` (a one-off that generated `calibrator_names.dat`; it runs code on import).

## Gotchas

Known bugs and open questions are GitHub issues (`gh issue list`).

- Hard-coded assumptions:
  - `STATE/OBS_MODE` is overwritten with exactly 5 rows (a no-op: CASA's concat output has no STATE rows).
  - The u=0 clip assumes field IDs 0–2.
  - The deep image uses the `imsize`/`cell` of the last SPW processed (always LoD now).
- Recording nodes can drop, so an LO can lack tunings (`LoX.C0352` … `LoX.C1504`), for the whole observation or from partway through. Each LO is 672 MHz recorded independently as 7 tunings of 96 MHz (192 × 0.5 MHz channels), always named `uvh5_files.TUNINGS` (C0352–C1504, the first channel number). `uvh5_files.read_lo` expects all 7 for every LO on its own and fills each missing one with zeroed, fully flagged data, at a recorded tuning's frequencies shifted by the difference in channel numbers. Each recorded tuning's start frequency is checked against its name, and an unknown tuning name is an error, so nothing is filled in the wrong place. An LO with no tunings in a scan was not recorded and is not filled. Without the filling:
  - CASA 6.6 `concat` aborts on exit (`ArrayShapeError`) when LOs have different channel counts, leaving stale row counts in `table.dat` that only the `table.lock` files correct. The input columns are variable-shape (`TiledShapeStMan`), so this looks like a CASA bug; the filling sidesteps it rather than explaining it.
  - a scan whose LO lost a tuning gets its own spectral window in `concat`.
  Filled channels are flagged, but CASA `fluxscale` reports each spw's flux density at the centre of *all* the G1 solve's selected channels, flagged or not (checked on CASA 6.6: LoD reported at 8999.75 MHz, the unflagged centre is 9057.35 MHz). So `pipeline.flagged_everywhere` finds channels flagged in every row of each split, and `write_casa_scripts.channel_selection` leaves them out of the two G1 `gaincal` calls (`spw='3:0~3;12~27'`); other gaincals and spws are unchanged.
  **Never delete `table.lock` files from an MS CASA produced**; use `tests/make_test_ms.py` to make a lock-free copy.
- Logging (`atari/log.py`): use `logger.info` for what the user needs to see in the terminal (steps, calibrator choices, refant) and `logger.debug` for detail; both go to `logs/atari_setup.log` beside the data (`cli.output_folder`), as do other libraries' warnings. Pool workers write only to the file (`log.setup_worker`). Run external programs with `log.run`, which writes their output to their own file in `logs/` and exits if they fail or (given `outputs=`) leave an expected file missing, since CASA exits normally when a task fails. Open tables with `ack=False`, or casacore prints a line per open.
- TaQL queries refer to Python variables as `$name` (e.g. `$y`, `$tm`), so linters report those variables as unused. Don't remove them.
- `.gitignore` anchors `/data/` to the repo root on purpose. An unanchored `data/` would hide `src/atari/data/` and `tests/data/` from git and from the wheel.
