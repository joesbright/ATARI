"""Logging for atari-setup. Key steps and decisions go to the terminal;
everything, including other libraries' warnings, goes to logs/atari_setup.log
beside the data. External programs (CASA, aoflagger) write to their own log
files there. Kept free of casacore so it can be tested anywhere."""
import logging
import os
import shutil
import subprocess
import sys
import time
import warnings
from pathlib import Path

from termcolor import colored

# ATARI's own messages. info() is shown in the terminal, debug() only in the
# log file (and in the terminal with --verbose).
logger = logging.getLogger('atari')

LOG_NAME = 'atari_setup.log'
FILE_FORMAT = '%(asctime)s %(processName)s %(levelname)s %(name)s: %(message)s'

# Lines from the end of a failed program's log to show in the terminal.
TAIL_LINES = 20

# The handlers set up here, so a rerun in the same Python session (e.g. the
# tests) replaces them instead of adding more.
_handlers = []

# Other libraries' warnings already logged by this process, so each is logged
# once rather than once per file read, and the warnings.showwarning they
# replaced.
_seen_warnings = set()
_previous_showwarning = None

# Whether --verbose was given: detailed messages then go to the terminal, so
# a progress bar redrawn in place would be broken up.
_verbose = False


class _TerminalFormatter(logging.Formatter):
    COLOURS = {logging.WARNING: 'yellow', logging.ERROR: 'red', logging.CRITICAL: 'red'}

    def format(self, record):
        message = super().format(record)
        if record.levelno >= logging.WARNING:
            message = colored(record.levelname.capitalize() + ': ' + message, self.COLOURS[record.levelno])
        return message


def _file_handler(logfile):
    # Append, because the conversion workers write to the same file.
    handler = logging.FileHandler(logfile, mode='a')
    handler.setFormatter(logging.Formatter(FILE_FORMAT))
    return handler


def _add(target, handler):
    target.addHandler(handler)
    _handlers.append((target, handler))


def _log_warning(message, category, filename, lineno, file=None, line=None):
    # Used as warnings.showwarning, which is what warnings.warn() calls to show
    # a warning. Not warnings.formatwarning, which pyuvdata replaces with one
    # that leaves out the category and where the warning came from. One line
    # per warning.
    text = (category.__name__ + ': ' + ' '.join(str(message).split())
            + ' (' + filename.split('site-packages' + os.sep)[-1] + ':' + str(lineno) + ')')
    if text not in _seen_warnings:
        _seen_warnings.add(text)
        logging.getLogger('warnings').warning(text)


def _capture_warnings():
    global _previous_showwarning
    _seen_warnings.clear()
    if warnings.showwarning is not _log_warning:
        _previous_showwarning = warnings.showwarning
        warnings.showwarning = _log_warning


def close_logging():
    global _previous_showwarning
    for target, handler in _handlers:
        target.removeHandler(handler)
        handler.close()
    _handlers.clear()
    if _previous_showwarning is not None:
        warnings.showwarning = _previous_showwarning
        _previous_showwarning = None


def setup_logging(logdir, verbose=False):
    """Send ATARI's messages to the terminal and everything to a new log file
    in logdir. Returns the log file's path."""
    global _verbose
    close_logging()
    _verbose = verbose
    logdir = Path(logdir)
    logdir.mkdir(parents=True, exist_ok=True)
    logfile = logdir / LOG_NAME
    logfile.write_text('')  # start a new log on each run

    # The file gets everything: ATARI's messages at every level, and other
    # libraries' (pyuvdata, astropy) at INFO and above.
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    _add(root, _file_handler(logfile))
    logger.setLevel(logging.DEBUG)
    # warnings.warn(), which pyuvdata uses, becomes a log message.
    _capture_warnings()

    # The terminal only gets ATARI's messages.
    terminal = logging.StreamHandler(sys.stdout)
    terminal.setLevel(logging.DEBUG if verbose else logging.INFO)
    terminal.setFormatter(_TerminalFormatter('%(message)s'))
    _add(logger, terminal)

    return logfile


def setup_worker(logfile):
    """For multiprocessing.Pool workers: write only to the log file. Forked
    workers inherit the parent's handlers, so remove those first."""
    for target in [logging.getLogger(), logger]:
        for handler in list(target.handlers):
            target.removeHandler(handler)
    _handlers.clear()
    logging.getLogger().setLevel(logging.INFO)
    _add(logging.getLogger(), _file_handler(logfile))
    logger.setLevel(logging.DEBUG)
    _capture_warnings()


def _duration(seconds):
    if seconds < 60:
        return str(round(seconds)) + ' s'
    if seconds < 3600:
        return str(round(seconds / 60)) + ' min'
    return str(int(seconds // 3600)) + ' h ' + str(round(seconds % 3600 / 60)) + ' min'


class Progress:
    """Progress through total steps (e.g. scans converted). In a terminal, a
    bar redrawn in place; otherwise, and in the log file, a line per step."""
    WIDTH = 20

    def __init__(self, total, description):
        self.total = total
        self.description = description
        self.done = 0
        self.start = time.monotonic()
        self.bar = sys.stdout.isatty() and not _verbose

    def update(self, label):
        self.done += 1
        line = self.description + ': ' + str(self.done) + '/' + str(self.total) + ' (' + label + ')'
        if not self.bar:
            logger.info(line)
            return
        logger.debug(line)
        elapsed = time.monotonic() - self.start
        filled = self.WIDTH * self.done // self.total
        text = (self.description + ' [' + '#' * filled + '-' * (self.WIDTH - filled) + '] '
                + str(self.done) + '/' + str(self.total) + ' (' + str(100 * self.done // self.total) + '%), '
                + _duration(elapsed))
        if self.done < self.total:
            text += ', about ' + _duration(elapsed / self.done * (self.total - self.done)) + ' left'
        # Pad, so a shorter line fully covers the one before.
        sys.stdout.write('\r' + text.ljust(100))
        if self.done == self.total:
            sys.stdout.write('\n')
        sys.stdout.flush()


def run(command, logfile, description, outputs=(), line_buffered=False):
    """Run a shell command (CASA, aoflagger) with its output going to logfile
    instead of the terminal. Stop with the end of the log if it fails, or if
    any of outputs is missing afterwards: CASA exits normally even when one of
    its tasks fails. line_buffered makes a program that holds its output back
    when writing to a file (aoflagger) write each line as it goes, so the log
    can be followed, using stdbuf where it is installed."""
    if line_buffered and shutil.which('stdbuf'):
        command = 'stdbuf -oL -eL ' + command
    logger.info(description + ' (log: ' + str(logfile) + ')...')
    logger.debug('Running: ' + command)
    start = time.monotonic()
    # Without uv's VIRTUAL_ENV, which CASA's own Python would warn about.
    env = {name: value for name, value in os.environ.items() if name != 'VIRTUAL_ENV'}
    with open(logfile, 'w') as f:
        result = subprocess.run(command, shell=True, stdout=f, stderr=subprocess.STDOUT, env=env)
    if result.returncode != 0:
        _fail(description, logfile, 'exit status ' + str(result.returncode))
    for output in outputs:
        if not os.path.exists(output):
            _fail(description, logfile, str(output) + ' was not made')
    logger.info(description + ' done (' + _duration(time.monotonic() - start) + ')')


def _fail(description, logfile, reason):
    with open(logfile, errors='replace') as f:
        tail = f.readlines()[-TAIL_LINES:]
    logger.error(description + ' failed (' + reason + '). End of ' + str(logfile) + ':\n'
                 + ''.join(tail).rstrip())
    sys.exit(1)
