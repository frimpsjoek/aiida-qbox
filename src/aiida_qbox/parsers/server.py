"""Parser implementation for Qbox server calculation outputs.

Parses the XML output from persistent server mode.
"""

from aiida import orm
from aiida.parsers import Parser

from aiida_qbox.parsers.qbox_output import (
    find_qbox_error,
    is_complete,
    parse_qbox_xml,
    walk_files,
)


class QboxServerParser(Parser):
    """Parser for QboxServerCalculation outputs."""

    def parse(self, **kwargs):
        """Parse retrieved files from QboxServerCalculation.

        Returns:
            ExitCode if parsing fails, None on success
        """
        try:
            files = walk_files(self.retrieved)
        except Exception:
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        output_filename = self.node.get_option('output_filename')
        if output_filename not in files:
            return self.exit_codes.ERROR_OUTPUT_STDOUT_MISSING

        try:
            stdout = files[output_filename]
        except Exception:
            return self.exit_codes.ERROR_OUTPUT_STDOUT_READ

        # Server mode: the main output is the XML file specified by server_output_file
        server_output_file = self.node.inputs.server_output_file.value
        xml_file = None
        for fname in files:
            if fname == server_output_file or fname.endswith('.xml'):
                xml_file = fname
                break

        if xml_file is None:
            return self.exit_codes.ERROR_OUTPUT_XML_MISSING

        try:
            xml_content = files[xml_file]
        except Exception:
            return self.exit_codes.ERROR_OUTPUT_XML_READ

        try:
            parsed = parse_qbox_xml(xml_content)
            parsed['xml_file'] = xml_file
        except Exception:
            return self.exit_codes.ERROR_OUTPUT_XML_PARSE

        # Check for Qbox error in stdout
        qbox_error = find_qbox_error(stdout)
        if qbox_error is not None:
            return self.exit_codes.ERROR_QBOX.format(message=qbox_error)

        # Check completion
        if not is_complete(stdout):
            return self.exit_codes.ERROR_OUTPUT_STDOUT_INCOMPLETE

        self.out('output_parameters', orm.Dict(parsed))
        return None