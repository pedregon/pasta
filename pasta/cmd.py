"""The `cmd` module is a command line application."""
import logging
import logging.handlers as logging_handlers
import os
import pathlib
import shlex
import sys
import time

import click
import stransi

from .config import Config
from .pty import PseudoTerminal
from .shell import Event
from .version import __version__


def stdin(b: bytes) -> bytes:
    if b == b"EOF":
        return b

    cbreak = b.replace(b"\n", b"\r\n")
    os.write(sys.stdout.fileno(), cbreak)
    # if b"\r\n" in b:
    #     print([d for d in stransi.Ansi(b).escapes()], flush=True)

    return b


def stdout(b: bytes) -> bytes:
    if b == b"EOF":
        return b

    cbreak = b.replace(b"\n", b"\r\n")
    os.write(sys.stdout.fileno(), cbreak)
    return b


def stderr(b: bytes) -> bytes:
    cbreak = b.replace(b"\n", b"\r\n")
    os.write(sys.stderr.fileno(), cbreak)
    return b


def print_version(ctx, param: click.Parameter, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return

    click.echo(__version__)
    ctx.exit()


@click.group(name=__package__, invoke_without_command=True)
@click.option(
    "--version",
    is_flag=True,
    callback=print_version,
    expose_value=False,
    is_eager=True,
    help="print the version",
)
@click.option("--config", "-c", type=str, default=None, help="config file path")
@click.option("--log-dir", type=str, default=None, help="log directory")
@click.option(
    "--log-level",
    type=click.Choice(["info", "debug"], case_sensitive=False),
    default="info",
    help="log level",
)
@click.option("--log-max-size", type=int, default=None, help="max log file size (MB)")
@click.option(
    "--log-backups",
    type=int,
    default=None,
    help="log backup count to retain",
)
@click.pass_context
def root(
    ctx: click.Context,
    config: str | None,
    log_dir: list[str] | None,
    log_level: str,
    log_max_size: int | None,
    log_backups: int | None,
) -> None:
    """Pasta is an interactive shell recorder for red team observability."""
    if config is not None:
        with pathlib.Path(config).open(mode="rb") as handle:
            conf = Config.load(handle)
    else:
        config_path = Config.find()
        if config_path is not None:
            with pathlib.Path(config_path).open(mode="rb") as handle:
                conf = Config.load(handle)
        else:
            conf = Config()

    match log_level.lower():
        case "info":
            conf.logging.level = logging.INFO
        case "debug":
            conf.logging.level = logging.DEBUG

    if log_dir is not None:
        conf.logging.directory = log_dir

    if log_max_size is not None:
        conf.logging.max_size = log_max_size

    if log_backups is not None:
        conf.logging.directory = log_backups

    ctx.obj = conf

    path = pathlib.Path(conf.logging.directory)
    path.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=conf.logging.level,
        format="%(asctime)s : %(name)s : %(levelname)s : %(message)s",
        handlers=[
            logging_handlers.RotatingFileHandler(
                filename=str(path.joinpath(f"{time.time_ns()}.log")),
                maxBytes=conf.logging.max_size * pow(10, 6),
                backupCount=conf.logging.backups,
            )
        ],
    )


@root.command(
    name="wrap",
    context_settings=dict(
        ignore_unknown_options=True,
    ),
)
@click.option("--echo", is_flag=True, help="echo mode")
@click.option(
    "--chdir",
    type=(str, os.PathLike),
    default=None,
    help="working directory",
)
@click.option(
    "--timeout",
    "-t",
    type=float,
    default=1,
    help="time to wait before forcibly exiting the command",
)
@click.argument(
    "args",
    nargs=-1,
    type=click.UNPROCESSED,
)
@click.pass_context
def root_wrap(
    ctx: click.Context,
    echo: bool,
    chdir: str | None,
    timeout: float,
    args: tuple[str],
) -> None:
    """Wrap a command and capture its output."""
    config: Config = ctx.obj
    cmd = shlex.join(args)
    logger = logging.getLogger(name=cmd)
    term = PseudoTerminal(config, logger=logger)
    with term.spool(cmd, cwd=chdir, echo=echo, timeout=timeout) as ts:
        ts.addHandler(Event.STDIN, stdin)
        ts.addHandler(Event.STDOUT, stdout)
        ts.addHandler(Event.STDERR, stderr)
        click.echo(
            click.style(
                "Pasta started, output log directory is '%s'."
                % config.logging.directory,
                fg="red",
                bold=True,
            )
        )

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

    click.echo(click.style("Pasta done.", fg="red", bold=True))


@root.command(name="config")
@click.pass_context
def root_config(
    ctx: click.Context,
) -> None:
    """Print the config."""
    config: Config = ctx.obj
    if len(config.model_fields_set) == 0:
        click.echo(config.dumps(comment=True))
    else:
        click.echo(config.dumps())


def cli() -> None:
    """Command line application entrypoint."""
    root.main()
