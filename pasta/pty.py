"""Pty code."""
from __future__ import annotations

import errno
import os
import pty
import shlex
import shutil
import subprocess
import sys
import termios
import tty
import typing as t

from . import shell


class Pasta:
    """Pasta is a pty.

    Attributes
    ----------
    linesep
        Cooked mode terminal line separator.
    crlf
        Terminal carriage return and line feed.
    """

    closed: bool = False

    def __init__(
        self,
        cmd: str = "",
        env: dict[str, str] = os.environ.copy(),
        echo: bool = True,
    ) -> None:
        """Start wrapping."""
        # split the command into argv
        args = shlex.split(cmd)

        # ensure executable path
        if exe := shutil.which(args[0]):
            args[0] = exe

        # get the standard input file descriptor
        self.stdin_fd = sys.stdin.fileno()

        if not os.isatty(self.stdin_fd):
            raise ValueError("Standard input is not a tty.")

        # create an audit log
        sys.audit("pasta.pty")

        # create a pseudo-terminal (terminal, cable)
        self.master_fd, self.slave_fd = pty.openpty()

        # set standard input terminal to raw mode
        mode = termios.tcgetattr(self.stdin_fd)
        try:
            tty.setraw(self.stdin_fd)
            self.echo = echo
            restore = True
        except termios.error:
            restore = False

        # define a standard input terminal reset callback
        def reset() -> None:
            if restore:
                termios.tcsetattr(self.stdin_fd, termios.TCSAFLUSH, mode)

        self.reset = reset

        self.proc = subprocess.Popen(
            args,
            env=env,
            stdin=self.slave_fd,
        )

    def get_echo(self) -> bool:
        try:
            attr = termios.tcgetattr(self.stdin_fd)
        except termios.error as err:
            if err.args[0] == errno.EINVAL:
                raise IOError(
                    err.args[0],
                    f"{err.args[1]}: Unable to set terminal echo: '{sys.platform}'",
                )
            raise

        return bool(attr[3] & termios.ECHO)

    def set_echo(self, value: bool) -> bool:
        errmsg = "setecho() may not be called on this platform (it may still be possible to enable/disable echo when spawning the child process)"

        try:
            attr = termios.tcgetattr(self.master_fd)
        except termios.error as err:
            if err.args[0] == errno.EINVAL:
                raise IOError(err.args[0], "%s: %s." % (err.args[1], errmsg))
            raise

        if value:
            attr[3] = attr[3] | termios.ECHO
        else:
            attr[3] = attr[3] & ~termios.ECHO

        try:
            # I tried TCSADRAIN and TCSAFLUSH, but these were inconsistent and
            # blocked on some platforms. TCSADRAIN would probably be ideal.
            termios.tcsetattr(self.master_fd, termios.TCSANOW, attr)
        except IOError as err:
            if err.args[0] == errno.EINVAL:
                raise IOError(err.args[0], "%s: %s." % (err.args[1], errmsg))
            raise

    def spool(self, cmd: str) -> shell.Typescript:
        """Capture captures Actions.

        Return
        ------
        A generator of Actions.
        """
        return shell.Typescript()

    def kill(self) -> None:
        """Kill sends SIGKILL to the child process."""
        return self.proc.kill()

    def wait(self, timeout: float | None = None) -> int:
        """Wait for the child process to terminate.

        Parameters
        ----------
        timeout
            Time to wait before forced termination.

        Return
        ------
        Child process exit code.
        """
        return self.proc.wait(timeout)

    def close(self) -> t.Optional[int]:
        """Close.

        Return
        ------
        Process exit code.
        """
        if self.closed:
            return self.proc.poll()

        try:
            exit_code = self.wait()
            self.closed = True
        finally:
            self.reset()
            os.close(self.slave_fd)
            os.close(self.master_fd)

        return exit_code