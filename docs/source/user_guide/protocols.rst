=========
Protocols
=========

``aiida-qbox`` includes 16 built-in protocols for common Qbox calculation types.
Each protocol is a dictionary with ``description`` and ``parameters`` keys.

Listing Protocols
+++++++++++++++++

.. code-block:: python

   from aiida_qbox.workflows.protocols import list_protocols, get_protocol

   print(list_protocols())
   # {'scf': 'Single-point SCF calculation',
   #  'relax': 'Geometry optimization with CG',
   #  ...}

   protocol = get_protocol('hybrid_relax')
   print(protocol['description'])
   print(protocol['parameters'])

Using a Protocol
++++++++++++++++

.. code-block:: python

   from aiida_qbox.workflows.protocols import get_protocol
   from aiida.plugins import WorkflowFactory

   protocol = get_protocol('hybrid_relax')
   parameters = protocol['parameters'].copy()

   # Customize for your system
   parameters['set cell'] = '10.26 0 0  0 10.26 0  0 0 10.26'
   parameters['species Si'] = 'Si_PBE.xml'
   parameters['atom Si1 Si'] = '1.3575 1.3575 1.3575'
   parameters['atom Si2 Si'] = '-1.3575 -1.3575 -1.3575'

   QboxRelaxWorkChain = WorkflowFactory('qbox.relax')
   builder = QboxRelaxWorkChain.get_builder()
   builder.qbox.parameters = orm.Dict(dict=parameters)
   # ... submit ...

Protocol Reference
++++++++++++++++++

.. list-table:: Built-in Protocols
   :header-rows: 1
   :widths: 20 30 50

   * - Protocol
     - Description
     - Key Parameters
   * - ``scf``
     - Single-point SCF calculation
     - ``xc=PBE, wf_dyn=PSDA, scf_tol=1e-8, max_scf=100``
   * - ``relax``
     - Geometry optimization with CG
     - ``+ atoms_dyn=CG, dt=10``
   * - ``md``
     - Born-Oppenheimer MD
     - ``+ atoms_dyn=MD, dt=5, scf_tol=1e-6, max_scf=50``
   * - ``cpmd``
     - Car-Parrinello MD
     - ``wf_dyn=MD, atoms_dyn=MD, dt=3, mass=400``
   * - ``hybrid``
     - PBE0 SCF with bisection
     - ``xc=PBE0, blHF=3 3 3, btHF=0.01, max_scf=150``
   * - ``hybrid_relax``
     - PBE0 geometry optimization
     - ``+ atoms_dyn=CG, dt=10``
   * - ``hse``
     - HSE06 SCF
     - ``xc=HSE, muRSH=0.2, alphaRSH=0.25, betaRSH=0.0``
   * - ``hse_relax``
     - HSE06 geometry optimization
     - ``+ atoms_dyn=CG, dt=10``
   * - ``ddh``
     - DDH SCF (alpha=1/eps_inf)
     - ``xc=PBE0, alpha_PBE0=0.25, blHF=3 3 3, btHF=0.01``
   * - ``ddh_relax``
     - DDH geometry optimization
     - ``+ atoms_dyn=CG, dt=10``
   * - ``finite_field``
     - Finite-field polarization
     - ``e_field=0 0 0.001``
   * - ``thermostat_md``
     - Nosé-Hoover NVT MD
     - ``thermostat=NOSE, th_temp=300, th_time=100``
   * - ``polarization``
     - Berry-phase polarization
     - ``polarization=BERRY``
   * - ``cell_relax``
     - Variable-cell CG
     - ``cell_dyn=CG, stress=ON``
   * - ``server_init``
     - WEST finite-field server
     - Same as ``scf`` protocol

Loading/Saving Custom Protocols
+++++++++++++++++++++++++++++++

.. code-block:: python

   from aiida_qbox.workflows.protocols import load_protocol_file, save_protocol

   # Load from YAML file
   protocol = load_protocol_file('my_protocol.yaml')

   # Save to YAML file
   save_protocol(protocol, 'my_protocol.yaml')

YAML format example (``my_protocol.yaml``):

.. code-block:: yaml

   description: "Custom PBE0 with tighter convergence"
   parameters:
     set ecut: "40"
     set xc: "PBE0"
     set wf_dyn: "PSDA"
     set scf_tol: "1e-9"
     set max_scf: "200"
     set blHF: "3 3 3"
     set btHF: "0.01"
     randomize_wf: ""
     run: "0 200"

Modifying Protocol Parameters
+++++++++++++++++++++++++++++

.. code-block:: python

   protocol = get_protocol('hybrid_relax')
   params = protocol['parameters']

   # Override specific values
   params['set ecut'] = '50'
   params['set scf_tol'] = '1e-9'
   params['set max_scf'] = '200'

   # For DDH, set alpha_PBE0 = 1/eps_inf
   ddh = get_protocol('ddh')
   ddh['parameters']['set alpha_PBE0'] = '0.0826'  # Si: eps_inf = 12.1

CLI Access
++++++++++

.. code-block:: shell

   # List all protocols
   aiida-qbox data-cmd show-protocols

   # Output:
   #   scf: Single-point SCF calculation
   #   relax: Geometry optimization with CG
   #   md: Born-Oppenheimer MD
   #   ...