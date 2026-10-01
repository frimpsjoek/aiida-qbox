======================
Adding Calculations
======================

To add a new Qbox calculation mode (e.g., TDDFT, GW, etc.):

1. Create the CalcJob
+++++++++++++++++++++

.. code-block:: python

   # aiida_qbox/calculations/newmode.py
   from aiida import orm
   from aiida.common import datastructures
   from aiida.engine import CalcJob
   from aiida_qbox.utils import get_parent_qbox_prefix, get_parent_save_subdir

   class NewModeCalculation(CalcJob):
       _DEFAULT_INPUT_FILE = 'newmode.in'
       _DEFAULT_OUTPUT_FILE = 'newmode.out'
       _DEFAULT_PARSER = 'qbox.newmode'

       @classmethod
       def define(cls, spec):
           super().define(spec)
           # ... inputs, outputs, exit codes ...

       def prepare_for_submission(self, folder):
           # Write input, setup remote_copy_list, calcinfo
           return calcinfo

2. Register Entry Point
+++++++++++++++++++++++

In ``pyproject.toml``:

.. code-block:: toml

   [project.entry-points."aiida.calculations"]
   "qbox.newmode" = "aiida_qbox.calculations.newmode:NewModeCalculation"

3. Create Parser
++++++++++++++++

.. code-block:: python

   # aiida_qbox/parsers/newmode.py
   from aiida.parsers import Parser
   from aiida_qbox.parsers.qbox_output import parse_qbox_xml

   class NewModeParser(Parser):
       def parse(self, **kwargs):
           # Parse stdout + XML
           return exit_code_or_none

4. Register Parser
++++++++++++++++++

In ``pyproject.toml``:

.. code-block:: toml

   [project.entry-points."aiida.parsers"]
   "qbox.newmode" = "aiida_qbox.parsers.newmode:NewModeParser"

5. Add Tests
++++++++++++

.. code-block:: python

   # tests/test_calculations.py
   def test_newmode_calculation_define():
       spec = NewModeCalculation.spec()
       # assert inputs/outputs/exit_codes