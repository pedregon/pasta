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

from . import errors, shell
from .config import Config


class PseudoTerminal:
    """PseudoTerminal is a subprocess-based pty.

    Attributes
    ----------
    logger
        Optional logger for events.
    """

    def __init__(self, config: Config, logger: logging.Logger | None = None) -> None:
        self.config = config
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
            logger.debug("Echo mode {}: {}".format(fd, "on" if value else "off"))

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
            logger.debug("Resizing {}: {}x{}".format(fd, cols, rows))

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
        env: dict[str, str] | None = None,
        cwd: os.PathLike | str | None = None,
        echo: bool = True,
        timeout: float | None = None,
        bufsize: int = 8192,
        waterlevel: int = 4096,
        readsize: int = 1024,
        pass_fds: tuple[int, ...] = (),
        close_fds: bool = True,
        preexec_fn: t.Callable[..., t.Any] | None = None,
    ) -> abc.Generator[shell.Typescript, None, None]:
        """Spool spools child process IO to buffers for the parent process to control.

        The "capture" implementation is focused on shell data streams and
        therefore was desgined with continuous interaction in mind.

        The parent process' terminal is put into raw mode, creating a "pass-through" for
        standard input keystrokes to be forwarded to a ptm. A ptm is the "master" file
        descriptor in a pseudo terminal pair, it forwards data to its cable, pts. The
        ptm is used by the parent process. The pts or "slave" is a terminal for use as
        the standard input of the child process.

        In most pty implementations, the ptm is used as the standard output and standard
        error file descriptors of the child process. However, to differentiate the
        standard output from standard error, distinct in-memory pipes are used. A pty
        is bidirectional such that data may be written or read from either ptm or pts
        end. If the child process is a controlling terminal, then echo mode should be
        off. But, if the child process is NOT a controlling terminal, then keystrokes
        forwarded to the pts will not be displayed. The solution is to set the pts
        into echo mode, then any data written to the "pass-through" will be echoed
        back to the ptm much like one would expect in a cooked mode terminal.

        A Typescript is leveraged to intercept the child process standard
        input, standard output, and standard error streams respectively. A Typescript
        supports callbacks that empower the parent process to enrich shell data or even
        write a stream to a respective parent process standard file descriptor.

        This method is a context manager to safely maintain the child process lifecycle
        during IO streaming.

        Parameters
        ----------
        cmd
            Command to execute in the child process.
        env
            Environment variables for the child process. By default inherits from
            parent process (forked).
        cwd
            Working directory to execute the child process in.
        echo
            Set the pts to echo mode (necessary if the child process is NOT a
            controlling terminal).
        timeout
            Time to wait before forcibly closing the child process when streaming ends.
        bufsize
            Buffer size for the child process standard output and standard error file
            descriptors.
        waterlevel
            Number of bytes to buffer in the parent process before needing to write to
            streams and reset the buffer.
        readsize
            Number of bytes to read from a file descriptor at a time.
        pass_fds
            File descriptors to keep open between the parent process and the child
            process.
        close_fds
            Control closing or inheriting of file descriptors.
        preexec_fn
            An object to be called in the child process just before execution.

        Returns
        -------
        A Typescript for the parent process to intercept and handle child process IO.

        Raises
        ------
        PastaError
            If the command is not found or executable.
            If the buffer size is less than 1.
            If the parent process standard input is not a TTY.
        """
        # split the command into argv
        args = shlex.split(cmd)

        # ensure executable path
        if exe := shutil.which(args[0]):
            args[0] = exe
        else:
            raise errors.PastaError("Command not found or executable: %s", exe)

        # validate buffer size
        if bufsize < 1:
            raise errors.PastaError("Buffer size cannot be less than 1")

        # get the standard input file descriptor
        stdin_fd = sys.stdin.fileno()
        if self.logger is not None:
            self.logger.debug("Parent process input file descriptor: %d", stdin_fd)

        if not os.isatty(stdin_fd):
            raise errors.PastaError("Standard input is not a tty.")

        # create an audit log
        sys.audit("pasta.pty", shlex.join(args))

        # create a pseudo-terminal (terminal, cable)
        ptm, pts = pty.openpty()
        if self.logger is not None:
            self.logger.debug("File descriptor ptm: %d", ptm)
            self.logger.debug("File descriptor pts: %d", pts)

        # set standard input terminal to raw mode
        mode = termios.tcgetattr(stdin_fd)
        # set pts to echo mode
        if echo != self._get_echo(pts):
            try:
                self._set_echo(pts, echo, logger=self.logger)
                restore = True
            except (IOError, termios.error) as err:
                restore = False
                if err.args[0] not in (errno.EINVAL, errno.ENOTTY):
                    raise

        if self.logger is not None:
            self.logger.debug("File descriptor echo mode: %s", "on" if echo else "off")

        proc = None
        blocking = False
        try:
            # start a child process
            if self.logger is not None:
                self.logger.debug("Executing child process: %s", cmd)
                if cwd is not None:
                    self.logger.debug("Child process workding directory: %s", cwd)

            proc = subprocess.Popen(
                args[:],
                env=env,
                cwd=cwd,
                start_new_session=True,  # https://www.man7.org/linux/man-pages/man2/setsid.2.html
                stdin=pts,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=bufsize,
                pass_fds=pass_fds,
                close_fds=close_fds,
                preexec_fn=preexec_fn,
            )

            if self.logger is not None:
                if proc.stdout is not None:
                    self.logger.debug(
                        "Child process output file descriptor: %d", proc.stdout.fileno()
                    )

                if proc.stderr is not None:
                    self.logger.debug(
                        "Child process error file descriptor: %d", proc.stderr.fileno()
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

            # resolve EOF ANSI escape code
            try:
                eof = ord(termios.tcgetattr(stdin_fd)[6][termios.VEOF])
            except (IOError, termios.error):
                eof = termios.CEOF

            # return proxied buffers for interception
            ts = shell.Typescript(self.config, eof=bytes([eof]), logger=self.logger)
            yield ts

            # set standard input terminal to raw mode
            try:
                tty.setraw(stdin_fd)
                if self.logger is not None:
                    self.logger.debug("File descriptor in raw mode: %d", stdin_fd)
                restore = True
            except termios.error:
                restore = False

            buf_i = b""
            buf_p = b""
            buf_o = b""
            buf_e = b""

            blocking = os.get_blocking(ptm)
            if blocking:
                if self.logger is not None:
                    self.logger.debug("Unblocking file descriptor: {}".format(ptm))

                os.set_blocking(ptm, False)

            while proc.poll() is None:
                rfds: list[int] = []
                wfds: list[int] = []

                # add parent process stdin to readers if buf_i not above waterlevel
                if len(buf_i) < waterlevel:
                    rfds.append(stdin_fd)

                # add ptm to readers if buf_p not above waterlevel
                if len(buf_p) < waterlevel:
                    rfds.append(ptm)

                # always add child process stdout if being captured
                if proc.stdout is not None:
                    rfds.append(proc.stdout.fileno())

                # always add child process stderr if being captured
                if proc.stderr is not None:
                    rfds.append(proc.stderr.fileno())

                # add ptm to writers if buf_i has data
                if len(buf_i) > 0:
                    wfds.append(ptm)

                rfds, wfds, _ = select.select(rfds, wfds, [])

                # read parent process stdin and copy data to buf_i
                if stdin_fd in rfds:
                    if self.logger is not None:
                        self.logger.debug("Reading from file descriptor: %d", stdin_fd)

                    data = os.read(stdin_fd, readsize)
                    if data:
                        if not echo:
                            data = ts.wrap(shell.Event.STDIN, data)

                        buf_i += data

                # read ptm and copy data to buf_p (should be echoed pts only)
                if ptm in rfds:
                    if self.logger is not None:
                        self.logger.debug("Reading from file descriptor: %d", ptm)

                    data = os.read(ptm, readsize)
                    if data:
                        if echo:
                            data = ts.wrap(shell.Event.STDIN, data)

                        buf_p += data

                # read child process stdout, intercept, and copy to buf_o
                if (
                    proc.stdout is not None
                    and (stdout_fd := proc.stdout.fileno()) in rfds
                ):
                    if self.logger is not None:
                        self.logger.debug("Reading from file descriptor: %d", stdout_fd)

                    try:
                        data = os.read(stdout_fd, readsize)
                        if data:
                            data = ts.wrap(shell.Event.STDOUT, data)
                            buf_o += data

                    except OSError:
                        # assume child process exited
                        break

                # read child process standard error, intercept, and copy to buffer
                if (
                    proc.stderr is not None
                    and (stderr_fd := proc.stderr.fileno()) in rfds
                ):
                    if self.logger is not None:
                        self.logger.debug("Reading from file descriptor: %d", stderr_fd)

                    try:
                        data = os.read(stderr_fd, readsize)
                        if data:
                            data = ts.wrap(shell.Event.STDERR, data)
                            buf_e += data

                    except OSError:
                        # assume child process exited
                        break

                # copy buf_i to ptm ("pass-through" parent process stdin to pts)
                if ptm in wfds:
                    if self.logger is not None:
                        self.logger.debug("Writing to file descriptor: %d", ptm)

                    n = os.write(ptm, buf_i)
                    buf_i = buf_i[n:]

            # flush typescript
            ts.wrap(shell.Event.STDOUT, ts.eof, flush=True)
            ts.wrap(shell.Event.STDIN, ts.eof + ts.crlf)
        except BaseException:
            # if an exception occurs e.g. KeyboardInterrupt, close the child process
            if proc is not None:
                proc.kill()

        finally:
            # exit the child process if something unexpected happened
            if proc is not None:
                try:
                    retcode = proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    retcode = proc.poll()

                if self.logger is not None:
                    self.logger.debug(
                        "Child process exited: %d",
                        retcode if retcode is not None else 0,
                    )

            # restore the parent process stdin
            if restore:
                termios.tcsetattr(stdin_fd, termios.TCSAFLUSH, mode)
                if self.logger is not None:
                    self.logger.debug(
                        "Parent process input file descriptor restored: %d", stdin_fd
                    )

            os.close(pts)
            os.close(ptm)
