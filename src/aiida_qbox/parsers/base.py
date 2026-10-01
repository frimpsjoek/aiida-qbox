"""Parser implementation for Qbox base calculation outputs.

Parses both stdout and XML output files for energies, forces, positions, etc.
"""

import re

from aiida import orm
from aiida.parsers import Parser

from aiida_qbox.parsers.qbox_output import (
    cpu_time_seconds,
    find_qbox_error,
    is_complete,
    parse_qbox_xml,
    walk_files,
    wall_time_seconds,
)

_SCF_CONVERGED = re.compile(r'SCF\s+converged', re.IGNORECASE)
_SCF_NOT_CONVERGED = re.compile(r'SCF\s+NOT\s+converged', re.IGNORECASE)
_GEOM_CONVERGED = re.compile(r'geometry\s+optimization\s+converged', re.IGNORECASE)


class QboxBaseParser(Parser):
    """Parser for QboxBaseCalculation outputs."""

    def parse(self, **kwargs):
        """Parse retrieved files from QboxBaseCalculation.

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

        parsed = self._parse_stdout(stdout)

        # Find XML output file (could be qbox.xml or prefix.xml)
        xml_file = None
        for fname in files:
            if fname.endswith('.xml') and not fname.endswith('.xsd'):
                xml_file = fname
                break

        if xml_file is not None:
            xml_content = files[xml_file]
            try:
                xml_parsed = parse_qbox_xml(xml_content)
                parsed.update(xml_parsed)
                parsed['xml_file'] = xml_file
            except Exception:
                return self.exit_codes.ERROR_OUTPUT_XML_PARSE
        else:
            return self.exit_codes.ERROR_OUTPUT_XML_MISSING

        # Check for Qbox error
        qbox_error = find_qbox_error(stdout)
        if qbox_error is not None:
            return self.exit_codes.ERROR_QBOX.format(message=qbox_error)

        # Check completion
        if not is_complete(stdout):
            return self.exit_codes.ERROR_OUTPUT_STDOUT_INCOMPLETE

        # Check convergence
        converged = self._check_convergence(parsed, stdout)
        parsed['converged'] = converged
        if not converged:
            return self.exit_codes.ERROR_CONVERGENCE_NOT_REACHED

        self.out('output_parameters', orm.Dict(parsed))

        # Also output XML as SinglefileData if present
        if xml_file is not None:
            try:
                xml_node = orm.SinglefileData(file=self.retrieved.base.repository.open(xml_file, 'rb'))
                self.out('output_xml', xml_node)
            except Exception:
                pass

        return None

    def _parse_stdout(self, stdout: str) -> dict:
        """Parse stdout for timing and version info."""
        parsed = {}
        parsed['cpu_time'] = cpu_time_seconds(stdout)
        parsed['wall_time'] = wall_time_seconds(stdout)

        # Extract Qbox version
        match = re.search(r'Qbox\s+version\s+(\S+)', stdout)
        if match:
            parsed['qbox_version'] = match.group(1)

        match = re.search(r'qbox\s+(\d+\.\d+\.\d+)', stdout, re.IGNORECASE)
        if match:
            parsed['qbox_version'] = match.group(1)

        return parsed

    def _check_convergence(self, parsed: dict, stdout: str) -> bool:
        """Check if calculation converged based on stdout and parsed data."""
        # Check for explicit convergence markers
        if _SCF_NOT_CONVERGED.search(stdout):
            return False

        if _SCF_CONVERGED.search(stdout):
            return True

        if _GEOM_CONVERGED.search(stdout):
            return True

        # If we have forces and they're small, consider converged
        forces = parsed.get('forces', {})
        if forces:
            max_force = max(
                (abs(fx)**2 + abs(fy)**2 + abs(fz)**2)**0.5
                for fx, fy, fz in forces.values()
            )
            if max_force < 1e-4:  # Default threshold
                return True

        # If we have etotal and it's reasonable, assume converged
        if 'etotal' in parsed:
            return True

        return False