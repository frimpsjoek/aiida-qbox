"""WorkChain for Qbox server mode with error handling.

Runs Qbox in persistent server mode for client-server coupling with WEST
or other codes. Handles server lifecycle and error recovery.
"""

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
    abort,
    find_fatal_marker,
    scheduler_stderr,
)

QboxServerCalculation = CalculationFactory('qbox.server')


class QboxServerWorkChain(BaseRestartWorkChain):
    """WorkChain to run Qbox server with automated error handling.

    Features:
        - Runs Qbox in persistent server mode with lock-file communication
        - Server crashes: out-of-memory marker → abort; otherwise restart
        - Qbox error → abort with Qbox's message
        - XML retrieve failure → retry once from remote folder
        - Configurable maximum restart attempts
        - Server runs until explicitly stopped (via quit command from client)
    """

    _process_class = QboxServerCalculation

    defaults = AttributeDict({
        'max_iterations': 3,
        'delta_factor_max_seconds': 0.95,
    })

    @classmethod
    def define(cls, spec):
        """Define the process specification."""
        super().define(spec)

        # Expose QboxServerCalculation inputs
        spec.expose_inputs(
            QboxServerCalculation,
            namespace='qbox',
            exclude=('metadata.options.parser_name',)
        )

        # Server-specific inputs
        spec.input(
            'clean_workdir',
            valid_type=orm.Bool,
            default=lambda: orm.Bool(False),
            help='Clean working directory after successful completion.'
        )
        spec.input(
            'max_iterations',
            valid_type=orm.Int,
            default=lambda: orm.Int(3),
            help='Maximum number of restart attempts (server restarts).'
        )
        spec.input(
            'max_walltime_factor',
            valid_type=orm.Float,
            default=lambda: orm.Float(1.5),
            help='Factor to multiply walltime on each restart.'
        )

        # Workflow outline
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

        # Expose QboxServerCalculation outputs
        spec.expose_outputs(QboxServerCalculation)

        # Exit codes
        spec.exit_code(
            401,
            'ERROR_MAXIMUM_ITERATIONS_EXCEEDED',
            message='Maximum number of server restarts exceeded.'
        )
        spec.exit_code(
            402,
            'ERROR_PARENT_FOLDER_INVALID',
            message='Parent folder is invalid or missing required files.'
        )
        spec.exit_code(
            403,
            'ERROR_UNRECOVERABLE_FAILURE',
            message='A handler found a failure that a restart cannot fix (see the workchain report).'
        )

    def setup(self):
        """Initialize context variables."""
        super().setup()
        self.ctx.max_iterations = self.inputs.max_iterations.value
        self.ctx.restart_from_checkpoint = False
        self.ctx.inputs = AttributeDict(self.exposed_inputs(QboxServerCalculation, 'qbox'))
        self.ctx.max_walltime_factor = self.inputs.max_walltime_factor.value

    def validate_inputs(self):
        """Validate that parent folder is provided."""
        parent_folder = self.ctx.inputs.get('parent_folder', None)

        if parent_folder is None:
            return self.exit_codes.ERROR_PARENT_FOLDER_INVALID

        if not isinstance(parent_folder, orm.RemoteData):
            return self.exit_codes.ERROR_PARENT_FOLDER_INVALID

        self.report(f'Parent folder: {parent_folder.get_remote_path()}')
        return None

    def prepare_process(self):
        """Mutate inputs in place before the parent's ``run_process`` submits."""
        if self.ctx.restart_from_checkpoint:
            # For server restart, just reuse the same inputs
            # The XML state will be copied from the parent folder
            self.report('Restarting Qbox server from previous state')
            self.ctx.restart_from_checkpoint = False

    def _restart_server(self, calculation, reason: str):
        """Restart server from ``calculation``'s state."""
        if 'remote_folder' not in calculation.outputs:
            return abort(self, f'{reason}: no remote_folder to restart from.')

        self.ctx.inputs.parent_folder = calculation.outputs.remote_folder
        self.ctx.restart_from_checkpoint = True
        self.report(f'{reason}: restarting server from saved state')
        return ProcessHandlerReport(do_break=True)

    @process_handler(priority=600, exit_codes=[
        QboxServerCalculation.exit_codes.ERROR_OUTPUT_STDOUT_INCOMPLETE,
        QboxServerCalculation.exit_codes.ERROR_OUT_OF_WALLTIME,
    ])
    def handle_killed(self, calculation):
        """Server killed: out of memory → abort; otherwise restart with increased walltime."""
        marker = find_fatal_marker(scheduler_stderr(calculation))
        if marker is not None:
            return abort(self, f'Server killed with "{marker}" in _scheduler-stderr.txt: needs more memory.')

        options = self.ctx.inputs.metadata.options
        if options.get('max_wallclock_seconds'):
            new_walltime = int(options['max_wallclock_seconds'] * self.ctx.max_walltime_factor)
            options['max_wallclock_seconds'] = new_walltime
            self.report(f'Increased walltime to {new_walltime}s for server restart')

        return self._restart_server(calculation, 'Server killed (walltime?)')

    @process_handler(priority=590, exit_codes=[QboxServerCalculation.exit_codes.ERROR_QBOX])
    def handle_qbox_error(self, calculation):
        """Qbox error: rerunning the same input cannot help."""
        return abort(self, f'Qbox server error in {calculation.process_label}<{calculation.pk}>: {calculation.exit_message}')

    @process_handler(
        priority=550,
        exit_codes=[
            QboxServerCalculation.exit_codes.ERROR_OUTPUT_XML_MISSING,
            QboxServerCalculation.exit_codes.ERROR_OUTPUT_XML_READ,
            QboxServerCalculation.exit_codes.ERROR_OUTPUT_XML_PARSE,
            QboxServerCalculation.exit_codes.ERROR_OUTPUT_STDOUT_MISSING,
        ],
    )
    def handle_retrieve_failure(self, calculation):
        """Retry once when a file we expected to retrieve is missing/corrupt."""
        seen = self.ctx.get('retrieve_retry_count', 0)
        if seen >= 1:
            return abort(self, 'Retrieve failure persists after one retry; aborting')
        self.ctx.retrieve_retry_count = seen + 1

        if 'remote_folder' not in calculation.outputs:
            return abort(self, 'No remote_folder on failed calc; cannot retry retrieve')

        self.report(
            f'Retrieve failure (exit {calculation.exit_status}); retrying once '
            'against existing remote_folder'
        )
        self.ctx.inputs.parent_folder = calculation.outputs.remote_folder
        self.ctx.restart_from_checkpoint = True
        return ProcessHandlerReport(True)

    def results(self):
        """Finalize."""
        super().results()
        return None