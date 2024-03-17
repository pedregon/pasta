"""Pty code."""
from __future__ import annotations

import contextlib
import errno
import fcntl
import logging
import os
import pty
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
from collections import abc

from . import multiplexor, shell


class Terminal:
    """Terminal is a subprocess pseudo terminal.

    Attributes
    ----------
    logger
        Optional logger for events.
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger

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
    def _set_echo(fd: int, value: bool, logger: logging.Logger | None = None) -> None:
        """Set a terminal file descriptor to or form echo mode.

        Echo mode echoes input keystrokes back to the output.

        Parameters
        ----------
        fd
            Terminal file descriptor.
        value
            If to set echo mode on or off.
        logger
            Optional logger.

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

        if logger is not None:
            logger.debug("Echo mode %d: %s", fd, "on" if value else "off")

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
    def _set_term_winsize(
        fd: int,
        rows: int,
        cols: int,
        logger: logging.Logger | None = None,
    ) -> None:
        """Set the terminal window size.

        Parameters
        ----------
        fd
            Terminal file descriptor.
        rows
            Terminal cell row count.
        cols
            Terminal cell column count.
        logger
            Optional logger.
        """
        if logger is not None:
            logger.debug("Resizing %d: %dx%d", fd, cols, rows)

        TIOCSWINSZ = getattr(termios, "TIOCSWINSZ", -2146929561)
        s = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, TIOCSWINSZ, s)

    @classmethod
    def _resize_term_factory(
        cls,
        parent_fd: int,
        child_fd: int,
        logger: logging.Logger | None = None,
    ) -> signal._HANDLER:
        """Return a SIGNWINCH signal handler that resizes terminal windows.

        Parameters
        ----------
        parent_fd
            A parent terminal file descriptor.
        child_fd
            A child terminal file descriptor.
        logger
            Optional logger.

        Returns
        -------
        Signal handler callback.
        """

        def handleSignal(signalNumber: int, _: types.FrameType | None) -> None:
            """Handle a SIGNWINCH signal."""
            if signalNumber != signal.SIGWINCH:
                return

            rows, cols = cls._get_term_winsize(parent_fd)
            cls._set_term_winsize(child_fd, rows, cols, logger=logger)

        return handleSignal

    @contextlib.contextmanager
    def spool(
        self,
        cmd: str,
        env: dict[str, str] | None = os.environ.copy(),
        cwd: os.PathLike | None = None,
        timeout: float | None = 1,
        echo: bool = True,
        bufsize: int = 8192,
        waterlevel: int = 4096,
        readsize: int = 1024,
    ) -> abc.Generator[shell.Typescript, None, None]:
        """Spool spools child process IO to buffers for the parent process to control.

        The "capture" implementation is focused on shell streams and therefore is
        desgined to enable continuous interaction.

        The parent process terminal is put into raw mode, creating a "pass-through" for
        standard input keystrokes to be forwarded to a ptm. A ptm is the "master" file
        descriptor in a pseudo terminal pair, it forwards data to its cable, pts. The
        ptm is used by the parent process. The pts or "slave" is a terminal for use as
        the standard input of the child process.

        In most pty implementations, the ptm is used as the standard output and standard
        error file descriptors of the child process. However, to differentiate the
        standard output from standard error, distinct in-memory pipes are used. A pty
        is bidirectional such that data may be written or read from either ptm or pts
        end. The ptm is still read from in our case to capture echoed keystrokes. If the
        pts is in echo mode, then any data written to the "pass-through" will be echoed
        back to the ptm much like one would expect in a cooked mode terminal.

        Typescripts are leveraged as callbacks to intercept the child process standard
        input, standard output, and standard error streams respectively.

        This method is a context manager such that the child process lifecycle may be
        safely managed during streaming.

        Parameters
        ----------
        cmd
            Command to execute in the child process.
        env
            Environment variables for the child process. Defaults to inherit from the
            parent process.
        cwd
            Working directory to execute the child process in.
        timeout
            Time to wait before forcibly closing the child process when streaming ends.
        echo
            Set echo mode for the pts (capture child process standard input?).
        bufsize
            Buffer size for the child process standard output and standard error file
            descriptors.
        waterlevel
            Number of bytes to buffer in the parent process before needing to write to
            streams and reset the buffer.
        readsize
            Number of bytes to read from file descriptors at a time.

        Returns
        -------
        A terminal manager for controlling the parent process despite giving terminal
        control to the child process.

        Raises
        ------
        ValueError
            If the parent process standard input is not a TTY.
        """
        # split the command into argv
        args = shlex.split(cmd)

        # ensure executable path
        if exe := shutil.which(args[0]):
            args[0] = exe

        # get the standard input file descriptor
        stdin_fd = sys.stdin.fileno()
        if self.logger is not None:
            self.logger.debug("File descriptor parent terminal: %d", stdin_fd)

        if not os.isatty(stdin_fd):
            raise ValueError("Standard input is not a tty.")

        # create an audit log
        sys.audit("pasta.pty")

        # create a pseudo-terminal (terminal, cable)
        ptm, pts = pty.openpty()
        if self.logger is not None:
            self.logger.debug("File descriptor ptm: %d", ptm)
            self.logger.debug("File descriptor pts: %d", pts)

        # set standard input terminal to raw mode
        mode = termios.tcgetattr(stdin_fd)
        try:
            tty.setraw(stdin_fd)
            if self.logger is not None:
                self.logger.debug("Set parent terminal to raw mode")

            # set the pty slave to echo mode
            if echo != self._get_echo(pts):
                try:
                    self._set_echo(pts, echo, logger=self.logger)
                except (IOError, termios.error) as err:
                    if err.args[0] not in (errno.EINVAL, errno.ENOTTY):
                        raise

            restore = True
        except termios.error:
            restore = False

        proc = None
        blocking = False
        try:
            # start a child process
            if self.logger is not None:
                self.logger.debug("Executing child process: %s", shlex.join(args))
                if cwd is not None:
                    self.logger.debug(
                        "Using working directory for child process: %s", cwd
                    )

            proc = subprocess.Popen(
                args[:],
                env=env,
                cwd=cwd,
                # stdin=subprocess.PIPE,
                stdin=pts,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=bufsize,
            )

            if self.logger is not None:
                # if proc.stdin is not None:
                #     self.logger.debug(
                #         "File descriptor child input: %d", proc.stdin.fileno()
                #     )

                if proc.stdout is not None:
                    self.logger.debug(
                        "File descriptor child output: %d", proc.stdout.fileno()
                    )

                if proc.stderr is not None:
                    self.logger.debug(
                        "File descriptor child error: %d", proc.stderr.fileno()
                    )

            # set the initial terminal size
            rows, cols = self._get_term_winsize(stdin_fd)
            self._set_term_winsize(pts, rows, cols)

            # register the terminal resize signal handler
            signal.signal(
                signal.SIGWINCH,
                self._resize_term_factory(
                    stdin_fd,
                    pts,
                    logger=self.logger,
                ),
            )

            # return proxied buffers for read-only
            ts = shell.Typescript()
            yield ts

            buf_i = b""
            buf_p = b""
            buf_o = b""
            buf_e = b""

            blocking = os.get_blocking(ptm)
            if blocking:
                if self.logger is not None:
                    self.logger.debug("Unblocking file descriptor: %d", ptm)

                os.set_blocking(ptm, False)

            while proc.poll() is None:
                rfds: list[int] = []
                wfds: list[int] = []

                # add standard input to readers if buffer not above waterlevel
                if len(buf_i) < waterlevel:
                    rfds.append(stdin_fd)

                # add ptm to readers if buffer not above waterlevel
                if len(buf_p) < waterlevel:
                    rfds.append(ptm)

                # always add subprocess standard output if it is being captured
                if proc.stdout is not None:
                    rfds.append(proc.stdout.fileno())

                # always add subprocess standard error if it is being captured
                if proc.stderr is not None:
                    rfds.append(proc.stderr.fileno())

                # add ptm to writers if buffer has data
                if len(buf_i) > 0:
                    wfds.append(ptm)

                rfds, wfds, _ = select.select(rfds, wfds, [])

                # read standard input and store data in buffer
                if stdin_fd in rfds:
                    if self.logger is not None:
                        self.logger.debug("Reading from file descriptor: %d", stdin_fd)

                    try:
                        data = os.read(stdin_fd, readsize)
                        buf_i += data
                    except OSError:
                        pass

                # read ptm, intercept, and copy to buffer (should be echoed pts only)
                if ptm in rfds:
                    if self.logger is not None:
                        self.logger.debug("Reading from file descriptor: %d", stdin_fd)

                    try:
                        data = os.read(ptm, readsize)
                    except OSError:
                        data = b""

                    if data:
                        data = ts.wrap(shell.Event.STDIN, data)
                        buf_p += data

                # read child process standard output, intercept, and copy to buffer
                if (
                    proc.stdout is not None
                    and (stdout_fd := proc.stdout.fileno()) in rfds
                ):
                    if self.logger is not None:
                        self.logger.debug("Reading from file descriptor: %d", stdout_fd)

                    try:
                        data = os.read(stdout_fd, readsize)
                    except OSError:
                        data = b""

                    if data:
                        data = ts.wrap(shell.Event.STDOUT, data)
                        buf_o += data

                # read child process standard error, intercept, and copy to buffer
                if (
                    proc.stderr is not None
                    and (stderr_fd := proc.stderr.fileno()) in rfds
                ):
                    if self.logger is not None:
                        self.logger.debug("Reading from file descriptor: %d", stderr_fd)

                    try:
                        data = os.read(stderr_fd, readsize)
                    except OSError:
                        data = b""

                    if data:
                        data = ts.wrap(shell.Event.STDERR, data)
                        buf_e += data

                # copy buffer to ptm ("pass-through" parent standard input to child pts)
                if ptm in wfds:
                    if self.logger is not None:
                        self.logger.debug("Writing to file descriptor: %d", ptm)

                    n = os.write(ptm, buf_i)
                    buf_i = buf_i[n:]

        finally:
            # exit the child process
            if proc is not None:
                try:
                    exit_code = proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    exit_code = proc.poll()

                if self.logger is not None:
                    self.logger.debug("Exited child process: %d", exit_code or 0)

            if blocking:
                if self.logger is not None:
                    self.logger.debug("Blocking file descriptor: %d", ptm)

                os.set_blocking(ptm, True)

            os.close(pts)
            os.close(ptm)

            # restore the standard input terminal
            if restore:
                termios.tcsetattr(stdin_fd, termios.TCSAFLUSH, mode)
                if self.logger is not None:
                    self.logger.debug("Restored parent terminal")
