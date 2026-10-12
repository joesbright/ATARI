"""Make tests/data/master_ms.ms from the master_ms.ms that a pipeline run on
the test observation produced.

The measurement sets CASA writes can have table.dat files whose row counts
are out of date: the correct counts are only in the table.lock files, which
casacore reads when they are present. The test copy is committed without
lock files, so every table, including each subtable, is rewritten row by row
here so that its table.dat is correct. The result is checked by deleting the
lock files and reading every table again in a fresh process.

Run it where python-casacore is installed (e.g. an ATA node):
    python make_test_ms.py ~/atari_baseline_run/master_ms.ms ~/master_ms_clean.ms
"""
import argparse
import os
import shutil
import subprocess
import sys

from casacore.tables import table

COUNT_ROWS = '''
import os, sys
from casacore.tables import table
ms = sys.argv[1]
for name in [''] + sorted(os.listdir(ms)):
    if os.path.isfile(os.path.join(ms, name, 'table.dat')):
        t = table(os.path.join(ms, name), ack=False)
        print(name or '.', t.nrows())
        t.close()
'''


def row_counts(ms):
    """Row count of the main table ('.') and each subtable, read with
    casacore in a separate process so no open or cached tables are reused."""
    output = subprocess.run([sys.executable, '-c', COUNT_ROWS, ms], check=True,
                            capture_output=True, text=True).stdout
    return dict(line.rsplit(' ', 1) for line in output.splitlines())


def value_copy(src, dst):
    t = table(src, ack=False)
    t.copy(dst, deep=True, valuecopy=True)
    t.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('src', help='master_ms.ms produced by a pipeline run')
    parser.add_argument('dst', help='where to write the clean copy (must not exist)')
    args = parser.parse_args()

    if os.path.exists(args.dst):
        parser.error(args.dst + ' already exists')

    expected = row_counts(args.src)

    # A deep copy rewrites the main table but copies subtables file by file,
    # so rewrite each subtable as well.
    value_copy(args.src, args.dst)
    for name in sorted(os.listdir(args.dst)):
        sub = os.path.join(args.dst, name)
        if os.path.isfile(os.path.join(sub, 'table.dat')):
            value_copy(sub, sub + '.tmp')
            shutil.rmtree(sub)
            os.rename(sub + '.tmp', sub)

    for root, dirs, files in os.walk(args.dst):
        if 'table.lock' in files:
            os.remove(os.path.join(root, 'table.lock'))

    actual = row_counts(args.dst)
    for name in sorted(expected):
        print('%-17s %6s rows' % (name, actual.get(name)))
    if actual != expected:
        sys.exit('row counts differ from the original: ' + str(expected))
    print('row counts match the original without lock files')

    # Reading the tables above created new lock files; remove them again.
    for root, dirs, files in os.walk(args.dst):
        if 'table.lock' in files:
            os.remove(os.path.join(root, 'table.lock'))


if __name__ == '__main__':
    main()
