#!/bin/bash
# Calibrates every split in parallel: each <split>/1GC.py in its own CASA process,
# up to $ATARI_JOBS at a time. Logs: {WORKDIR}/logs/1GC_<split>.log
# Exits non-zero if a CASA process failed. CASA exits normally when a task inside
# it fails, so check the logs too.
CASA={CASA}
JOBS=${ATARI_JOBS:-4}
run_one() {
    if "$CASA" --nologger --nogui --log2term --nologfile -c "$2" > "$1" 2>&1; then
        echo "done    $2"
    else
        echo "FAILED  $2 (log: $1)"
        return 1
    fi
}
export -f run_one
export CASA
echo "Calibrating 4 splits, $JOBS at a time..."
xargs -P "$JOBS" -L 1 bash -c 'run_one "$0" "$1"' <<'SPLITS'
'{WORKDIR}/logs/1GC_AT2026yeh_spw0.log' '{WORKDIR}/AT2026yeh_spw0/1GC.py'
'{WORKDIR}/logs/1GC_AT2026yeh_spw1.log' '{WORKDIR}/AT2026yeh_spw1/1GC.py'
'{WORKDIR}/logs/1GC_AT2026yeh_spw2.log' '{WORKDIR}/AT2026yeh_spw2/1GC.py'
'{WORKDIR}/logs/1GC_AT2026yeh_spw3.log' '{WORKDIR}/AT2026yeh_spw3/1GC.py'
SPLITS
status=$?
[ $status -eq 0 ] && echo "All splits calibrated." || echo "Calibration failed for at least one split (see FAILED above)."
exit $status
