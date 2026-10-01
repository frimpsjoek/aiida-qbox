Architecture
============

Plugin Structure
++++++++++++++++

.. code-block:: text

   aiida_qbox/
   ├── __init__.py                 # version
   ├── calculations/               # CalcJob plugins
   │   ├── __init__.py
   │   ├── base.py                 # qbox.base (standard runs)
   │   └── server.py               # qbox.server (WEST coupling)
   ├── parsers/                    # Output parsers
   │   ├── __init__.py
   │   ├── base.py                 # qbox.base parser
   │   ├── server.py               # qbox.server parser
   │   └── qbox_output.py          # Shared XML/stdout utilities
   ├── workchains/                 # WorkChains with error handling
   │   ├── __init__.py
   │   ├── base.py                 # QboxBaseWorkChain
   │   ├── relax.py                # QboxRelaxWorkChain
   │   ├── md.py                   # QboxMDWorkChain
   │   ├── server.py               # QboxServerWorkChain
   │   └── recovery.py             # Shared error recovery utilities
   ├── workflows/                  # Protocols
   │   ├── __init__.py
   │   ├── protocols.py            # 16 built-in protocols
   │   └── protocols/              # YAML protocol files
   ├── cli/                        # Command-line tools
   │   ├── __init__.py
   │   ├── setup/codes.py          # Code setup commands
   │   └── data.py                 # Data inspection commands
   ├── utils/                      # Utility functions
   │   ├── __init__.py
   │   └── parent_folder.py        # Prefix/subdir extraction
   └── tools/                      # Programmatic setup
       ├── __init__.py
       └── setup.py

Entry Points
++++++++++++

Registered in ``pyproject.toml``:

.. code-block:: toml

   [project.entry-points."aiida.calculations"]
   "qbox.base" = "aiida_qbox.calculations.base:QboxBaseCalculation"
   "qbox.server" = "aiida_qbox.calculations.server:QboxServerCalculation"

   [project.entry-points."aiida.parsers"]
   "qbox.base" = "aiida_qbox.parsers.base:QboxBaseParser"
   "qbox.server" = "aiida_qbox.parsers.server:QboxServerParser"

   [project.entry-points."aiida.workflows"]
   "qbox.base" = "aiida_qbox.workchains.base:QboxBaseWorkChain"
   "qbox.relax" = "aiida_qbox.workchains.relax:QboxRelaxWorkChain"
   "qbox.md" = "aiida_qbox.workchains.md:QboxMDWorkChain"
   "qbox.server" = "aiida_qbox.workchains.server:QboxServerWorkChain"

Calculation Plugins
++++++++++++++++++++

``QboxBaseCalculation``
   Standard Qbox runs (SCF, relax, MD, CPMD).
   Input: ``parameters`` (Dict with ``set`` commands), optional ``parent_folder``.
   Output: ``output_parameters`` (Dict), ``output_xml`` (SinglefileData), ``remote_folder``.

``QboxServerCalculation``
   Client-server mode for WEST finite-field coupling.
   Required: ``parent_folder``, ``parameters``, ``server_input_file``, ``server_output_file``.
   Runs ``qb -i input -s qb_in qb_out``.

Parser Utilities (``qbox_output.py``)
+++++++++++++++++++++++++++++++++++++

* ``parse_qbox_xml(xml)`` — Extract ``etotal``, ``forces``, ``positions``, ``cell``, ``stress``, ``cpu_time``, ``wall_time``
* ``cpu_time_seconds(stdout)`` / ``wall_time_seconds(stdout)`` — Timing extraction
* ``find_qbox_error(stdout)`` — Detect ``ERROR:``, ``qbox: error:``, ``<error>``
* ``is_complete(stdout)`` — Check ``<status>completed</status>`` or ``run ... completed``

WorkChain Base Class
++++++++++++++++++++

All workchains inherit from ``BaseRestartWorkChain`` and implement:

* ``setup()`` — Initialize context (budget, iteration counters)
* ``validate_inputs()`` — Check parent folder
* ``prepare_process()`` — Mutate inputs before resubmit (increase ``max_scf``, double walltime)
* ``_restart_if_progress()`` — Common restart logic with progress check
* Handlers: ``handle_killed``, ``handle_qbox_error``, ``handle_convergence_failure``, ``handle_retrieve_failure``

Recovery Utilities (``recovery.py``)
++++++++++++++++++++++++++++++++++++

* ``find_fatal_marker(text)`` — OOM/sigkill detection
* ``scheduler_stderr(calc)`` — Read ``_scheduler-stderr.txt``
* ``abort(wc, msg)`` — Stop workchain with ERROR_UNRECOVERABLE_FAILURE
* ``next_max_scf(current, budget)`` — ``current + budget``
* ``made_scf_progress(prev, current)`` — Progress check

Protocol System
+++++++++++++++

* ``BUILTIN_PROTOCOLS`` dict with 16 protocols
* ``get_protocol(name)`` / ``list_protocols()``
* YAML files in ``workflows/protocols/``
* ``load_protocol_file()`` / ``save_protocol()``

CLI Commands
++++++++++++

``aiida-qbox setup-codes``
   Auto-detect (``auto``), manual (``qbox LABEL``), list

``aiida-qbox data-cmd``
   ``show-protocols``, ``parse-xml <pk>``, ``show-params <pk>``, ``show-output <pk>``

Testing
+++++++

* ``pytest tests/`` — 23 unit tests
* Fixtures in ``tests/fixtures/`` with real Qbox outputs
* Recovery utilities tested in ``test_recovery.py``