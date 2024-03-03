"""The `cmd` module is a command line application."""
import os
import pathlib
import pty
import select
import selectors
import shlex
import subprocess
import sys
import termios
import tty

import click


def _copy(master_fd: int):
    if os.get_blocking(master_fd):
        # If we write more than tty/ndisc is willing to buffer, we may block
        # indefinitely. So we set master_fd to non-blocking temporarily during
        # the copy operation.
        os.set_blocking(master_fd, False)
        try:
            _copy(master_fd, master_read=master_read, stdin_read=stdin_read)
        finally:
            # restore blocking mode for backwards compatibility
            os.set_blocking(master_fd, True)
        return
    high_waterlevel = 4096
    stdin_avail = master_fd != STDIN_FILENO
    stdout_avail = master_fd != STDOUT_FILENO
    i_buf = b''
    o_buf = b''

    pass


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
    try:
        command = shlex.quote(shlex.join(args))
        click.echo(command)
        stdout_fd = sys.stdin.fileno()
        if not os.isatty(stdout_fd):
            raise click.ClickException("Not a tty")

        mode = termios.tcgetattr(stdout_fd)
        try:
            tty.setraw(sys.stdout.fileno())
            restore = True
        except termios.error:
            restore = False

        sel = selectors.DefaultSelector()
        try:
            master_fd, slave_fd = pty.openpty()
            proc = subprocess.Popen(
                args,
                stdin=slave_fd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=4096,
                env=os.environ,
                close_fds=True,
            )
            sel.register(stdout_fd, selectors.EVENT_READ)
            sel.register(proc.stdout.fileno(), selectors.EVENT_READ)  # pyright: ignore[reportOptionalMemberAccess]
            sel.register(proc.stderr.fileno(), selectors.EVENT_READ)  # pyright: ignore[reportOptionalMemberAccess]
            with pathlib.Path().open(mode="w") as stdout_handle, pathlib.Path().open(mode="w") as stderr_handle: 
                while proc.poll() is None:
                    events = sel.select(timeout=1)
                    for key, mask in events:
                        if mask & selectors.EVENT_WRITE:
                            break
                        if mask & selectors.EVENT_READ:
                            data = os.read(key.fd, 1024)
                            if not data:
                                sel.unregister(key.fd)
                            else:
                                if

            os.close(master_fd)
        finally:
            sel.close()
            if restore:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSAFLUSH, mode)
        #     termios.tcdrain(sys.stdout)
    except KeyboardInterrupt:
        return


def cli() -> None:
    """Command line application entrypoint."""
    root.main()