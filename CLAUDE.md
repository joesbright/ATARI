# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

ATARI (Allen Telescope Array Radio Imaging) is research code that calibrates and images ATA correlator data. Input is either the ATA's default uvh5 recordings or an existing measurement set. It is a uv-managed package (`pyproject.toml`, `uv.lock`): the distribution is `ata-atari`, the import name is `atari`, and the code is in `src/atari/`. There is no linter.

## Running the pipeline

```bash
uv sync              # once; installs ATARI in editable mode
uv run atari-setup <PATH_TO_MS_OR_UVH5_FOLDER> --refant <name_or_index> [--casapath <casa>] [--chanbin 8] [--flagants ant1,ant2] [--calibrators extra.dat]
bash <OUT>/1GC_.sh         # first-generation calibration, one CASA process per split in parallel
                           # (or casa -c <OUT>/1GC_.py: the same splits one after another)
. <OUT>/image_.sh          # WSClean imaging
```

`1GC_.sh`, `1GC_.py` and `image_.sh` are written to `<OUT>` = `cli.output_folder`: the folder holding an input MS, or the uvh5 folder itself, beside `logs/` and the per-target folders. Nothing is written to the current folder. The input path is made absolute first, so the scripts work from any folder. `ATARI/01_setup.py` is a thin wrapper that calls `atari.pipeline.main` for the old usage. On the ATA compute nodes, symlink the data folder and pass the symlink; `--casapath` is needed there.

Dependencies:
- **Python ≥3.10**, declared in `pyproject.toml` and locked in `uv.lock`: numpy, scipy, astropy, pyuvdata (must accept `fix_old_proj=`), python-casacore, termcolor. pytest is in the `dev` dependency group.
  - python-casacore only ships Linux x86_64 wheels. Elsewhere (including macOS) it builds from source and needs the casacore C++ library; `uv sync --no-install-package python-casacore` installs everything else. With casacore missing, use `uv run --no-sync`, because plain `uv run` re-syncs and tries to build it. On macOS (including arm64), conda-forge ships python-casacore 3.8.1: a conda/micromamba env with it plus the other packages at their `uv.lock` versions (`uv export --frozen --no-hashes --no-emit-project --group dev --no-emit-package python-casacore`, then `pip install -r` and `pip install --no-deps -e .`) runs every test except the uvh5 route, which stays on the ATA nodes (no aoflagger build for macOS, and its CASA version differs).
- **External programs**: CASA (run as a subprocess and used to run `1GC_.py`), aoflagger (uvh5 path only), WSClean.

## Tests

`uv run pytest -rs` (131 tests). GitHub Actions (`.github/workflows/tests.yml`) runs them on ubuntu for Python 3.10 and 3.13; there the uvh5-route test is skipped. On an ATA node (e.g. comp-node9) all 131 run:

```bash
ATARI_CASAPATH=/home/sonata/src/casa-6.6.0-20/bin/casa uv run pytest -rs
```

- Need no casacore (run on macOS): `test_calibrators.py`, `test_cli.py`, `test_log.py`, `test_script_writers.py` (parses the generated CASA script with `ast`, which catches broken quoting), `test_uvh5_files.py`.
- `test_conversion.py`: uvh5 → per-LO MS conversion of the test observation with the locked pyuvdata.
- `test_pipeline.py`: regression tests. They compare `1GC_.py` (rebuilt from the per-split `1GC.py` scripts it runs, so the calibration commands themselves are compared), `1GC_.sh` (CASA path masked) and `image_.sh` with `tests/data/expected/` (temp path replaced by `{WORKDIR}`), from two routes:
  - `tests/data/master_ms.ms` (needs casacore only);
  - `tests/data/uvh5/` (also needs CASA and aoflagger; `ATARI_CASAPATH` if casa is an alias).
- Test data: `tests/data/uvh5/` is three scans of p060 2026-10-04 (3c48, 0038+416, AT2026yeh), cut with `tests/make_test_data.py` (h5py, so the raw files' old uvh5 layout is kept). LoD has only 5 tunings because recording nodes dropped; that is deliberate and realistic. Each tuning is cut to its middle 32 channels, so the test LOs have gaps between tunings (real tunings have 192 channels and abut).
- Changing expected outputs (only for intended behaviour changes): on a node, run the uvh5 test with `ATARI_UPDATE_EXPECTED=1 ... --basetemp=/tmp/atari_regen`, clean its combined MS (`/tmp/atari_regen/test_setup_from_uvh50/uvh5/61317_AT2026yeh.ms`) with `tests/make_test_ms.py` into `tests/data/master_ms.ms`, copy the expected scripts into `tests/data/expected/` (a node with SSH agent forwarding can commit and push them directly), and check the old → new diff is exactly the intended change before committing.

## Architecture

`atari/pipeline.py` `main()` mostly **writes scripts rather than running calibration**: it inspects the MS with `casacore.tables` and appends text to `1GC_.py` (CASA) and `image_.sh` (WSClean) in the output folder. If either already exists there (an earlier run), it stops at startup rather than delete them. Its temporary CASA scripts (`concat_command.py`, `avg_command.py`, `flag_command.py`) also go in the output folder, and CASA runs with `logs/` as its working folder (`log.run(cwd=)`), so its `<task>.last` files land there.

Flow:
1. **uvh5 input**:
   - `uvh5_files.find_time_ids` lists each scan once, leaving out skipped fields (below), and a `multiprocessing.Pool` runs `parallel_file_conversion` per time ID. It converts each LO (`LoA`–`LoD`, hard-coded) to MS via `uvh5_files.read_lo` and pyuvdata's `write_ms`, and calls `fix_scans.fix_spw`. An LO with no files in a scan was not recorded and is skipped.
   - **Per LO, in parallel** (issue #40; `uvh5_files.group_by_lo`, `log.run_parallel`): the converted MSs (`uvh5_files.find_converted_ms`, which matches only `uvh5_*_Lo?.ms`) are grouped by LO, and for each LO CASA `concat`s its scans into `<input>/LoX_tmp.ms` (plus `mstransform` without `--flagants` antennas into `LoX_tmp2.ms`). The converted MSs are then deleted, `fix_scans.flag_zero_visibilities` flags exact zeros (a process per LO), aoflagger flags each LO (as many at once as fit in 75% of available memory at ~0.8× each LO's size, `uvh5_files.flagging_jobs`; threads left to aoflagger, so a job left running alone uses every core; run in the output folder so any reordering files land there), and CASA channel-averages each into `LoX_avg.ms`. Logs per LO: `logs/casa_concat_LoX.log`, `aoflagger_LoX.log`, `casa_average_LoX.log`.
   - The averaged LOs are `concat`ed (`timesort=True`; LoA–LoD become spw0–spw3 in this order) into `<input>/<MJD>_<targets>.ms` (`uvh5_files.final_ms_name`: the first scan's MJD, all targets sorted and joined with `_`, e.g. `61294_AT2026yeh.ms`; log `casa_combine.log`), `fix_scans.fix_scans` renumbers its scans, and its zeros are flagged once more (a few, ~0.01%, are left after aoflagger and the averaging). Everything after this works on that one MS, as before. Checked on 2026-09-18 p060: aoflagger treats each spw on its own, so the flags equal those of the old single-combined-MS route (0.000% differ); `concat` may store some rows with the antennas swapped (exact conjugates). Setup's combine/flag/average steps went from ~49 to ~34 min, and the whole setup from 66 to 52 min (`concat` 13→4, zero-flagging 6.6→1.6, aoflagger 18→21 with 3 LOs at once as memory allowed (CPU-bound once in memory; fixing `-j` per job made the last LO slow: 26 min), averaging 11→3, plus 4 min to combine the LOs). `tests/data/master_ms.ms` keeps its old name: it is only an input to the MS-route tests.
   - Expected layout: `<dir>/uvh5*<timeID>*0001/Lo?*/*.uvh5`. The time ID comes from fixed `_`-separated positions in the filename; the field name is everything between it and the trailing `_0001`, since it can contain underscores.
2. **Field classification** (`atari.calibrators.classify_field`):
   - `Stay_put` (any case; `SKIP_FIELDS`) → skipped completely. These scans are recorded while the sources are below the horizon.
   - 3c286, 3c48 or 3c147 (any case; `FLUX_CALIBRATORS`) → flux calibrator (hard-coded).
   - Name substring-matched by `atari.calibrators.match_calibrators` against `src/atari/data/calibrator_names.dat` plus the optional `--calibrators` file → gain calibrator.
   - Anything else → target.
   - Each target is paired with its nearest gain calibrator.
   - `pipeline.check_fields` stops with an error if there is no flux or no gain calibrator. For uvh5 input it runs on the field names in the file names (`uvh5_files.find_fields`), before the conversion.
   - MS input: exact zeros are flagged in the given MS at the start (`pipeline.flag_zeros`).
   - `--refant` (required) is looked up in the final MS's ANTENNA table by `cli.resolve_refant`: all digits → index, otherwise name. CASA always gets the index.
3. **Per target and SPW**: a TaQL query splits out `<target>_spwN/<target>_spwN.ms`, containing the target, its gain calibrator and the flux calibrator, with `IMAGES/`, `CALIBRATION_TABLES/` and `PLOTS/` subfolders. These are written beside the input; `os.mkdir` fails on a re-run if they already exist. For each split:
   - `fgc.first_generation_calibration` writes the CASA recipe into the split's own `<split>/1GC.py`; `1GC_.py` runs these one after another (`exec`), and `1GC_.sh` (`write_casa_scripts.write_parallel_calibration`) runs each in its own CASA process, up to min(splits, cores) at once (`ATARI_JOBS` overrides), logging to `logs/1GC_<split>.log` and exiting non-zero if a CASA process failed. CASA's calibration uses ~1.1 cores (measured on comp-node9), so this is ~4× faster for 4 subbands. The recipe: elevation flag (all data above `fgc.ELEVATION_LIMIT` = 85°, CASA's `flagdata(mode='elevation')`; issue #48: on 2026-11-06 p060 the source was lost in a scan at 88–89°, and its bad gains spoiled the target scans either side through the interpolation in time; no upper limit is published for the ATA) → tfcrop/rflag (on DATA) → setjy → G0 → K0 → B0 → G1 → fluxscale → applycal → tfcrop/rflag again on the **calibrated** data (`datacolumn='corrected'`, all fields) → `statwt` on the target only (weights from the scatter of the calibrated data, so noisy antennas count for less; 2026-09-18 p060: image noise a further 8–36% lower, fluxes unchanged to 0.1%; not on calibrators, whose bright signal would inflate the scatter). Flagging the uncalibrated data after calibration missed rare extreme outliers (2026-09-18 p060: the top 1% of target samples held 75% of the variance); flagging the corrected data lowered the image noise 1.8–2.9× with the flux scale unchanged (3C286 and 0119+321 within 0.3%). The default flag extension across polarisations is kept: turning it off kept more, but noisier, data and raised the image noise 25%. B0 is solved once per flux-calibrator scan (`combine=''`; CASA's `bandpass` defaults to `combine='scan'`, one bandpass averaged over all scans) and applied with `interp='linear'` in time, so a bandpass that drifts over a long track is followed (issue #30; on 2026-09-18 p060 spw0 the shape changed by ~0.5% in amplitude and ~0.4° in phase between scans 13.6 h apart, beyond the solution noise).
   - `fgc.image_all_fields` writes three WSClean commands. All WSClean commands (also the deep image) use Briggs robust `write_wsclean_scripts.BRIGGS_ROBUST` = 0.7, chosen from a robust sweep on 2026-09-18 p060 (see the comment there); re-check it when the array changes.
4. **Final steps**: a deep WSClean image over all splits is written to `DEEP_IMAGE/`. (An earlier "u=0" clip of each field's calibrated amplitudes above their 99th percentile was removed in 2026-11: it flagged nothing on 2026-09-18 p060, would bias bright calibrators if it did, and flagging the corrected data covers its purpose.)

Layering: `pipeline.py` → `fgc.py` (defines the recipe order; imported as `FGC`) → `write_casa_scripts.py` / `write_wsclean_scripts.py`. These two build CASA task calls and WSClean commands by string concatenation, so check quoting carefully when editing them. `fix_scans.py` edits MS tables in place. `calibrators.py`, `cli.py`, `log.py` and `uvh5_files.py` are kept free of casacore so they can be tested anywhere.

`legacy/` holds code the pipeline does not use and that is not packaged: `uvh5_to_ms.py`, `concat_all_{b,c}.py` (old `seti-node*` layout), `general_functions.py` (needs CASA's `tb`), and `find_phase_calibrator.py` (a one-off that generated `calibrator_names.dat`; it runs code on import).

## Gotchas

Known bugs and open questions are GitHub issues (`gh issue list`).

- Dead antennas, feeds and LOs are recorded as exact zeros without being flagged (37.6% of all samples on 2026-09-18 p060, mostly unflagged; neither aoflagger nor CASA's flagging caught them). ATARI flags them itself (see Flow); `test_pipeline.assert_no_unflagged_zeros` checks that none reach the per-target splits.
- Hard-coded assumptions:
  - `STATE/OBS_MODE` is overwritten with exactly 5 rows (a no-op: CASA's concat output has no STATE rows).
  - The deep image uses the `imsize`/`cell` of the last SPW processed (always LoD now).
- Recording nodes can drop, so an LO can lack tunings (`LoX.C0352` … `LoX.C1504`), for the whole observation or from partway through. Each LO is 672 MHz recorded independently as 7 tunings of 96 MHz (192 × 0.5 MHz channels), always named `uvh5_files.TUNINGS` (C0352–C1504, the first channel number). `uvh5_files.read_lo` expects all 7 for every LO on its own and fills each missing one with zeroed, fully flagged data, at a recorded tuning's frequencies shifted by the difference in channel numbers. Each recorded tuning's start frequency is checked against its name, and an unknown tuning name is an error, so nothing is filled in the wrong place. An LO with no tunings in a scan was not recorded and is not filled. Without the filling:
  - CASA 6.6 `concat` aborts on exit (`ArrayShapeError`) when LOs have different channel counts, leaving stale row counts in `table.dat` that only the `table.lock` files correct. The input columns are variable-shape (`TiledShapeStMan`), so this looks like a CASA bug; the filling sidesteps it rather than explaining it.
  - a scan whose LO lost a tuning gets its own spectral window in `concat`.
  Filled channels are flagged, but CASA `fluxscale` reports each spw's flux density at the centre of *all* the G1 solve's selected channels, flagged or not (checked on CASA 6.6: LoD reported at 8999.75 MHz, the unflagged centre is 9057.35 MHz). So `pipeline.flagged_everywhere` finds channels flagged in every row of each split, and `write_casa_scripts.channel_selection` leaves them out of the two G1 `gaincal` calls (`spw='3:0~3;12~27'`); other gaincals and spws are unchanged.
  **Never delete `table.lock` files from an MS CASA produced**; use `tests/make_test_ms.py` to make a lock-free copy.
- Logging (`atari/log.py`): use `logger.info` for what the user needs to see in the terminal (steps, calibrator choices, refant) and `logger.debug` for detail; both go to `logs/atari_setup.log` beside the data (`cli.output_folder`), as do other libraries' warnings (`warnings.warn`, logged once each per process with their category and source, since pyuvdata replaces `warnings.formatwarning`). Pool workers write only to the file (`log.setup_worker`); `log.Progress` shows the conversion's progress (a bar redrawn in a terminal, otherwise a line per scan). Run external programs with `log.run` (without uv's `VIRTUAL_ENV`, which CASA's IPython warns about), which writes their output to their own file in `logs/` and exits if they fail or (given `outputs=`) leave an expected file missing, since CASA exits normally when a task fails. aoflagger runs with `-v` and `line_buffered=True` (`stdbuf`), since it holds its output back when writing to a file. Open tables with `ack=False`, or casacore prints a line per open.
- TaQL queries refer to Python variables as `$name` (e.g. `$y`, `$tm`), so linters report those variables as unused. Don't remove them.
- `.gitignore` anchors `/data/` to the repo root on purpose. An unanchored `data/` would hide `src/atari/data/` and `tests/data/` from git and from the wheel.
