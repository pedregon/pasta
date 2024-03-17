"""The `cmd` module is a command line application."""
import asyncio
import shlex
import time

import click

from . import pty


async def wrap(cmd: str) -> None:
    pasta = pty.Pasta()
    async with pasta.spool(cmd, echo=False) as spooler:
        print("start", flush=True)
        b = await spooler[0].tokenize()
        print(b, flush=True)

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
    asyncio.run(wrap(cmd))
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
