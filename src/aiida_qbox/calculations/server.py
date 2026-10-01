"""CalcJob implementation for Qbox qb executable (server mode).

Qbox server mode runs as a persistent process that accepts commands via
lock-file synchronization and returns XML output. Used for finite-field
WEST coupling where WEST acts as the client.
"""

import os
from aiida import orm
from aiida.common import datastructures
from aiida.engine import CalcJob

from aiida_qbox.utils import get_parent_qbox_prefix, get_parent_save_subdir


def validate_qbox_server_parameters(value, _):
    """Validate Qbox server parameters Dict."""
    if value is None:
        return None
    params = value.get_dict()
    if not isinstance(params, dict):
        return "parameters must be a dictionary"
    return None


class QboxServerCalculation(CalcJob):
    """CalcJob for Qbox qb executable (server mode).

    Runs as a persistent server that communicates via lock files.
    WEST client sends commands, server executes and writes XML output.

    Required inputs:
        - parent_folder: RemoteData from a completed calculation (for initial state)
        - parameters: Dict with initial Qbox commands (run once at startup)
        - server_input_file: Name of the input lock file (default: 'qb_in')
        - server_output_file: Name of the output XML file (default: 'qb_out')

    Outputs:
        - output_parameters: Dict with parsed results from last XML output
        - remote_folder: RemoteData pointing to calculation directory
    """

    _DEFAULT_INPUT_FILE = 'qbox_server.in'
    _DEFAULT_OUTPUT_FILE = 'qbox_server.out'
    _DEFAULT_PARSER = 'qbox.server'

    @classmethod
    def define(cls, spec):
        """Define the process specification."""
        super().define(spec)

        # Input specifications
        spec.input(
            'metadata.options.input_filename',
            valid_type=str,
            default=cls._DEFAULT_INPUT_FILE,
            help='Filename for the Qbox server startup input file.'
        )
        spec.input(
            'metadata.options.output_filename',
            valid_type=str,
            default=cls._DEFAULT_OUTPUT_FILE,
            help='Filename for the Qbox stdout output.'
        )
        spec.input(
            'metadata.options.parser_name',
            valid_type=str,
            default=cls._DEFAULT_PARSER,
            help='Parser to use for output processing.'
        )
        spec.input(
            'metadata.options.withmpi',
            valid_type=bool,
            default=True,
            help='Whether to run with MPI.'
        )

        spec.input(
            'parent_folder',
            valid_type=orm.RemoteData,
            required=True,
            help='Output folder from a completed Qbox calculation for initial state.'
        )
        spec.input(
            'parameters',
            valid_type=orm.Dict,
            required=True,
            validator=validate_qbox_server_parameters,
            help='Initial Qbox commands to run at server startup.'
        )
        spec.input(
            'server_input_file',
            valid_type=orm.Str,
            required=False,
            default=lambda: orm.Str('qb_in'),
            help='Name of the client input file (lock file base).'
        )
        spec.input(
            'server_output_file',
            valid_type=orm.Str,
            required=False,
            default=lambda: orm.Str('qb_out'),
            help='Name of the server output XML file.'
        )
        spec.input(
            'settings',
            valid_type=orm.Dict,
            required=False,
            help='Optional settings for calculation and parser behavior.'
        )

        # Output specifications
        spec.output(
            'output_parameters',
            valid_type=orm.Dict,
            required=True,
            help='Parsed output parameters from the last XML output.'
        )
        spec.output(
            'remote_folder',
            valid_type=orm.RemoteData,
            required=True,
            help='Remote folder containing calculation outputs.'
        )
        spec.default_output_node = 'output_parameters'

        # Exit codes
        spec.exit_code(
            301,
            'ERROR_NO_RETRIEVED_FOLDER',
            message='The retrieved folder could not be accessed.'
        )
        spec.exit_code(
            302,
            'ERROR_OUTPUT_STDOUT_MISSING',
            message='The stdout output file was not found in retrieved folder.'
        )
        spec.exit_code(
            312,
            'ERROR_OUTPUT_STDOUT_INCOMPLETE',
            message='Server terminated unexpectedly (no completion marker).'
        )
        spec.exit_code(
            320,
            'ERROR_OUTPUT_XML_MISSING',
            message='The XML output file was not found.'
        )
        spec.exit_code(
            321,
            'ERROR_OUTPUT_XML_READ',
            message='The XML output file could not be read.'
        )
        spec.exit_code(
            322,
            'ERROR_OUTPUT_XML_PARSE',
            message='The XML output file could not be parsed.'
        )
        spec.exit_code(
            330,
            'ERROR_QBOX',
            message='Qbox stopped with an error: {message}'
        )
        spec.exit_code(
            400,
            'ERROR_OUT_OF_WALLTIME',
            message='The calculation ran out of walltime.'
        )
        spec.exit_code(
            500,
            'ERROR_UNKNOWN',
            message='An unknown error occurred during the calculation.'
        )

    def prepare_for_submission(self, folder):
        """Prepare the calculation for submission."""
        parameters = self.inputs.parameters.get_dict()
        parent_folder = self.inputs.parent_folder
        parent_calc = parent_folder.creator
        qe_prefix = get_parent_qbox_prefix(parent_calc, parameters)

        server_input_file = self.inputs.server_input_file.value
        server_output_file = self.inputs.server_output_file.value

        # Write startup input file
        input_filename = self.metadata.options.input_filename
        with folder.open(input_filename, 'w', encoding='utf-8') as handle:
            self._write_qbox_input(handle, parameters)

        # Setup calculation info
        calcinfo = datastructures.CalcInfo()
        calcinfo.uuid = str(self.uuid)

        # Copy parent XML for initial state
        parent_remote_path = parent_folder.get_remote_path()
        parent_subdir = get_parent_save_subdir(parent_calc)
        xml_source = os.path.join(parent_remote_path, parent_subdir, f'{qe_prefix}.xml')
        xml_dest = f'{qe_prefix}.xml'
        calcinfo.remote_copy_list = [(
            parent_folder.computer.uuid,
            xml_source,
            xml_dest,
        )]

        # Code info: run in server mode with lock file communication
        codeinfo = datastructures.CodeInfo()
        codeinfo.cmdline_params = [
            '-i', input_filename,
            '-s', f'{server_input_file} {server_output_file}'
        ]
        codeinfo.stdout_name = self.metadata.options.output_filename
        codeinfo.code_uuid = self.inputs.code.uuid
        calcinfo.codes_info = [codeinfo]

        # Files to retrieve
        calcinfo.retrieve_list = [
            self.metadata.options.output_filename,
            f'{server_output_file}',
        ]

        settings = self.inputs.get('settings', orm.Dict()).get_dict()
        additional_retrieve = settings.get('additional_retrieve_list', [])
        calcinfo.retrieve_list.extend(additional_retrieve)

        return calcinfo

    def _write_qbox_input(self, handle, parameters: dict):
        """Write Qbox input commands to file."""
        for cmd, args in parameters.items():
            if args is None or args == '':
                handle.write(f'{cmd}\n')
            else:
                handle.write(f'{cmd} {args}\n')