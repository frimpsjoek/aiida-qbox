"""Utilities for handling parent folder and prefix extraction."""

from aiida import orm


def get_parent_qbox_prefix(parent_calc, parameters: dict) -> str:
    """Extract the Qbox prefix from the parent calculation.

    Qbox uses the prefix for XML output files (e.g., prefix.xml).
    The prefix can be set via 'set prefix' command in parameters,
    or derived from the parent calculation label.

    Args:
        parent_calc: The parent calculation node
        parameters: Input parameters dict

    Returns:
        The prefix string to use for XML files
    """
    # Check if prefix is explicitly set in parameters
    for cmd, args in parameters.items():
        if cmd.lower().startswith('set prefix'):
            return args.strip() if args else 'qbox'

    # Try to get from parent calculation's metadata
    if hasattr(parent_calc, 'get_attribute'):
        prefix = parent_calc.get_attribute('qbox_prefix', None)
        if prefix:
            return prefix

    # Try to extract from parent label
    if hasattr(parent_calc, 'label'):
        # Use parent label as prefix, sanitized
        label = parent_calc.label
        # Remove common suffixes
        for suffix in ['_relax', '_md', '_scf', '_gs', '_relax', '_opt']:
            if label.endswith(suffix):
                label = label[:-len(suffix)]
                break
        return label.replace(' ', '_').replace('/', '_')

    return 'qbox'


def get_parent_save_subdir(parent_calc) -> str:
    """Get the subdirectory within the parent remote folder where the XML file is located.

    For Qbox, the XML file is typically in the working directory ('.'),
    but some workflows might use a subdirectory.

    Args:
        parent_calc: The parent calculation node

    Returns:
        Subdirectory path (relative to remote folder root), or '.' for root
    """
    # Check if parent has a 'save_subdir' attribute
    if hasattr(parent_calc, 'get_attribute'):
        subdir = parent_calc.get_attribute('qbox_save_subdir', None)
        if subdir:
            return subdir

    # Default to current directory
    return '.'