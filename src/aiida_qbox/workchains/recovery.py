"""Shared error-recovery helpers for Qbox base workchains.

Two AiiDA facts these helpers exist for:

* ``ProcessHandlerReport(False)`` does NOT abort: its exit code has status 0, so
  ``BaseRestartWorkChain`` logs "a handler dealt with the problem, restarting" and reruns the
  same failing calculation until ``max_iterations``. Aborting needs a non-zero exit code:
  use :func:`abort`.
* Out-of-memory and MPI kills are reported by the scheduler/MPI launcher on the job's stderr
  (``_scheduler-stderr.txt``, retrieved by default), not in Qbox's stdout.
"""

from aiida.engine import ProcessHandlerReport

QBOX_DEFAULT_MAX_SCF = 100  # Default max SCF iterations
SCHEDULER_STDERR = '_scheduler-stderr.txt'

# Checked case-insensitively, first match wins.
FATAL_MARKERS = (
    'out of memory',
    'oom-kill',
    'oom_kill',
    'memory allocation failed',
    'cannot allocate memory',
    'bad termination',
    'mpi_abort',
    'sigkill',
    'killed by signal',
    'segmentation fault',
    'segfault',
)


def find_fatal_marker(text: str) -> str | None:
    """Return the first out-of-memory / MPI-kill marker found in ``text``, else None."""
    haystack = text.lower()
    return next((marker for marker in FATAL_MARKERS if marker in haystack), None)


def scheduler_stderr(calculation) -> str:
    """Text of the job's scheduler stderr, or '' if it was not retrieved."""
    if not hasattr(calculation, 'outputs'):
        return ''
    try:
        retrieved = calculation.outputs.retrieved
    except AttributeError:
        return ''
    if retrieved is None:
        return ''
    try:
        return retrieved.base.repository.get_object_content(SCHEDULER_STDERR)
    except (FileNotFoundError, OSError, AttributeError):
        return ''


def abort(workchain, message: str) -> ProcessHandlerReport:
    """Stop the workchain now with ERROR_UNRECOVERABLE_FAILURE (never rerun the same failure)."""
    workchain.report(message)
    return ProcessHandlerReport(do_break=True, exit_code=workchain.exit_codes.ERROR_UNRECOVERABLE_FAILURE)


def next_max_scf(current_scf: int, budget: int) -> int:
    """Return the new max_scf for a restart.

    Qbox's max_scf caps the total SCF iteration count. A restart resumes from
    the previous state, so we need to increase the cap by the budget.
    """
    return int(current_scf) + int(budget)


def made_scf_progress(previous_scf: int | None, current_scf: int | None) -> bool:
    """True if this attempt advanced SCF beyond the previous attempt.

    ``scf_iter`` of a restart that crashed early is read from the output
    copied from its parent, so an unchanged value means the attempt did nothing.
    """
    if current_scf is None:
        return False
    return previous_scf is None or current_scf > previous_scf