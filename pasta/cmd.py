"""The `cmd` module is a command line application."""
import logging
import os
import shlex
import sys

import click
import stransi

from . import pty, shell


def stdin(b: bytes) -> bytes:
    os.write(sys.stdout.fileno(), b)
    # if b"\r\n" in b:
    #     print([d for d in stransi.Ansi(b).escapes()], flush=True)

    return b


def stdout(b: bytes) -> bytes:
    os.write(sys.stdout.fileno(), b)
    return b


def stderr(b: bytes) -> bytes:
    os.write(sys.stderr.fileno(), b)
    return b


def wrap(cmd: str, dedicated_tty: bool) -> None:
    logger = logging.getLogger(name="pasta")
    logger.setLevel(logging.DEBUG)
    # logger.addHandler(logging.StreamHandler())
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
        print("Action %s:" % action.id, flush=True)
        print("Started at %s:" % action.time_started.isoformat(), flush=True)
        print("Time taken %f:" % action.time_elapsed, flush=True)
        print("Prompt:", flush=True)
        print(action.prompt_ps1, flush=True)
        print("Stdin:", flush=True)
        print(action.command_input, flush=True)
        print("Stdout:", flush=True)
        print(action.command_output, flush=True)
        print("Stderr:", flush=True)
        print(action.command_error, flush=True)
        print("Typescript:", flush=True)
        os.write(sys.stdout.fileno(), action.typescript)
        print(flush=True)


@click.command(
    name=__package__,
    context_settings=dict(
        ignore_unknown_options=True,
    ),
)
@click.option("--tty", is_flag=True)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def root(ctx: click.Context, tty: bool, args: tuple[str]) -> None:
    """A."""
    cmd = shlex.join(args)
    wrap(cmd, tty)
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