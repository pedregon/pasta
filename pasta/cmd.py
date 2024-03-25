"""The `cmd` module is a command line application."""
import logging
import os
import shlex
import sys
import time

import click
import stransi

from . import pty, shell
from .config import Config
from .version import __version__


def stdin(b: bytes) -> bytes:
    if b == b"EOF":
        return b

    os.write(sys.stdout.fileno(), b)
    # if b"\r\n" in b:
    #     print([d for d in stransi.Ansi(b).escapes()], flush=True)

    return b


def stdout(b: bytes) -> bytes:
    if b == b"EOF":
        return b

    os.write(sys.stdout.fileno(), b)
    return b


def stderr(b: bytes) -> bytes:
    os.write(sys.stderr.fileno(), b)
    return b


def wrap(cmd: str, dedicated_tty: bool, log_level: str) -> None:
    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        filename="/tmp/pasta.log",
    )
    logger = logging.getLogger(name=cmd)
    pasta = pty.Terminal(logger=logger)
    with pasta.spool(
        cmd,
        dedicated_tty=dedicated_tty,
        echo=not dedicated_tty,
    ) as ts:
        ts.addHandler(shell.Event.STDIN, stdin)
        ts.addHandler(shell.Event.STDOUT, stdout)
        ts.addHandler(shell.Event.STDERR, stderr)
        pass

    for action in ts.actions:
        logger.info(
            "Action {} started at {} and executed for {} seconds -->\nPrompt:\n{}\nStdin:\n{}\nStdout:\n{}\nStderr:\n{}\n".format(
                action.id,
                action.time_started.isoformat(),
                action.time_elapsed,
                action.prompt_ps1,
                action.command_input,
                action.command_output,
                action.command_error,
            )
        )


def print_version(ctx, param: click.Parameter, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return

    click.echo(__version__)
    ctx.exit()


@click.command(
    name=__package__,
    context_settings=dict(
        ignore_unknown_options=True,
    ),
)
# @click.option("--config", "-c", type=str | None)
@click.option(
    "--version", is_flag=True, callback=print_version, expose_value=False, is_eager=True
)
@click.option("--tty", is_flag=True)
@click.option(
    "--log-level",
    type=click.Choice(["info", "debug"], case_sensitive=False),
    default="info",
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def root(
    ctx: click.Context, config: str | None, tty: bool, log_level: str, args: tuple[str]
) -> None:
    """A."""
    cmd = shlex.join(args)
    wrap(cmd, tty, log_level)
    # try:
    #     with pasta.spool() as streams:
    #         stdin = streams[0].tokenize()
    #         stdout = streams[1].tokenize()
    #         stderr = streams[2].tokenize()
    #         while True:
    #             time.sleep(1)
    #             try:
    #                 b0 = next(stdin)
    #                 print("stdin", b0, flush=True)
    #             except StopIteration:
    #                 break
    #             try:
    #                 b1 = next(stdout)
    #                 print("stdout", b1, flush=True)
    #             except StopIteration:
    #                 break
    #             # try:
    #             #     b2 = next(stderr)
    #             #     print("stderr", b2, flush=True)
    #             # except StopIteration:
    #             #     break
    # finally:
    #     pasta.close()
    #


def cli() -> None:
    """Command line application entrypoint."""
    root.main()