#!/usr/bin/env python3

import os
import socket
import sys

import click
import tabulate
from click_repl import repl, ExitReplException
from prompt_toolkit.output import ColorDepth
from prompt_toolkit.shortcuts import CompleteStyle

from fosdemosc import *
from fosdemosc import helpers
from fosdemosc import presets

osc: OSCController


class AliasedGroup(click.Group):
    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        matches = [x for x in self.list_commands(ctx)
                   if x.startswith(cmd_name)]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        ctx.fail(f"Too many matches: {', '.join(sorted(matches))}")

    def resolve_command(self, ctx, args):
        # always return the full command name
        _, cmd, args = super().resolve_command(ctx, args)
        return cmd.name, cmd, args

def preset_choices():
    return [x for x in presets.keys()]


@click.command(invoke_without_command=True, cls=AliasedGroup)
@click.option('--device', '-d', type=click.File('wb'), default='/dev/tty_fosdem_audio_ctl',
              help='Override the serial port on which the mixer is attached')
@click.pass_context
def cli(ctx: click.Context, device: click.File):
    prompt_kwargs = {
        'message': 'mixer@%s> ' % socket.gethostname(),
        'color_depth': ColorDepth.MONOCHROME,
        'complete_style': CompleteStyle.READLINE_LIKE
    }

    try:
        global osc
        if not 'osc' in globals():
            osc = OSCController(device.name)
    except OSError as e:
        click.echo(f'Cannot connect to device: {e}', err=True)
        sys.exit(e.errno)

    if ctx.invoked_subcommand is None:
        @cli.command(hidden=True)
        def quit():
            raise ExitReplException()

        @cli.command(hidden=True)
        def exit():
            raise ExitReplException()

        @cli.command(name='?', hidden=True)
        def question():
            click.echo(ctx.get_help())

        ctx.invoke(info)
        repl(click.get_current_context(), prompt_kwargs=prompt_kwargs)


@cli.command(help='Show all gains in human-readable format')
def matrix():
    head = ['#'] + osc.outputs

    formatted = [
        [osc.inputs[i], *line]
        for i, line in enumerate(osc.get_matrix())
    ]

    click.echo(tabulate.tabulate(formatted, headers=head, floatfmt=".2f", tablefmt='simple_grid'))

@cli.command(help='Show input/output aaudio levels')
def vu():
    head = ['#', 'rms', 'peak', 'smooth']
    channel_data = [[ch, levels.rms, levels.peak, levels.smooth] for ch, levels in osc.get_channel_vu_meters().items()]
    bus_data = [[bus, levels.rms, levels.peak, levels.smooth] for bus, levels in osc.get_bus_vu_meters().items()]
    click.echo(tabulate.tabulate(channel_data, headers=head, floatfmt=".2f", tablefmt='simple_grid'))
    click.echo(tabulate.tabulate(bus_data, headers=head, floatfmt=".2f", tablefmt='simple_grid'))

@cli.command(help='List channel names')
def channels():
    click.echo('\t'.join(osc.inputs))


@cli.command(help='List bus names')
def buses():
    click.echo('\t'.join(osc.outputs))


@cli.command(name='list', help='List channels and buses')
def list_channels_buses():
    click.echo('Inputs/Outputs:')
    header = ['#', *range(max(len(osc.inputs), len(osc.outputs)))]
    click.echo(tabulate.tabulate([
        ['Channel', *osc.inputs],
        ['Bus', *osc.outputs]
    ], headers=header, tablefmt='simple_grid'))

    click.echo('Presets:')
    header = ['#', *range(len(presets))]
    click.echo(tabulate.tabulate([['Preset', *presets.keys()]], headers=header, tablefmt='simple_grid'))


@cli.command()
def info():
    click.echo('-' * 80)
    click.echo('FOSDEM Audio Control @%s' % socket.gethostname())
    click.echo('Connected to device %s' % osc.device)
    click.echo('-' * 80)


@cli.command(help='Get the gain for a specified channel')
@click.argument('channel')
@click.argument('bus')
def get_gain(channel: int | str, bus: int | str):
    try:
        channel = helpers.parse_channel(osc, channel)
        bus = helpers.parse_bus(osc, bus)

        click.echo(osc.get_gain(channel, bus))
    except ValueError as e:
        click.echo(f'Invalid input: {e}', err=True)


@cli.command(help='Set the gain for a specified channel')
@click.argument('channel')
@click.argument('bus')
@click.argument('level', type=float)
def set_gain(channel: int | str, bus : int | str, level: float | str):
    try:
        channel = helpers.parse_channel(osc, channel)
        bus = helpers.parse_bus(osc, bus)
        level = helpers.parse_level(osc, level)

        osc.set_gain(channel, bus, level)
    except ValueError as e:
        click.echo(f'Invalid input: {e}', err=True)


@cli.command(help='Apply preset')
@click.argument('preset', type=click.Choice(preset_choices()))
@click.help_option()
def preset(preset: str):
    if preset not in presets:
        click.echo('Preset not found', err=True)
    else:
        for i in range(0, len(osc.inputs)):
            for j in range(0, len(osc.outputs)):
                osc.set_gain(i, j, presets[preset][i][j])


@cli.command()
def cls():
    click.clear()


@cli.command('help')
@click.pass_context
def print_help(ctx: click.Context):
    click.echo(ctx.parent.get_help())


if __name__ == '__main__':
    cli()
