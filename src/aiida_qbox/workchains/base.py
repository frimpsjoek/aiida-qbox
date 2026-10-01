"""Base WorkChain for Qbox with error handling and restarts.

Provides automated error handling, convergence checking, and
restart capability for Qbox calculations.
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
    QBOX_DEFAULT_MAX_SCF,
    abort,
    find_fatal_marker,
    made_scf_progress,
    next_max_scf,
    scheduler_stderr,
)

QboxBaseCalculation = CalculationFactory('qbox.base')


class QboxBaseWorkChain(BaseRestartWorkChain):
    """WorkChain to run Qbox with automated error handling.

    Features:
        - SCF not converged → restart with max_scf raised by the original budget;
          aborts if an attempt made no SCF progress (never loops)
        - Killed job: out-of-memory marker → abort; otherwise restart, walltime ×2
        - Qbox error → abort with Qbox's message
        - XML retrieve failure → retry once from remote folder
        - Configurable maximum restart attempts
    """

    _process_class = QboxBaseCalculation

    defaults = AttributeDict({
        'max_iterations': 5,
        'delta_factor_max_seconds': 0.95,
    })

    @classmethod
    def define(cls, spec):
        """Define the process specification."""
        super().define(spec)

        # Expose QboxBaseCalculation inputs
        spec.expose_inputs(
            QboxBaseCalculation,
            namespace='qbox',
            exclude=('metadata.options.parser_name',)
        )

        # Additional inputs
        spec.input(
            'clean_workdir',
            valid_type=orm.Bool,
            default=lambda: orm.Bool(False),
            help='Clean working directory after successful completion.'
        )
        spec.input(
            'max_iterations',
            valid_type=orm.Int,
            default=lambda: orm.Int(5),
            help='Maximum number of restart attempts.'
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

        # Expose QboxBaseCalculation outputs
        spec.expose_outputs(QboxBaseCalculation)

        # Exit codes
        spec.exit_code(
            401,
            'ERROR_MAXIMUM_ITERATIONS_EXCEEDED',
            message='Maximum number of iterations exceeded without convergence.'
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
        """Initialize context variables.

        ``super().setup()`` (from BaseRestartWorkChain) already initializes
        ``self.ctx.iteration = 0`` and ``self.ctx.is_finished = False`` and sets
        ``self.ctx.process_name``. We layer Qbox-specific state on top.
        """
        super().setup()
        self.ctx.max_iterations = self.inputs.max_iterations.value
        self.ctx.restart_from_checkpoint = False
        self.ctx.inputs = AttributeDict(self.exposed_inputs(QboxBaseCalculation, 'qbox'))
        params = self.ctx.inputs.parameters.get_dict()

        # Extract max_scf from parameters if present
        self.ctx.max_scf_budget = QBOX_DEFAULT_MAX_SCF
        for cmd, args in params.items():
            if 'max_scf' in cmd.lower():
                try:
                    self.ctx.max_scf_budget = int(args)
                    break
                except (ValueError, TypeError):
                    pass

        self.ctx.last_scf_iter = None

    def validate_inputs(self):
        """Validate that parent folder is suitable if provided."""
        parent_folder = self.ctx.inputs.get('parent_folder', None)

        if parent_folder is not None:
            if not isinstance(parent_folder, orm.RemoteData):
                return self.exit_codes.ERROR_PARENT_FOLDER_INVALID

            self.report(f'Parent folder: {parent_folder.get_remote_path()}')

        return None

    def prepare_process(self):
        """Mutate inputs in place before the parent's ``run_process`` submits.

        Do NOT increment ``self.ctx.iteration`` here — the parent's
        ``run_process`` is the only place that owns that counter.
        """
        if self.ctx.restart_from_checkpoint:
            params = self.ctx.inputs.parameters.get_dict()
            # Update max_scf for restart
            new_max_scf = next_max_scf(self.ctx.last_scf_iter, self.ctx.max_scf_budget)
            for cmd, args in params.items():
                if 'max_scf' in cmd.lower():
                    params[cmd] = str(new_max_scf)
                    break
            else:
                # Add max_scf if not present
                params['set max_scf'] = str(new_max_scf)

            self.report(f"Restarting SCF (max_scf={new_max_scf})")
            self.ctx.inputs.parameters = orm.Dict(params)

            # For restart, use the remote folder from the failed calculation
            # The XML file will be copied by the calculation's prepare_for_submission
            self.ctx.restart_from_checkpoint = False

    def _restart_if_progress(self, calculation, reason: str):
        """Restart from ``calculation``'s state, or abort if it made no progress."""
        params = calculation.outputs.output_parameters.get_dict() if 'output_parameters' in calculation.outputs else {}
        scf_iter = params.get('scf_iter') or params.get('n_scf')

        if not made_scf_progress(self.ctx.last_scf_iter, scf_iter):
            return abort(self, f'{reason}, and no SCF progress (scf_iter={scf_iter}, previous='
                               f'{self.ctx.last_scf_iter}): a restart cannot help. Check stdout and '
                               f'_scheduler-stderr.txt of {calculation.process_label}<{calculation.pk}>.')

        self.ctx.last_scf_iter = scf_iter
        self.ctx.inputs.parent_folder = calculation.outputs.remote_folder
        self.ctx.restart_from_checkpoint = True
        self.report(f'{reason} at scf_iter={scf_iter}: restarting from saved state')
        return ProcessHandlerReport(do_break=True)

    @process_handler(priority=600, exit_codes=[
        QboxBaseCalculation.exit_codes.ERROR_OUTPUT_STDOUT_INCOMPLETE,
        QboxBaseCalculation.exit_codes.ERROR_OUT_OF_WALLTIME,
    ])
    def handle_killed(self, calculation):
        """Job killed before completion: out of memory → abort; otherwise (walltime) restart, walltime ×2."""
        marker = find_fatal_marker(scheduler_stderr(calculation))
        if marker is not None:
            return abort(self, f'Job killed with "{marker}" in _scheduler-stderr.txt: needs more memory per MPI '
                               'rank (more nodes or fewer ranks per node). Resource change left to the user.')

        options = self.ctx.inputs.metadata.options
        if options.get('max_wallclock_seconds'):
            options['max_wallclock_seconds'] = int(options['max_wallclock_seconds'] * 2)

        return self._restart_if_progress(calculation, 'Killed before completion (walltime?)')

    @process_handler(priority=500, exit_codes=[QboxBaseCalculation.exit_codes.ERROR_CONVERGENCE_NOT_REACHED])
    def handle_convergence_failure(self, calculation):
        """SCF or geometry optimization hit max iterations without converging: restart with raised cap."""
        return self._restart_if_progress(calculation, 'SCF/geometry optimization not converged')

    @process_handler(priority=590, exit_codes=[QboxBaseCalculation.exit_codes.ERROR_QBOX])
    def handle_qbox_error(self, calculation):
        """Qbox error (bad input, missing file, environment): rerunning the same input cannot help."""
        return abort(self, f'Qbox error in {calculation.process_label}<{calculation.pk}>: {calculation.exit_message}')

    @process_handler(
        priority=550,
        exit_codes=[
            QboxBaseCalculation.exit_codes.ERROR_OUTPUT_XML_MISSING,
            QboxBaseCalculation.exit_codes.ERROR_OUTPUT_XML_READ,
            QboxBaseCalculation.exit_codes.ERROR_OUTPUT_XML_PARSE,
            QboxBaseCalculation.exit_codes.ERROR_OUTPUT_STDOUT_MISSING,
        ],
    )
    def handle_retrieve_failure(self, calculation):
        """Retry once when a file we expected to retrieve is missing/corrupt.

        Covers transient filesystem races (slow NFS, scheduler-killed retrieve)
        where the Qbox calc actually finished but the XML / stdout did not
        make it back to the AiiDA repository. We re-run from the remote folder.
        """
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

    # ``results`` and ``should_run_process`` are inherited from BaseRestartWorkChain.