"""CLI commands for Qbox data handling."""

import click
from aiida import load_profile
from aiida.orm import SinglefileData, Dict, load_node

from aiida_qbox.workflows.protocols import list_protocols


@click.group()
def data_cmd():
    """Commands for handling Qbox data."""
    pass


@data_cmd.command('parse-xml')
@click.argument('node_pk', type=int)
def parse_xml(node_pk):
    """Parse XML output from a Qbox calculation node.

    NODE_PK: PK of a calculation node with output_xml output
    """
    load_profile()

    try:
        node = load_node(node_pk)
    except Exception as e:
        click.echo(f"Error loading node {node_pk}: {e}")
        return

    if 'output_xml' not in node.outputs:
        click.echo(f"Node {node_pk} does not have output_xml output")
        return

    xml_node = node.outputs.output_xml
    click.echo(f"Parsing XML from {xml_node.filename} (PK={xml_node.pk})")

    try:
        from aiida_qbox.parsers.qbox_output import parse_qbox_xml
        with xml_node.open('r') as f:
            content = f.read()
        parsed = parse_qbox_xml(content)

        for key, value in parsed.items():
            if key != 'forces':  # Print forces separately
                click.echo(f"  {key}: {value}")

        if 'forces' in parsed:
            click.echo("  forces:")
            for atom, force in parsed['forces'].items():
                click.echo(f"    {atom}: {force}")

    except Exception as e:
        click.echo(f"Error parsing XML: {e}")


@data_cmd.command('show-params')
@click.argument('node_pk', type=int)
def show_params(node_pk):
    """Show input parameters of a Qbox calculation node."""
    load_profile()

    try:
        node = load_node(node_pk)
    except Exception as e:
        click.echo(f"Error loading node {node_pk}: {e}")
        return

    if 'parameters' in node.inputs:
        params = node.inputs.parameters.get_dict()
        click.echo("Input parameters:")
        for cmd, args in params.items():
            if args:
                click.echo(f"  {cmd} {args}")
            else:
                click.echo(f"  {cmd}")
    else:
        click.echo("No parameters input found")


@data_cmd.command('show-output')
@click.argument('node_pk', type=int)
def show_output(node_pk):
    """Show output parameters of a Qbox calculation node."""
    load_profile()

    try:
        node = load_node(node_pk)
    except Exception as e:
        click.echo(f"Error loading node {node_pk}: {e}")
        return

    if 'output_parameters' in node.outputs:
        params = node.outputs.output_parameters.get_dict()
        click.echo("Output parameters:")
        for key, value in params.items():
            if isinstance(value, dict):
                click.echo(f"  {key}:")
                for k, v in value.items():
                    click.echo(f"    {k}: {v}")
            elif isinstance(value, list) and len(value) > 10:
                click.echo(f"  {key}: [list with {len(value)} elements]")
            else:
                click.echo(f"  {key}: {value}")
    else:
        click.echo("No output_parameters output found")


@data_cmd.command('show-protocols')
def show_protocols():
    """List available built-in Qbox protocols."""
    for name, desc in list_protocols().items():
        click.echo(f"  {name}: {desc}")