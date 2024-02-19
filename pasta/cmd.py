"""The `cmd` module is a command line application."""
import os
import pty
import select
import shlex
import subprocess
import sys
import termios
import tty

import click


@click.command(
    name=__package__,
    context_settings=dict(
        ignore_unknown_options=True,
    ),
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def root(ctx: click.Context, args: tuple[str]) -> None:
    """A."""
    command = shlex.quote(shlex.join(args))
    click.echo(command)
    restore = termios.tcgetattr(sys.stdin.fileno())
    tty.setraw(sys.stdout.fileno())
    click.echo(os.isatty(sys.stdin.fileno()))
    click.echo(os.read(sys.stdin.fileno(), 1024))
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSAFLUSH, restore)
    # stdin_master_fd, stdin_slave_fd = pty.openpty()
    # combined_master_fd, combined_slave_fd = pty.openpty()
    # try:
    #     proc = subprocess.Popen(
    #         args=shlex.split(command),
    #         stdin=stdin_slave_fd,
    #         stdout=combined_slave_fd,
    #         stderr=combined_slave_fd,
    #     )
    #     while proc.poll() is None:
    #         select.select([master_fd, sys.stdin], [], [])
    # finally:
    #     termios.tcdrain(sys.stdout)


def cli() -> None:
    """Command line application entrypoint."""
    root.main()
