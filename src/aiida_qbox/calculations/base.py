"""CalcJob implementation for Qbox qb executable (standard runs).

Qbox performs FPMD and electronic structure calculations with support for
hybrid functionals and finite-field client-server mode for WEST.
"""

import os
from typing import Optional

import yaml
from aiida import orm
from aiida.common import datastructures
from aiida.engine import CalcJob

from aiida_qbox.utils import get_parent_qbox_prefix, get_parent_save_subdir


def validate_qbox_parameters(value, _):
    """Validate Qbox parameters Dict.

    Args:
        value: The Dict node containing parameters
        _: Port (unused)

    Returns:
        Error message string if validation fails, None otherwise
    """
    if value is None:
        return None

    params = value.get_dict()

    # Check for required sections
    # Qbox input is a sequence of commands, not a nested dict structure
    # We just validate it's a valid dict
    if not isinstance(params, dict):
        return "parameters must be a dictionary"

    return None


class QboxBaseCalculation(CalcJob):
    """CalcJob for Qbox qb executable (standard runs).

    Performs FPMD, ground state, or excited state calculations.
    Can also run in client-server mode for finite-field WEST coupling.

    Required inputs:
        - parent_folder: RemoteData from a completed calculation (optional, for restarts)
        - parameters: Dict with Qbox input commands (will be serialized to text format)

    Outputs:
        - output_parameters: Dict with parsed results from XML output
        - remote_folder: RemoteData pointing to calculation directory
        - output_xml: SinglefileData with the XML output file
    """

    _DEFAULT_INPUT_FILE = 'qbox.in'
    _DEFAULT_OUTPUT_FILE = 'qbox.out'
    _DEFAULT_XML_FILE = 'qbox.xml'
    _DEFAULT_PARSER = 'qbox.base'

    @classmethod
    def define(cls, spec):
        """Define the process specification."""
        super().define(spec)

        # Input specifications
        spec.input(
            'metadata.options.input_filename',
            valid_type=str,
            default=cls._DEFAULT_INPUT_FILE,
            help='Filename for the Qbox input file (text format).'
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
            required=False,
            help='Output folder from a completed Qbox calculation for restart.'
        )
        spec.input(
            'parameters',
            valid_type=orm.Dict,
            required=True,
            validator=validate_qbox_parameters,
            help='Qbox input parameters as a sequence of commands. '
                 'Each key is a command name, value is the argument string.'
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
            help='Parsed output parameters including energies, forces, etc.'
        )
        spec.output(
            'remote_folder',
            valid_type=orm.RemoteData,
            required=True,
            help='Remote folder containing calculation outputs.'
        )
        spec.output(
            'output_xml',
            valid_type=orm.SinglefileData,
            required=False,
            help='XML output file with full sample data.'
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
            310,
            'ERROR_OUTPUT_STDOUT_READ',
            message='The stdout output file could not be read.'
        )
        spec.exit_code(
            311,
            'ERROR_OUTPUT_STDOUT_PARSE',
            message='The stdout output file could not be parsed.'
        )
        spec.exit_code(
            312,
            'ERROR_OUTPUT_STDOUT_INCOMPLETE',
            message='stdout has no completion marker: the job was killed '
                    '(walltime, out of memory, node failure).'
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
            410,
            'ERROR_CONVERGENCE_NOT_REACHED',
            message='SCF or geometry optimization did not converge.'
        )
        spec.exit_code(
            500,
            'ERROR_UNKNOWN',
            message='An unknown error occurred during the calculation.'
        )

    def prepare_for_submission(self, folder):
        """Prepare the calculation for submission.

        Creates the text input file and sets up remote symlinks for restarts.

        Args:
            folder: SandboxFolder for staging input files

        Returns:
            CalcInfo object with calculation details
        """
        # Get parameters and prepare for text serialization
        parameters = self.inputs.parameters.get_dict()

        # Get parent calculation info for restart
        qe_prefix = 'qbox'
        if 'parent_folder' in self.inputs:
            parent_folder = self.inputs.parent_folder
            parent_calc = parent_folder.creator
            qe_prefix = get_parent_qbox_prefix(parent_calc, parameters)

        # Write text input file
        input_filename = self.metadata.options.input_filename
        with folder.open(input_filename, 'w', encoding='utf-8') as handle:
            self._write_qbox_input(handle, parameters)

        # Setup calculation info
        calcinfo = datastructures.CalcInfo()
        calcinfo.uuid = str(self.uuid)

        # Handle restart: copy parent XML sample file if restarting
        if 'parent_folder' in self.inputs:
            parent_folder = self.inputs.parent_folder
            parent_remote_path = parent_folder.get_remote_path()
            parent_subdir = get_parent_save_subdir(parent_calc)
            xml_source = os.path.join(parent_remote_path, parent_subdir, f'{qe_prefix}.xml')
            xml_dest = f'{qe_prefix}.xml'
            calcinfo.remote_copy_list = [(
                parent_folder.computer.uuid,
                xml_source,
                xml_dest,
            )]

        # Code info
        codeinfo = datastructures.CodeInfo()
        codeinfo.cmdline_params = ['-i', input_filename]
        codeinfo.stdout_name = self.metadata.options.output_filename
        codeinfo.code_uuid = self.inputs.code.uuid
        calcinfo.codes_info = [codeinfo]

        # Files to retrieve
        calcinfo.retrieve_list = [
            self.metadata.options.output_filename,
            f'{qe_prefix}.xml',
        ]

        # Add additional retrieve files from settings
        settings = self.inputs.get('settings', orm.Dict()).get_dict()
        additional_retrieve = settings.get('additional_retrieve_list', [])
        calcinfo.retrieve_list.extend(additional_retrieve)

        return calcinfo

    def _write_qbox_input(self, handle, parameters: dict):
        """Write Qbox input commands to file.

        Args:
            handle: File handle to write to
            parameters: Dict with Qbox commands as keys and arguments as values
        """
        for cmd, args in parameters.items():
            if args is None or args == '':
                handle.write(f'{cmd}\n')
            else:
                handle.write(f'{cmd} {args}\n')