=======================
Adding WorkChains
=======================

All Qbox workchains follow the same pattern using ``BaseRestartWorkChain``.

Template
+++++++++

.. code-block:: python

   # aiida_qbox/workchains/newmode.py
   from aiida import orm
   from aiida.common import AttributeDict
   from aiida.engine import (
       BaseRestartWorkChain,
       ProcessHandlerReport,
       process_handler,
       while_,
   )
   from aiida.plugins import CalculationFactory

   from aiida_qbox.workchains.recovery import (
       QBOX_DEFAULT_MAX_SCF,
       abort,
       find_fatal_marker,
       made_scf_progress,
       next_max_scf,
       scheduler_stderr,
   )

   MyCalculation = CalculationFactory('qbox.mymode')


   class MyModeWorkChain(BaseRestartWorkChain):
       _process_class = MyCalculation

       defaults = AttributeDict({
           'max_iterations': 5,
           'delta_factor_max_seconds': 0.95,
       })

       @classmethod
       def define(cls, spec):
           super().define(spec)

           # Expose calculation inputs
           spec.expose_inputs(
               MyCalculation,
               namespace='qbox',
               exclude=('metadata.options.parser_name',)
           )

           # Workchain-specific inputs
           spec.input(
               'clean_workdir',
               valid_type=orm.Bool,
               default=lambda: orm.Bool(False),
           )
           spec.input(
               'max_iterations',
               valid_type=orm.Int,
               default=lambda: orm.Int(5),
           )

           # Outline
           spec.outline(
               cls.setup,
               cls.validate_inputs,
               while_(cls.should_run_process)(
                   cls.prepare_process,
                   cls.run_process,
                   cls.inspect_process,
               ),
               cls.results,
           )

           # Expose calculation outputs
           spec.expose_outputs(MyCalculation)

           # Workchain-level exit codes
           spec.exit_code(401, 'ERROR_MAXIMUM_ITERATIONS_EXCEEDED', ...)
           spec.exit_code(402, 'ERROR_PARENT_FOLDER_INVALID', ...)
           spec.exit_code(403, 'ERROR_UNRECOVERABLE_FAILURE', ...)

       def setup(self):
           super().setup()
           self.ctx.max_iterations = self.inputs.max_iterations.value
           self.ctx.restart_from_checkpoint = False
           self.ctx.inputs = AttributeDict(self.exposed_inputs(MyCalculation, 'qbox'))

           # Budget for restarts
           params = self.ctx.inputs.parameters.get_dict()
           self.ctx.max_scf_budget = QBOX_DEFAULT_MAX_SCF
           for cmd, args in params.items():
               if 'max_scf' in cmd.lower():
                   self.ctx.max_scf_budget = int(args)
                   break

           self.ctx.last_scf_iter = None

       def validate_inputs(self):
           parent = self.ctx.inputs.get('parent_folder')
           if parent is not None and not isinstance(parent, orm.RemoteData):
               return self.exit_codes.ERROR_PARENT_FOLDER_INVALID
           return None

       def prepare_process(self):
           if self.ctx.restart_from_checkpoint:
               params = self.ctx.inputs.parameters.get_dict()
               new_max = next_max_scf(self.ctx.last_scf_iter, self.ctx.max_scf_budget)
               for cmd, args in params.items():
                   if 'max_scf' in cmd.lower():
                       params[cmd] = str(new_max)
                       break
               else:
                   params['set max_scf'] = str(new_max)
               self.ctx.inputs.parameters = orm.Dict(params)
               self.ctx.restart_from_checkpoint = False

       def _restart_if_progress(self, calculation, reason):
           params = calculation.outputs.output_parameters.get_dict() if 'output_parameters' in calculation.outputs else {}
           scf_iter = params.get('scf_iter') or params.get('n_scf')

           if not made_scf_progress(self.ctx.last_scf_iter, scf_iter):
               return abort(self, f'{reason}, no SCF progress (scf_iter={scf_iter}, prev={self.ctx.last_scf_iter})')

           self.ctx.last_scf_iter = scf_iter
           self.ctx.inputs.parent_folder = calculation.outputs.remote_folder
           self.ctx.restart_from_checkpoint = True
           self.report(f'{reason} at scf_iter={scf_iter}: restarting')
           return ProcessHandlerReport(do_break=True)

       @process_handler(priority=600, exit_codes=[
           MyCalculation.exit_codes.ERROR_OUTPUT_STDOUT_INCOMPLETE,
           MyCalculation.exit_codes.ERROR_OUT_OF_WALLTIME,
       ])
       def handle_killed(self, calculation):
           marker = find_fatal_marker(scheduler_stderr(calculation))
           if marker:
               return abort(self, f'Killed with "{marker}": needs more memory')

           opts = self.ctx.inputs.metadata.options
           if opts.get('max_wallclock_seconds'):
               opts['max_wallclock_seconds'] = int(opts['max_wallclock_seconds'] * 2)
           return self._restart_if_progress(calculation, 'Killed (walltime?)')

       @process_handler(priority=500, exit_codes=[MyCalculation.exit_codes.ERROR_CONVERGENCE_NOT_REACHED])
       def handle_convergence_failure(self, calculation):
           return self._restart_if_progress(calculation, 'Not converged')

       @process_handler(priority=590, exit_codes=[MyCalculation.exit_codes.ERROR_QBOX])
       def handle_qbox_error(self, calculation):
           return abort(self, f'Qbox error: {calculation.exit_message}')

       @process_handler(priority=550, exit_codes=[
           MyCalculation.exit_codes.ERROR_OUTPUT_XML_MISSING,
           MyCalculation.exit_codes.ERROR_OUTPUT_XML_READ,
           MyCalculation.exit_codes.ERROR_OUTPUT_XML_PARSE,
           MyCalculation.exit_codes.ERROR_OUTPUT_STDOUT_MISSING,
       ])
       def handle_retrieve_failure(self, calculation):
           seen = self.ctx.get('retrieve_retry_count', 0)
           if seen >= 1:
               return abort(self, 'Retrieve failure persists after retry')
           self.ctx.retrieve_retry_count = seen + 1

           if 'remote_folder' not in calculation.outputs:
               return abort(self, 'No remote_folder to retry from')

           self.report('Retrieve failure; retrying once')
           self.ctx.inputs.parent_folder = calculation.outputs.remote_folder
           self.ctx.restart_from_checkpoint = True
           return ProcessHandlerReport(True)

       def results(self):
           super().results()
           # Optional: add workchain-specific final checks
           return None

Register Entry Point
++++++++++++++++++++

In ``pyproject.toml``:

.. code-block:: toml

   [project.entry-points."aiida.workflows"]
   "qbox.newmode" = "aiida_qbox.workchains.newmode:MyModeWorkChain"