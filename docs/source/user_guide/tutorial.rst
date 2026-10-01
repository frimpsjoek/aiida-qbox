========
Tutorial
========

This tutorial walks through common Qbox workflows using the aiida-qbox plugin.
All examples assume you have completed the :doc:`get_started` setup.

.. contents::
   :local:
   :depth: 2

SCF with Hybrid Functionals (PBE0)
++++++++++++++++++++++++++++++++++

Hybrid functionals use recursive subspace bisection for O(N) scaling.
The ``hybrid`` protocol includes bisection parameters.

.. code-block:: python

   from aiida_qbox.workflows.protocols import get_protocol
   protocol = get_protocol('hybrid')  # or 'hybrid_relax' for optimization

   # Parameters include:
   #   set xc: 'PBE0'
   #   set blHF: '3 3 3'      # bisection levels (x,y,z)
   #   set btHF: '0.01'       # threshold (error ~1e-3 au)

   builder.qbox.parameters = orm.Dict(dict=protocol['parameters'])

   # For DDH (dielectric-dependent hybrid), set alpha_PBE0 = 1/eps_inf
   # e.g., Si with eps_inf = 12.1 -> alpha_PBE0 = 0.0826
   ddh_protocol = get_protocol('ddh')
   ddh_protocol['parameters']['set alpha_PBE0'] = '0.0826'

HSE06 Range-Separated Hybrid
++++++++++++++++++++++++++++

.. code-block:: python

   protocol = get_protocol('hse')  # or 'hse_relax'
   # Parameters:
   #   set xc: 'HSE'
   #   set muRSH: '0.2'       # screening parameter
   #   set alphaRSH: '0.25'   # SR HF fraction
   #   set betaRSH: '0.0'     # LR HF fraction (0 for HSE06)

Finite-Field Polarization
+++++++++++++++++++++++++

For finite-field response calculations (used by WEST):

.. code-block:: python

   protocol = get_protocol('finite_field')
   # Parameters include:
   #   set e_field: '0 0 0.001'  # perturbative field along z

   # The response density gives the screened interaction:
   # tau(r) = delta V_pert(r) + int v_c(r,r') delta rho(r') dr'

Nosé-Hoover Thermostat MD
+++++++++++++++++++++++++

.. code-block:: python

   protocol = get_protocol('thermostat_md')
   # Parameters:
   #   set thermostat: 'NOSE'
   #   set th_temp: '300'      # target temperature (K)
   #   set th_time: '100'      # thermostat time constant
   #   set th_width: '0.1'     # thermostat width

Berry-Phase Polarization
++++++++++++++++++++++++

.. code-block:: python

   protocol = get_protocol('polarization')
   # Parameters:
   #   set polarization: 'BERRY'

   # Output includes polarization vector in output_parameters

Variable-Cell Relaxation
++++++++++++++++++++++++

.. code-block:: python

   protocol = get_protocol('cell_relax')
   # Parameters:
   #   set atoms_dyn: 'CG'
   #   set cell_dyn: 'CG'
   #   set stress: 'ON'

Using the CLI
+++++++++++++

List all available protocols:

.. code-block:: shell

   aiida-qbox data-cmd show-protocols

Parse XML output from a completed calculation:

.. code-block:: shell

   aiida-qbox data-cmd parse-xml 12345

Inspect input parameters:

.. code-block:: shell

   aiida-qbox data-cmd show-params 12345

Inspect output parameters:

.. code-block:: shell

   aiida-qbox data-cmd show-output 12345

Complete Example: Silicon Band Structure with PBE0
++++++++++++++++++++++++++++++++++++++++++++++++++

.. code-block:: python

   from aiida.plugins import WorkflowFactory
   from aiida import orm
   from aiida.engine import run_get_node
   from aiida_qbox.workflows.protocols import get_protocol

   QboxRelaxWorkChain = WorkflowFactory('qbox.relax')

   # 1. Geometry optimization with PBE
   relax_protocol = get_protocol('relax')
   relax_protocol['parameters']['set cell'] = '10.26 0 0  0 10.26 0  0 0 10.26'
   relax_protocol['parameters']['species Si'] = 'Si_PBE.xml'
   relax_protocol['parameters']['atom Si1 Si'] = '1.3575 1.3575 1.3575'
   relax_protocol['parameters']['atom Si2 Si'] = '-1.3575 -1.3575 -1.3575'

   builder = QboxRelaxWorkChain.get_builder()
   builder.qbox.code = orm.Code.get(label='qb-1.0@localhost')
   builder.qbox.parameters = orm.Dict(dict=relax_protocol['parameters'])
   builder.qbox.metadata.options = {
       'max_wallclock_seconds': 7200,
       'withmpi': True,
       'resources': {'num_machines': 1, 'num_mpiprocs_per_machine': 4},
   }
   builder.force_tolerance = orm.Float(1e-4)
   builder.max_iterations = orm.Int(10)

   relax_results, relax_node = run_get_node(builder)
   print(f"Relaxed energy: {relax_results['output_parameters'].get_dict()['etotal']:.6f} Ry")

   # 2. Single-point PBE0 on relaxed structure
   hybrid_protocol = get_protocol('hybrid')
   hybrid_protocol['parameters']['set cell'] = relax_protocol['parameters']['set cell']
   hybrid_protocol['parameters']['species Si'] = 'Si_PBE.xml'
   # Use relaxed positions from output
   relax_out = relax_results['output_parameters'].get_dict()
   # ... extract positions from relax_out['positions'] ...

   QboxBaseWorkChain = WorkflowFactory('qbox.base')
   builder = QboxBaseWorkChain.get_builder()
   builder.qbox.code = orm.Code.get(label='qb-1.0@localhost')
   builder.qbox.parameters = orm.Dict(dict=hybrid_protocol['parameters'])
   builder.qbox.metadata.options = {
       'max_wallclock_seconds': 14400,
       'withmpi': True,
       'resources': {'num_machines': 1, 'num_mpiprocs_per_machine': 8},
   }
   builder.max_iterations = orm.Int(5)

   scf_results, scf_node = run_get_node(builder)
   print(f"PBE0 energy: {scf_results['output_parameters'].get_dict()['etotal']:.6f} Ry")

This gives you the PBE0 total energy on the PBE-relaxed structure —
a common workflow for band gap calculations.