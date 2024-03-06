"""Pty code."""
from __future__ import annotations

import contextlib
import errno
import fcntl
import os
import pty
import queue
import select
import shlex
import shutil
import signal
import struct
import subprocess
import sys
import termios
import tty
import types
import typing as t
from collections import deque

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
        cmd: str,
        env: dict[str, str] = os.environ.copy(),
        echo: bool = True,
        bufsize: int = 4096,
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

            # set the pty slave to echo mode
            # if not echo:
            #     try:
            #         self._set_echo(False)
            #     except (IOError, termios.error) as err:
            #         if err.args[0] not in (errno.EINVAL, errno.ENOTTY):
            #             raise
            #
            restore = True
        except termios.error:
            restore = False

        # define a standard input terminal reset callback
        def reset() -> None:
            if restore:
                termios.tcsetattr(self.stdin_fd, termios.TCSAFLUSH, mode)

        self.reset = reset

        # start the child process
        self.proc = subprocess.Popen(
            args,
            env=env,
            stdin=self.slave_fd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=bufsize,
        )

        # set the initial terminal size
        rows, cols = self._get_terminal_window_size()
        self._set_terminal_window_size(rows, cols)

        # register the terminal resize signal handler
        signal.signal(signal.SIGWINCH, self._resize_terminal_factory())

    def _get_echo(self) -> bool:
        """A."""
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

    def _set_echo(self, value: bool) -> None:
        """A."""
        errmsg = "setecho() may not be called on this platform (it may still be possible to enable/disable echo when spawning the child process)"

        try:
            attr = termios.tcgetattr(self.stdin_fd)
        except termios.error as err:
            if err.args[0] == errno.EINVAL:
                raise IOError(err.args[0], "%s: %s." % (err.args[1], errmsg))
            raise

        if value:
            attr[3] = attr[3] | termios.ECHO
        else:
            attr[3] = attr[3] & ~termios.ECHO

        try:
            termios.tcsetattr(self.stdin_fd, termios.TCSADRAIN, attr)
        except IOError as err:
            if err.args[0] == errno.EINVAL:
                raise IOError(err.args[0], "%s: %s." % (err.args[1], errmsg))
            raise

    def _get_terminal_window_size(self) -> tuple[t.Any, ...]:
        TIOCGWINSZ = getattr(termios, "TIOCGWINSZ", 1074295912)
        s = struct.pack("HHHH", 0, 0, 0, 0)
        x = fcntl.ioctl(self.stdin_fd, TIOCGWINSZ, s)
        return struct.unpack("HHHH", x)[0:2]

    def _set_terminal_window_size(self, rows: int, cols: int) -> None:
        TIOCSWINSZ = getattr(termios, "TIOCSWINSZ", -2146929561)
        s = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(self.slave_fd, TIOCSWINSZ, s)

    def _resize_terminal_factory(self) -> signal._HANDLER:
        def handleSignal(signalNumber: int, _: types.FrameType | None) -> None:
            """Handle a SIGNWINCH signal."""
            if signalNumber != signal.SIGWINCH:
                return

            rows, cols = self._get_terminal_window_size()
            self._set_terminal_window_size(rows, cols)

        return handleSignal

    @contextlib.contextmanager
    def spool(
        self,
        histsize: int = 1000,
        bufsize: int = 4096,
        readsize: int = 1024,
    ) -> t.Generator[
        tuple[shell.Typescript, shell.Typescript, shell.Typescript],
        None,
        None,
    ]:
        """Capture captures Actions.

        Return
        ------
        A generator of Actions.
        """
        os.set_blocking(self.master_fd, False)
        if self.proc.stdout is not None:
            os.set_blocking(self.proc.stdout.fileno(), False)
        if self.proc.stderr is not None:
            os.set_blocking(self.proc.stderr.fileno(), False)

        stdin = deque[bytes](maxlen=histsize)
        stdout = deque[bytes](maxlen=histsize)
        stderr = deque[bytes](maxlen=histsize)
        yield (
            shell.Typescript(stdin),
            shell.Typescript(stdout),
            shell.Typescript(stderr),
        )
        buf = b""
        try:
            while self.proc.poll() is None:
                rfds = []
                wfds = []
                # add standard input to readers if buffer not above waterline
                if len(buf) < bufsize:
                    rfds.append(self.stdin_fd)

                # always add subprocess standard output if it is being captured
                if self.proc.stdout is not None:
                    rfds.append(self.proc.stdout.fileno())

                # always add subprocess standard error if it is being captured
                if self.proc.stderr is not None:
                    rfds.append(self.proc.stderr.fileno())

                # add ptm to writers if buffer has data
                if len(buf) > 0:
                    wfds.append(self.master_fd)

                rfds, wfds, _ = select.select(rfds, wfds, [])

                # read standard input and store data in buffer
                if self.stdin_fd in rfds:
                    try:
                        data = os.read(self.stdin_fd, readsize)
                    except OSError:
                        data = b""

                    if data:
                        buf += data

                # copy buffer to ptm and a deque
                if self.master_fd in wfds:
                    n = os.write(self.master_fd, buf)
                    stdin.append(buf)
                    buf = buf[n:]

                # copy subproces standard output to a deque
                if self.proc.stdout is not None and self.proc.stdout in rfds:
                    try:
                        data = os.read(self.proc.stdout.fileno(), readsize)  # type: ignore[reportOptionalMemberAccess]
                        stdout.append(data)
                    except OSError:
                        pass

                # copy subprocess standard error to a deque
                if self.proc.stderr is not None and self.proc.stderr in rfds:
                    try:
                        data = os.read(self.proc.stderr.fileno(), readsize)  # type: ignore[reportOptionalMemberAccess]
                        stderr.append(data)
                    except OSError:
                        pass

                # detect EOF from the ptm
                if self.master_fd in rfds:
                    try:
                        data = os.read(self.master_fd, readsize)
                    except OSError:
                        data = b""

                    if not data:
                        break
        finally:
            # replace with send EOF to ptm
            self.wait()

    def kill(self) -> None:
        """Kill sends SIGKILL to the child process."""
        self.proc.kill()

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

    def close(
        self,
        timeout: float | None = None,
        force: bool = False,
    ) -> t.Optional[int]:
        """Close.

        Return
        ------
        Process exit code.
        """
        if self.closed:
            return self.proc.poll()

        try:
            if force:
                self.kill()
                exit_code = self.proc.poll()
            else:
                exit_code = self.wait(timeout)
            self.closed = True
        finally:
            self.reset()
            os.close(self.slave_fd)
            os.close(self.master_fd)

        return exit_code
