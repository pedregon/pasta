"""Pty code."""
from __future__ import annotations

import asyncio
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

import pydantic

from . import shell


class AsyncDeque:
    def __init__(self, maxlen: int | None = None):
        self._deque = deque[bytes](maxlen=maxlen)
        self._lock = asyncio.Lock()

    async def append(self, item):
        async with self._lock:
            self._deque.append(item)

    async def appendleft(self, item):
        async with self._lock:
            self._deque.appendleft(item)

    async def pop(self):
        async with self._lock:
            return self._deque.pop()

    async def popleft(self):
        async with self._lock:
            return self._deque.popleft()

    async def peek(self):
        async with self._lock:
            return self._deque[-1]

    async def peekleft(self):
        async with self._lock:
            return self._deque[0]

    def __len__(self):
        return len(self._deque)


class Spooler(t.NamedTuple):
    """."""

    stdin: shell.Typescript
    stdout: shell.Typescript
    stderr: shell.Typescript


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

    @staticmethod
    def _get_echo(fd: int) -> bool:
        """Check if the terminal is in echo mode.

        Echo mode echoes input keystrokes back to the output.

        Parameters
        ----------
        fd
            Terminal file descriptor.

        Returns
        -------
        Truthful.

        Raises
        ------
        IOError
            If the file descriptor is not a supported terminal.
        """
        try:
            attr = termios.tcgetattr(fd)
        except termios.error as err:
            if err.args[0] == errno.EINVAL:
                raise IOError(
                    err.args[0],
                    f"{err.args[1]}: Unable to get terminal echo: '{sys.platform}'",
                )
            raise

        return bool(attr[3] & termios.ECHO)

    @staticmethod
    def _set_echo(fd: int, value: bool) -> None:
        """Set a terminal file descriptor to or form echo mode.

        Echo mode echoes input keystrokes back to the output.

        Parameters
        ----------
        fd
            Terminal file descriptor.
        value
            If to set echo mode on or off.

        Raises
        ------
        IOError
            If the file descriptor is not a supported terminal.
        """
        errmsg = "echo mode is settable on this platform"

        try:
            attr = termios.tcgetattr(fd)
        except termios.error as err:
            if err.args[0] == errno.EINVAL:
                raise IOError(err.args[0], "%s: %s." % (err.args[1], errmsg))
            raise

        if value:
            attr[3] = attr[3] | termios.ECHO
        else:
            attr[3] = attr[3] & ~termios.ECHO

        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, attr)
        except IOError as err:
            if err.args[0] == errno.EINVAL:
                raise IOError(err.args[0], "%s: %s." % (err.args[1], errmsg))
            raise

    @staticmethod
    def _get_term_winsize(fd: int) -> tuple[t.Any, ...]:
        """Get the terminal window size.

        Parameters
        ----------
        fd
            Terminal file descriptor.

        Returns
        -------
        rows
            Terminal cell row count.
        cols
            Terminal cell column count.
        """
        TIOCGWINSZ = getattr(termios, "TIOCGWINSZ", 1074295912)
        s = struct.pack("HHHH", 0, 0, 0, 0)
        x = fcntl.ioctl(fd, TIOCGWINSZ, s)
        return struct.unpack("HHHH", x)[0:2]

    @staticmethod
    def _set_term_winsize(fd: int, rows: int, cols: int) -> None:
        """Set the terminal window size.

        Parameters
        ----------
        fd
            Terminal file descriptor.
        rows
            Terminal cell row count.
        cols
            Terminal cell column count.
        """
        TIOCSWINSZ = getattr(termios, "TIOCSWINSZ", -2146929561)
        s = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, TIOCSWINSZ, s)

    @classmethod
    def _resize_term_factory(cls, parent_fd: int, child_fd: int) -> signal._HANDLER:
        """Return a SIGNWINCH signal handler that resizes terminal windows.

        Parameters
        ----------
        parent_fd
            A parent terminal file descriptor.
        child_fd
            A child terminal file descriptor.

        Returns
        -------
        Signal handler callback.
        """

        def handleSignal(signalNumber: int, _: types.FrameType | None) -> None:
            """Handle a SIGNWINCH signal."""
            if signalNumber != signal.SIGWINCH:
                return

            rows, cols = cls._get_term_winsize(parent_fd)
            cls._set_term_winsize(child_fd, rows, cols)

        return handleSignal

    async def _copy(self, spooler: AsyncDeque) -> t.AsyncGenerator[bytes, None]:
        # while :
        try:
            b = await spooler.pop()
            yield b
        except IndexError:
            pass

    @contextlib.asynccontextmanager
    async def spool(
        self,
        cmd: str,
        env: dict[str, str] = os.environ.copy(),
        echo: bool = True,
        histsize: int = 1000,
        bufsize: int = 4096,
        readsize: int = 1024,
    ) -> t.AsyncGenerator[Spooler, None]:
        """Capture captures Actions.

        Return
        ------
        A generator of Actions.
        """
        # split the command into argv
        args = shlex.split(cmd)

        # ensure executable path
        if exe := shutil.which(args[0]):
            args[0] = exe

        # get the standard input file descriptor
        stdin_fd = sys.stdin.fileno()

        if not os.isatty(stdin_fd):
            raise ValueError("Standard input is not a tty.")

        # create an audit log
        sys.audit("pasta.pty")

        # create a pseudo-terminal (terminal, cable)
        ptm, pts = pty.openpty()

        # set standard input terminal to raw mode
        mode = termios.tcgetattr(stdin_fd)
        try:
            tty.setraw(stdin_fd)

            # set the pty slave to echo mode
            # try:
            #     self._set_echo(pts, echo)
            # except (IOError, termios.error) as err:
            #     if err.args[0] not in (errno.EINVAL, errno.ENOTTY):
            #         raise

            restore = True
        except termios.error:
            restore = False

        proc = None

        try:
            # start a child process
            proc = subprocess.Popen(
                args[:],
                env=env,
                stdin=pts,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=bufsize,
            )

            # set the initial terminal size
            rows, cols = self._get_term_winsize(stdin_fd)
            self._set_term_winsize(pts, rows, cols)

            # register the terminal resize signal handler
            signal.signal(signal.SIGWINCH, self._resize_term_factory(stdin_fd, pts))

            # initialize ring buffer queues for write-only
            stdin = AsyncDeque(maxlen=histsize)
            stdout = AsyncDeque(maxlen=histsize)
            stderr = AsyncDeque(maxlen=histsize)

            # return proxied buffers for read-only
            yield Spooler(
                stdin=shell.Typescript(self._copy(stdin)),
                stdout=shell.Typescript(self._copy(stdout)),
                stderr=shell.Typescript(self._copy(stderr)),
            )

            buf_i = b""
            buf_o = b""
            buf_e = b""
            while proc.poll() is None:
                rfds: list[int] = []
                wfds: list[int] = []

                # add standard input to readers if buffer not above waterline
                if len(buf_i) < bufsize:
                    rfds.append(stdin_fd)

                # always add subprocess standard output if it is being captured
                if proc.stdout is not None:
                    rfds.append(proc.stdout.fileno())

                # always add subprocess standard error if it is being captured
                if proc.stderr is not None:
                    rfds.append(proc.stderr.fileno())

                # add ptm to writers if buffer has data
                if len(buf_i) > 0:
                    wfds.append(ptm)

                buf_o = b""
                buf_i = b""
                rfds, wfds, _ = select.select(rfds, wfds, [])

                # read standard input and store data in buffer
                if stdin in rfds:
                    print("reading from stdin", flush=True)
                    try:
                        data = os.read(stdin_fd, readsize)
                    except OSError:
                        data = b""

                    if data:
                        buf_i += data

                # copy buffer to ptm and a deque
                if ptm in wfds:
                    print("writing to ptm", flush=True)
                    n = os.write(ptm, buf_i)
                    buf_i = buf_i[n:]
                    await stdin.append(buf_i)

                # copy subproces standard output to a deque
                if proc.stdout is not None and proc.stdout in rfds:
                    print("reading from stdout", flush=True)
                    try:
                        data = os.read(self.proc.stdout.fileno(), readsize)  # type: ignore[reportOptionalMemberAccess]
                        buf_o += data
                        await stdout.append(data)
                    except OSError:
                        pass

                # copy subprocess standard error to a deque
                if proc.stderr is not None and proc.stderr in rfds:
                    print("reading from stderr", flush=True)
                    try:
                        data = os.read(self.proc.stderr.fileno(), readsize)  # type: ignore[reportOptionalMemberAccess]
                        buf_e += data
                        await stderr.append(data)
                    except OSError:
                        pass

                # detect EOF from what would be ptm
                if len(buf_o) == 0 and len(buf_e) == 0:
                    print("eof", flush=True)
                    self.closed = True
                    break

        finally:
            # restore the standard input terminal
            if restore:
                termios.tcsetattr(stdin_fd, termios.TCSAFLUSH, mode)

            # replace with send EOF to ptm
            if proc is not None:
                proc.terminate()

            os.close(pts)
            os.close(ptm)

    # def kill(self) -> None:
    #     """Kill sends SIGKILL to the child process."""
    #     self.proc.kill()
    #
    # def wait(self, timeout: float | None = None) -> int:
    #     """Wait for the child process to terminate.
    #
    #     Parameters
    #     ----------
    #     timeout
    #         Time to wait before forced termination.
    #
    #     Return
    #     ------
    #     Child process exit code.
    #     """
    #     return self.proc.wait(timeout)
    #
    # def close(
    #     self,
    #     timeout: float | None = None,
    #     force: bool = False,
    # ) -> t.Optional[int]:
    #     """Close.
    #
    #     Return
    #     ------
    #     Process exit code.
    #     """
    #     if self.closed:
    #         return self.proc.poll()
    #
    #     try:
    #         if force:
    #             self.kill()
    #             exit_code = self.proc.poll()
    #         else:
    #             exit_code = self.wait(timeout)
    #         self.closed = True
    #     finally:
    #         self.reset()
    #         os.close(self.pts)
    #         os.close(self.ptm)
    #
    #     return exit_code

    # def __enter__(self) -> None:
    #     return None
    #
    # @t.overload
    # def __exit__(self, exc_type: None, exc_val: None, exc_tb: None) -> None:
    #     ...
    #
    # @t.overload
    # def __exit__(
    #     self,
    #     exc_type: type[BaseException],
    #     exc_val: BaseException,
    #     exc_tb: types.TracebackType,
    # ) -> None:
    #     ...
    #
    # def __exit__(
    #     self,
    #     exc_type: type[BaseException] | None,
    #     exc_val: BaseException | None,
    #     exc_tb: types.TracebackType | None,
    # ) -> None:
    #     pass
