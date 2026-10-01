Getting started
===============

``aiida-qbox`` is an AiiDA plugin that wraps the
`Qbox code <https://qboxcode.org>`_ for FPMD/DFT electronic-structure
calculations with hybrid functionals, and provides client-server mode
for finite-field coupling with `WEST <https://west-code.org>`_.

It exposes Qbox's ``qb`` executable as AiiDA ``CalcJob`` plugins
with two modes:

* **Standard mode** (``qbox.base``) — SCF, geometry optimization, Born-Oppenheimer MD, CPMD
* **Server mode** (``qbox.server``) — Persistent server for WEST finite-field coupling

And four ``WorkChain`` orchestrators with automated error recovery:

* ``qbox.base`` — Restart-aware wrapper for standard calculations
* ``qbox.relax`` — Geometry optimization with force convergence checking
* ``qbox.md`` — Molecular dynamics with step tracking across restarts
* ``qbox.server`` — Server lifecycle management for WEST coupling

.. admonition:: Compatibility
   :class: note

   Driven end-to-end against:

   * Qbox binaries built against QE 7.x
   * ``aiida-core`` **2.9**
   * ``aiida-quantumespresso`` **5.1**

Installation
++++++++++++

.. code-block:: shell

   git clone https://github.com/frimpsjoek/aiida-qbox.git
   cd aiida-qbox
   pip install -e .                  # editable install
   verdi plugin list aiida.workflows | grep qbox   # sanity check

Six workflow entry points should appear:
``qbox.base``, ``qbox.relax``, ``qbox.md``, ``qbox.server``.

AiiDA profile
+++++++++++++

For quick single-system runs you don't need Docker, PostgreSQL, or RabbitMQ.
A broker-less SQLite profile works:

.. code-block:: shell

   verdi presto --profile-name aiida-presto --non-interactive

On this profile you submit calculations synchronously via
``aiida.engine.run_get_node``. For batch sweeps, configure a full profile
with a RabbitMQ broker and start the AiiDA daemon — none of the plugin's
logic changes.

Register the codes
++++++++++++++++++

Auto-detect Qbox executables:

.. code-block:: shell

   aiida-qbox setup-codes auto

Or manually for each code (pw.x for structure, qb for Qbox):

.. code-block:: shell

   for code in pw:quantumespresso.pw qb:qbox.base; do
       label=${code%:*}
       plug=${code#*:}
       verdi code create core.code.installed \
           --non-interactive --label "$label" \
           --computer localhost \
           --filepath-executable "$(which ${label}.x)" \
           --default-calc-job-plugin "$plug"
   done

Install pseudopotentials
++++++++++++++++++++++++

Qbox uses **XML pseudopotentials** (same format as QE but .xml extension).
If you have a UPF library, convert it or download XML directly.

.. code-block:: python

   from pathlib import Path
   from aiida import load_profile
   from aiida_pseudo.groups.family.pseudo import PseudoPotentialFamily
   from aiida_pseudo.data.pseudo.upf import UpfData
   load_profile('aiida-presto')
   PseudoPotentialFamily.create_from_folder(
       Path('/path/to/xml_pseudos'),
       label='Qbox/XML/PBE/SR',
       description='Qbox XML PBE scalar-relativistic',
       pseudo_type=UpfData,
   )

For SG15 ONCV: download XML from `pseudopotentials.quantum-simulation.org <https://pseudopotentials.quantum-simulation.org>`_.

Run SCF on Silicon
++++++++++++++++++

The canonical entry point for a standard calculation is ``QboxBaseWorkChain``
(or ``QboxBaseCalculation`` for direct submission).

See ``examples/run_scf_silicon.py`` for the complete, runnable script.

.. code-block:: python

   from aiida.plugins import WorkflowFactory
   from aiida import orm
   from aiida.engine import submit

   QboxBaseWorkChain = WorkflowFactory('qbox.base')
   builder = QboxBaseWorkChain.get_builder()

   # Qbox parameters using protocol
   from aiida_qbox.workflows.protocols import get_protocol
   protocol = get_protocol('scf')
   builder.qbox.parameters = orm.Dict(dict=protocol['parameters'])

   # Or customize manually
   builder.qbox.parameters = orm.Dict(dict={
       'set cell': '10.26 0 0  0 10.26 0  0 0 10.26',
       'species Si': 'Si_PBE.xml',
       'atom Si1 Si': '1.3575 1.3575 1.3575',
       'atom Si2 Si': '-1.3575 -1.3575 -1.3575',
       'set ecut': '30',
       'set xc': 'PBE',
       'set wf_dyn': 'PSDA',
       'set scf_tol': '1e-8',
       'set max_scf': '100',
       'randomize_wf': '',
       'run': '0 100',
   })

   builder.qbox.code = orm.Code.get(label='qb-1.0@localhost')
   builder.qbox.metadata.options = {
       'max_wallclock_seconds': 3600,
       'withmpi': True,
       'resources': {'num_machines': 1, 'num_mpiprocs_per_machine': 4},
   }
   builder.max_iterations = orm.Int(5)
   builder.clean_workdir = orm.Bool(False)

   from aiida.engine import run_get_node
   results, node = run_get_node(builder)
   out = results['output_parameters'].get_dict()
   print(f"Total energy: {out['etotal']:.6f} Ry")
   print(f"Converged: {out['converged']}")

On a 14-core M-series Mac with ``num_mpiprocs_per_machine=4``, this takes
~2 minutes for Si and returns a total energy of **-15.68 Ry**.

Run Geometry Optimization
+++++++++++++++++++++++++

Use ``QboxRelaxWorkChain`` which adds force convergence checking and
automatically restarts on SCF convergence failure.

.. code-block:: python

   QboxRelaxWorkChain = WorkflowFactory('qbox.relax')
   builder = QboxRelaxWorkChain.get_builder()

   builder.qbox.parameters = orm.Dict(dict={
       'set cell': '10.26 0 0  0 10.26 0  0 0 10.26',
       'species Si': 'Si_PBE.xml',
       'atom Si1 Si': '1.3575 1.3575 1.3575',
       'atom Si2 Si': '-1.3575 -1.3575 -1.3575',
       'set ecut': '30',
       'set xc': 'PBE',
       'set wf_dyn': 'PSDA',
       'set scf_tol': '1e-8',
       'set max_scf': '100',
       'set atoms_dyn': 'CG',
       'set dt': '10',
       'randomize_wf': '',
       'run': '0 100',
   })
   builder.force_tolerance = orm.Float(1e-4)  # Ry/bohr
   builder.max_iterations = orm.Int(10)

   results, node = run_get_node(builder)
   out = results['output_parameters'].get_dict()
   print(f"Final energy: {out['etotal']:.6f} Ry")
   for atom, force in out.get('forces', {}).items():
       max_f = max(abs(f) for f in force)
       print(f"  {atom}: max |F| = {max_f:.2e} Ry/bohr")

Run Molecular Dynamics
++++++++++++++++++++++

Use ``QboxMDWorkChain`` for Born-Oppenheimer or Car-Parrinello MD
with step tracking across restarts.

.. code-block:: python

   QboxMDWorkChain = WorkflowFactory('qbox.md')
   builder = QboxMDWorkChain.get_builder()

   builder.qbox.parameters = orm.Dict(dict={
       'set cell': '15.0 0 0  0 15.0 0  0 0 15.0',
       'species O': 'O_HSCV_PBE.xml',
       'species H': 'H_HSCV_PBE.xml',
       'atom O1 O': '7.5 7.5 7.5',
       'atom H1 H': '8.0 7.5 7.5',
       'atom H2 H': '7.5 8.0 7.5',
       'set ecut': '50',
       'set xc': 'PBE',
       'set wf_dyn': 'PSDA',
       'set scf_tol': '1e-6',
       'set max_scf': '50',
       'set atoms_dyn': 'MD',
       'set dt': '5',
       'randomize_wf': '',
       'run': '1000 1000',
   })
   builder.target_md_steps = orm.Int(1000)
   builder.max_iterations = orm.Int(5)

   results, node = run_get_node(builder)

Run Qbox Server for WEST Finite-Field Coupling
++++++++++++++++++++++++++++++++++++++++++++++

The server runs persistently, accepting perturbations from WEST via
lock-file synchronization.

.. code-block:: python

   QboxServerWorkChain = WorkflowFactory('qbox.server')
   builder = QboxServerWorkChain.get_builder()

   # Requires converged ground state calculation
   gs_node = orm.load_node(PK_OF_GS_CALC)
   builder.qbox.parent_folder = gs_node.outputs.remote_folder

   builder.qbox.parameters = orm.Dict(dict={
       'set ecut': '30',
       'set xc': 'PBE',
       'set wf_dyn': 'PSDA',
       'set scf_tol': '1e-8',
       'set max_scf': '100',
       'randomize_wf': '',
       'run': '0 100',
   })
   builder.max_iterations = orm.Int(3)

   # Submit and keep running until WEST sends 'quit'
   wc = submit(builder)
   print(f"Server started: PK={wc.pk}")

What lives where in the outputs
+++++++++++++++++++++++++++++++

``QboxBaseWorkChain`` outputs:

* ``output_parameters`` — Dict with ``etotal``, ``forces``, ``positions``, ``cell``, ``cpu_time``, ``wall_time``, ``converged``, ``scf_iter``
* ``output_xml`` — SinglefileData with full sample XML
* ``remote_folder`` — RemoteData for restarts

``QboxRelaxWorkChain`` additionally checks force convergence.

``QboxMDWorkChain`` tracks ``md_step`` across restarts.

``QboxServerWorkChain`` maintains persistent server state.

Available calculations and workchains
+++++++++++++++++++++++++++++++++++++

Two ``CalcJob`` plugins:

* ``qbox.base`` — Standard Qbox runs (SCF, relax, MD, CPMD)
* ``qbox.server`` — Client-server mode for WEST finite-field coupling

Four ``WorkChain`` plugins:

* ``qbox.base`` — Restart-aware wrapper for standard calculations
* ``qbox.relax`` — Geometry optimization with force convergence
* ``qbox.md`` — Molecular dynamics with step tracking
* ``qbox.server`` — Server lifecycle for WEST coupling

See ``CHANGELOG.md`` for the full list of features and bug fixes.