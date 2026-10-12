"""Regression test: run atari-setup on a small ATA measurement set and check
that the generated 1GC_.py and image_.sh match known-good copies in
tests/data/expected/. Those copies were made with the code as it was before
the package restructure, so any difference means behaviour has changed.

If a change is meant to alter the generated scripts, regenerate the copies
with
    ATARI_UPDATE_EXPECTED=1 uv run pytest tests/test_pipeline.py
and review the difference with `git diff tests/data/expected` before
committing it.
"""
import os
import shutil
from pathlib import Path

import pytest

pytest.importorskip('casacore', reason='python-casacore is not installed')

from atari.pipeline import main  # noqa: E402  (needs casacore)

DATA = Path(__file__).parent / 'data'
TEST_MS = DATA / 'test.ms'
EXPECTED = DATA / 'expected'
OUTPUTS = ['1GC_.py', 'image_.sh']

# Generated scripts contain absolute paths to the measurement set. They are
# replaced with this placeholder so the comparison works in any folder.
PLACEHOLDER = '{WORKDIR}'


@pytest.mark.skipif(not TEST_MS.exists(), reason='tests/data/test.ms is missing')
def test_setup_generates_expected_scripts(tmp_path, monkeypatch):
    # The pipeline edits the measurement set and writes folders beside it,
    # so work on a copy.
    ms = tmp_path / TEST_MS.name
    shutil.copytree(TEST_MS, ms)
    monkeypatch.chdir(tmp_path)

    main([str(ms)])

    for name in OUTPUTS:
        actual = (tmp_path / name).read_text().replace(str(tmp_path), PLACEHOLDER)
        if os.environ.get('ATARI_UPDATE_EXPECTED'):
            EXPECTED.mkdir(exist_ok=True)
            (EXPECTED / name).write_text(actual)
        assert actual == (EXPECTED / name).read_text(), name
