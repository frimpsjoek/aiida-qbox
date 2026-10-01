"""Shared XML parsing utilities for Qbox outputs.

Provides functions to parse Qbox XML output files (sample.xml) and stdout
for convergence, timing, and error detection.
"""

import re
import xml.etree.ElementTree as ET
from typing import Optional

from lxml import etree

# Namespace for Qbox XML
QBOX_NS = {'fpmd': 'http://www.quantum-simulation.org/ns/fpmd/fpmd-1.0'}


def cpu_time_seconds(stdout: str, prefix: str = '') -> Optional[float]:
    """Extract CPU time from Qbox stdout.

    Qbox prints timing like:
    <cputime>123.456</cputime>
    or in stdout: "cpu time: 123.456 s"

    Args:
        stdout: The stdout text
        prefix: Optional prefix for the timing label

    Returns:
        CPU time in seconds, or None if not found
    """
    # Try XML-style tag first
    match = re.search(r'<cputime>([\d.]+)</cputime>', stdout)
    if match:
        return float(match.group(1))

    # Try stdout text format
    patterns = [
        rf'{prefix}\s*cpu time:\s*([\d.]+)\s*s',
        r'cpu time:\s*([\d.]+)\s*s',
        r'CPU time\s*:\s*([\d.]+)\s*s',
    ]
    for pattern in patterns:
        match = re.search(pattern, stdout, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def wall_time_seconds(stdout: str, prefix: str = '') -> Optional[float]:
    """Extract wall time from Qbox stdout."""
    match = re.search(r'<walltime>([\d.]+)</walltime>', stdout)
    if match:
        return float(match.group(1))

    patterns = [
        rf'{prefix}\s*wall time:\s*([\d.]+)\s*s',
        r'wall time:\s*([\d.]+)\s*s',
        r'Wall time\s*:\s*([\d.]+)\s*s',
    ]
    for pattern in patterns:
        match = re.search(pattern, stdout, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def find_qbox_error(stdout: str) -> Optional[str]:
    """Find Qbox error message in stdout.

    Qbox errors appear as:
    - "ERROR: ..."
    - "<error>...</error>" in XML
    - "qbox: error: ..."

    Args:
        stdout: The stdout text

    Returns:
        Error message string, or None if no error found
    """
    # Check for ERROR: pattern
    match = re.search(r'ERROR:\s*(.+)', stdout)
    if match:
        return match.group(1).strip()

    # Check for qbox: error:
    match = re.search(r'qbox:\s*error:\s*(.+)', stdout, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Check for XML error tag
    match = re.search(r'<error>(.+?)</error>', stdout, re.DOTALL)
    if match:
        return match.group(1).strip()

    return None


def is_complete(stdout: str) -> bool:
    """Check if Qbox stdout indicates successful completion.

    Qbox prints completion markers like:
    - "<status>completed</status>"
    - "JOB DONE" (if it uses that)
    - Normal exit without error

    Args:
        stdout: The stdout text

    Returns:
        True if job appears to have completed successfully
    """
    # Check for explicit completion marker
    if re.search(r'<status>completed</status>', stdout):
        return True

    # Check for successful run completion
    if re.search(r'run\s+\d+\s+\d+\s*completed', stdout, re.IGNORECASE):
        return True

    # If no error and has timing info, likely completed
    if find_qbox_error(stdout) is None and cpu_time_seconds(stdout) is not None:
        return True

    return False


def parse_qbox_xml(xml_content: str) -> dict:
    """Parse Qbox XML output and extract key quantities.

    Args:
        xml_content: XML string content

    Returns:
        Dictionary with parsed quantities
    """
    parsed = {}

    try:
        root = etree.fromstring(xml_content.encode('utf-8'))
    except etree.XMLSyntaxError:
        # Try with standard ElementTree as fallback
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            return {'xml_parse_error': 'Failed to parse XML'}

    # Extract etotal
    etotal_elem = root.find('.//fpmd:etotal', QBOX_NS)
    if etotal_elem is not None and etotal_elem.text:
        try:
            parsed['etotal'] = float(etotal_elem.text.strip())
        except ValueError:
            pass

    # Extract forces
    forces = {}
    for atom in root.findall('.//fpmd:atom', QBOX_NS):
        name = atom.get('name')
        force_elem = atom.find('fpmd:force', QBOX_NS)
        if force_elem is not None and force_elem.text:
            try:
                force_vals = list(map(float, force_elem.text.strip().split()))
                if len(force_vals) == 3:
                    forces[name] = force_vals
            except ValueError:
                pass
    if forces:
        parsed['forces'] = forces

    # Extract positions
    positions = {}
    for atom in root.findall('.//fpmd:atom', QBOX_NS):
        name = atom.get('name')
        pos_elem = atom.find('fpmd:position', QBOX_NS)
        if pos_elem is not None and pos_elem.text:
            try:
                pos_vals = list(map(float, pos_elem.text.strip().split()))
                if len(pos_vals) == 3:
                    positions[name] = pos_vals
            except ValueError:
                pass
    if positions:
        parsed['positions'] = positions

    # Extract cell
    cell_elem = root.find('.//fpmd:unit_cell', QBOX_NS)
    if cell_elem is not None:
        a = cell_elem.get('a')
        b = cell_elem.get('b')
        c = cell_elem.get('c')
        if a and b and c:
            try:
                parsed['cell'] = [
                    list(map(float, a.split())),
                    list(map(float, b.split())),
                    list(map(float, c.split())),
                ]
            except ValueError:
                pass

    # Extract eigenvalues if present
    eigenvalues = []
    for sd in root.findall('.//fpmd:slater_determinant', QBOX_NS):
        for gf in sd.findall('fpmd:grid_function', QBOX_NS):
            # Check if this is an eigenvalue grid function
            pass  # Eigenvalues are typically in density_matrix

    # Extract stress tensor
    stress_elem = root.find('.//fpmd:stress', QBOX_NS)
    if stress_elem is not None and stress_elem.text:
        try:
            stress_vals = list(map(float, stress_elem.text.strip().split()))
            if len(stress_vals) == 6:
                parsed['stress'] = stress_vals
        except ValueError:
            pass

    # Extract CPU/wall time from XML
    cpu_elem = root.find('.//fpmd:cputime', QBOX_NS)
    if cpu_elem is not None and cpu_elem.text:
        try:
            parsed['cpu_time'] = float(cpu_elem.text.strip())
        except ValueError:
            pass

    wall_elem = root.find('.//fpmd:walltime', QBOX_NS)
    if wall_elem is not None and wall_elem.text:
        try:
            parsed['wall_time'] = float(wall_elem.text.strip())
        except ValueError:
            pass

    return parsed


def walk_files(retrieved_folder) -> dict:
    """Walk the retrieved folder and return a dict of filename -> content.

    Args:
        retrieved_folder: AiiDA FolderData node

    Returns:
        Dict mapping relative paths to file contents
    """
    files = {}
    for path in retrieved_folder.base.repository.list_object_names():
        try:
            with retrieved_folder.base.repository.open(path, 'r') as handle:
                files[path] = handle.read()
        except (OSError, UnicodeDecodeError):
            # Skip binary files
            pass
    return files