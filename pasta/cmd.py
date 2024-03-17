"""The `cmd` module is a command line application."""
import asyncio
import logging
import shlex
import time

import click

from . import pty, shell


def wrap(cmd: str) -> None:
    logger = logging.getLogger(name="pasta")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    pasta = pty.Pasta(logger=logger)
    stdin = shell.Typescript()
    stdout = shell.Typescript()
    stderr = shell.Typescript()
    with pasta.spool(
        cmd,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
    ) as term:
        print("start", flush=True)

    print(stdin.buffer, flush=True)
    print(stderr.buffer, flush=True)
    print(stdout.buffer, flush=True)

    print("end", flush=True)


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
    cmd = shlex.join(args)
    wrap(cmd)
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