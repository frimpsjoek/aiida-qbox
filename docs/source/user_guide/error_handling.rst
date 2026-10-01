===============
Error Handling
===============

All Qbox workchains (``qbox.base``, ``qbox.relax``, ``qbox.md``, ``qbox.server``)
inherit from AiiDA's ``BaseRestartWorkChain`` and implement automated error recovery
following the same patterns as ``aiida-west``.

.. contents::
   :local:
   :depth: 2

Exit Codes
++++++++++

.. list-table:: WorkChain Exit Codes
   :header-rows: 1
   :widths: 10 30 60

   * - Code
     - Name
     - Meaning
   * - 301
     - ERROR_NO_RETRIEVED_FOLDER
     - Retrieved folder inaccessible
   * - 302
     - ERROR_OUTPUT_STDOUT_MISSING
     - Stdout not found in retrieved
   * - 312
     - ERROR_OUTPUT_STDOUT_INCOMPLETE
     - Job killed (walltime/OOM/node failure)
   * - 320
     - ERROR_OUTPUT_XML_MISSING
     - XML output file not found
   * - 321
     - ERROR_OUTPUT_XML_READ
     - XML file could not be read
   * - 322
     - ERROR_OUTPUT_XML_PARSE
     - XML file could not be parsed
   * - 330
     - ERROR_QBOX
     - Qbox stopped with error
   * - 400
     - ERROR_OUT_OF_WALLTIME
     - Calculation exceeded walltime
   * - 410
     - ERROR_CONVERGENCE_NOT_REACHED
     - SCF/geometry not converged
   * - 500
     - ERROR_UNKNOWN
     - Unknown error

Plus workchain-level exit codes:

* 401 — ERROR_MAXIMUM_ITERATIONS_EXCEEDED
* 402 — ERROR_PARENT_FOLDER_INVALID
* 403 — ERROR_UNRECOVERABLE_FAILURE
* 410 — ERROR_FORCES_NOT_CONVERGED (relax)
* 420 — ERROR_MD_INCOMPLETE (md)

Recovery Handlers
+++++++++++++++++

.. list-table:: Handler Priority & Actions
   :header-rows: 1
   :widths: 20 20 60

   * - Handler
     - Priority
     - Action
   * - ``handle_killed`` (OOM)
     - 600
     - Read ``_scheduler-stderr.txt``; if OOM marker → **abort**; else (walltime) → double walltime, restart
   * - ``handle_killed`` (walltime)
     - 600
     - Double ``max_wallclock_seconds``, restart from remote
   * - ``handle_qbox_error``
     - 590
     - **Abort** — rerun won't fix bad input/environment
   * - ``handle_convergence_failure``
     - 500
     - Restart with ``max_scf += original_budget``; abort if no SCF progress
   * - ``handle_retrieve_failure``
     - 550
     - Retry **once** from ``remote_folder``; abort on second failure

Convergence Failure Recovery
++++++++++++++++++++++++++++

When SCF hits ``max_scf`` without converging (exit 410):

1. Workchain reads ``scf_iter`` from failed calculation's output
2. Increases ``max_scf`` by the original budget (default 100)
3. Sets ``wf_dyn`` to restart mode (if applicable)
4. Resubmits from ``remote_folder`` of failed calculation
5. **Aborts** if the attempt made zero SCF progress (prevents infinite loops)

.. code-block:: python

   # In your workchain inputs:
   builder.max_iterations = orm.Int(5)  # max restart attempts
   # Default budget = 100 SCF iterations per restart

Walltime Kill Recovery
++++++++++++++++++++++

When job is killed by scheduler (exit 312/400):

1. Check ``_scheduler-stderr.txt`` for OOM markers
2. If **OOM** (``out of memory``, ``oom-kill``, ``segmentation fault``, etc.) → **abort** with message about memory per MPI rank
3. If **walltime** (no OOM marker) → double ``max_wallclock_seconds``, restart

.. code-block:: python

   builder.qbox.metadata.options.max_wallclock_seconds = 3600
   # If killed → 7200 → 14400 → ...

OOM Detection
+++++++++++++

The ``scheduler_stderr()`` utility reads ``_scheduler-stderr.txt`` from the
retrieved folder and checks for markers (case-insensitive):

* ``out of memory``
* ``oom-kill`` / ``oom_kill``
* ``memory allocation failed``
* ``cannot allocate memory``
* ``bad termination``
* ``mpi_abort``
* ``sigkill`` / ``killed by signal``
* ``segmentation fault`` / ``segfault``

Qbox Error Recovery
+++++++++++++++++++

When Qbox prints ``ERROR: ...`` or ``<error>...</error>`` (exit 330):

* **Always aborts** — rerunning the same input won't fix it
* Error message preserved in workchain report

Retrieve Failure Recovery
+++++++++++++++++++++++++

When XML/stdout missing from retrieved (exit 302/320/321/322):

1. Retry **once** from the failed calculation's ``remote_folder``
2. If still fails → **abort** (exit 403)

Maximum Restart Attempts
++++++++++++++++++++++++

Controlled by ``max_iterations`` input (default: 5 for base/md, 10 for relax, 3 for server):

.. code-block:: python

   builder.max_iterations = orm.Int(5)

After exceeding, workchain exits with 401 (ERROR_MAXIMUM_ITERATIONS_EXCEEDED).

Force Convergence (Relax WorkChain)
+++++++++++++++++++++++++++++++++++

``QboxRelaxWorkChain`` checks forces in ``results()``:

.. code-block:: python

   builder.force_tolerance = orm.Float(1e-4)  # Ry/bohr
   # If max |F| > tolerance → exit 410

MD Step Tracking (MD WorkChain)
+++++++++++++++++++++++++++++++

``QboxMDWorkChain`` tracks completed MD steps across restarts:

.. code-block:: python

   builder.target_md_steps = orm.Int(1000)
   # If completed < target → exit 420 (ERROR_MD_INCOMPLETE)

   # Tracks md_step from output_parameters across restarts
   # Resumes from last completed step

Inspecting Failures
+++++++++++++++++++

Use ``verdi process report <pk>`` to see which handler fired:

.. code-block:: shell

   verdi process report 12345

Or programmatically:

.. code-block:: python

   from aiida import load_profile, orm
   load_profile()
   wc = orm.load_node(12345)
   for child in wc.called:
       print(child.pk, child.exit_status, child.exit_message)
       if 'output_parameters' in child.outputs:
           print(child.outputs.output_parameters.get_dict())