=========
Testing
=========

Test Structure
++++++++++++++

.. code-block:: text

   tests/
   ├── __init__.py
   ├── conftest.py              # AiiDA pytest fixtures
   ├── test_calculations.py     # CalcJob specs
   ├── test_parsers.py          # Parser utilities
   ├── test_parsers_real_output.py  # Real Qbox output fixtures
   ├── test_recovery.py         # Recovery utilities
   ├── test_workchains.py       # WorkChain specs
   └── fixtures/                # Real Qbox outputs
       ├── scf_converged/
       │   ├── aiida.out
       │   ├── qbox.xml
       │   └── expected.json
       ├── relax_converged/
       ├── md_complete/
       └── README.md

Running Tests
+++++++++++++

.. code-block:: shell

   # All tests
   pytest tests/ -v

   # With coverage
   pytest --cov=aiida_qbox tests/

   # Specific module
   pytest tests/test_parsers.py -v

Fixtures
++++++++

The ``conftest.py`` uses modern AiiDA test fixtures:

.. code-block:: python

   # tests/conftest.py
   import pytest
   pytest_plugins = ['aiida.tools.pytest_fixtures']

   # Available fixtures:
   # aiida_profile, aiida_profile_clean, aiida_code, aiida_localhost,
   # aiida_computer, submit_and_await, etc.

Unit Tests
++++++++++

Calculation Specs
-----------------

.. code-block:: python

   def test_qbox_base_calculation_define():
       spec = QboxBaseCalculation.spec()
       assert 'parameters' in spec.inputs
       assert 'output_parameters' in spec.outputs
       exit_codes = list(spec.exit_codes.keys())
       assert 'ERROR_NO_RETRIEVED_FOLDER' in exit_codes

Parser Utilities
----------------

.. code-block:: python

   def test_parse_qbox_xml():
       parsed = parse_qbox_xml(SAMPLE_XML)
       assert parsed['etotal'] == -15.6789
       assert 'forces' in parsed

   def test_cpu_time_seconds():
       assert cpu_time_seconds('cpu time: 123.45 s') == 123.45

Recovery Utilities
------------------

.. code-block:: python

   def test_find_fatal_marker():
       assert find_fatal_marker('Out of memory') == 'out of memory'
       assert find_fatal_marker('normal output') is None

   def test_next_max_scf():
       assert next_max_scf(50, 100) == 150

   def test_abort():
       wc = MockWorkChain()
       report = abort(wc, 'test')
       assert report.do_break is True
       assert report.exit_code == 403

WorkChain Specs
---------------

.. code-block:: python

   def test_qbox_base_workchain_define():
       spec = QboxBaseWorkChain.spec()
       assert 'qbox' in spec.inputs
       exit_codes = list(spec.exit_codes.keys())
       assert 'ERROR_MAXIMUM_ITERATIONS_EXCEEDED' in exit_codes

Real Output Fixtures
--------------------

Fixtures in ``tests/fixtures/`` with real Qbox outputs:

.. code-block:: python

   def test_xml_parsing_fixtures():
       for fixture_path in FIXTURE_DIR.iterdir():
           if not fixture_path.is_dir(): continue
           xml = (fixture_path / 'qbox.xml').read_text()
           parsed = parse_qbox_xml(xml)
           assert isinstance(parsed, dict)
           if 'etotal' in parsed:
               assert isinstance(parsed['etotal'], float)

Integration Tests (Requires pgtest)
-----------------------------------

Full integration tests require AiiDA pgtest fixtures to create real
calculation nodes:

.. code-block:: shell

   pytest tests/test_workchain_integration.py -v --pgtest

These test actual handler execution with mock calculation nodes.

Adding New Fixtures
+++++++++++++++++++

1. Run a real Qbox calculation
2. Copy ``stdout`` and ``qbox.xml`` to ``tests/fixtures/new_case/``
3. Create ``expected.json`` with expected parsed values
4. Add test case in ``test_parsers_real_output.py``