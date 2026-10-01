==================
Adding Parsers
==================

Qbox output parsing is centralized in ``qbox_output.py`` and extended by
specific parser classes.

Parser Interface
++++++++++++++++

.. code-block:: python

   from aiida.parsers import Parser
   from aiida import orm

   class MyParser(Parser):
       def parse(self, **kwargs):
           # 1. Get retrieved folder
           try:
               files = walk_files(self.retrieved)
           except Exception:
               return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

           # 2. Read stdout
           stdout = self.retrieved.base.repository.get_object_content(
               self.node.get_option('output_filename')
           )

           # 3. Parse stdout for timing, version, convergence
           parsed = self._parse_stdout(stdout)

           # 4. Find and parse XML
           xml_file = next((f for f in files if f.endswith('.xml')), None)
           if xml_file:
               xml = self.retrieved.base.repository.get_object_content(xml_file)
               parsed.update(parse_qbox_xml(xml))

           # 5. Check for errors
           if find_qbox_error(stdout):
               return self.exit_codes.ERROR_QBOX.format(message=error)

           # 6. Check completion
           if not is_complete(stdout):
               return self.exit_codes.ERROR_OUTPUT_STDOUT_INCOMPLETE

           # 7. Check convergence
           if not self._check_convergence(parsed, stdout):
               return self.exit_codes.ERROR_CONVERGENCE_NOT_REACHED

           # 8. Output results
           self.out('output_parameters', orm.Dict(parsed))
           if xml_file:
               self.out('output_xml', orm.SinglefileData(...))

           return None

Shared Utilities (``qbox_output.py``)
+++++++++++++++++++++++++++++++++++++

.. code-block:: python

   from aiida_qbox.parsers.qbox_output import (
       parse_qbox_xml,      # Dict with etotal, forces, positions, cell, stress, timing
       cpu_time_seconds,    # float from stdout
       wall_time_seconds,   # float from stdout
       find_qbox_error,     # error string or None
       is_complete,         # bool from stdout
       walk_files,          # Dict[str, str] from FolderData
   )

XML Structure
+++++++++++++

Qbox XML follows the ``fpmd`` namespace:

.. code-block:: xml

   <sample xmlns="http://www.quantum-simulation.org/ns/fpmd/fpmd-1.0">
     <etotal>-15.6789</etotal>
     <atomset>
       <unit_cell a="..." b="..." c="..."/>
       <species name="Si" mass="28.0855" pseudo="..."/>
       <atom name="Si1" species="Si">
         <position>1.3575 1.3575 1.3575</position>
         <force>0.001 -0.002 0.0005</force>
       </atom>
     </atomset>
     <cputime>123.45</cputime>
     <walltime>456.78</walltime>
   </sample>

Registering the Parser
++++++++++++++++++++++

In ``pyproject.toml``:

.. code-block:: toml

   [project.entry-points."aiida.parsers"]
   "qbox.mymode" = "aiida_qbox.parsers.mymode:MyModeParser"

Testing
+++++++

.. code-block:: python

   def test_myparser():
       from aiida.orm import FolderData
       from aiida_qbox.parsers.mymode import MyModeParser

       folder = FolderData()
       folder.put_object_from_filelike(b'stdout...', 'newmode.out')
       folder.put_object_from_filelike(b'<sample/>', 'newmode.xml')

       parser = MyModeParser(node=orm.CalcJobNode())
       parser.retrieved = folder
       parser.node.get_option = lambda x: 'newmode.out'

       result = parser.parse()
       assert result is None  # Success