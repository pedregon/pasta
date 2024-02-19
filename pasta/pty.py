"""Pty code."""
from __future__ import annotations

import os
import sys
import subprocess
import shlex
import typing as t


class PTY:
    """S."""

    linesep: bytes = os.linesep.encode('ascii')
    crlf: bytes = "\r\n".encode('ascii')

    @classmethod
    def spawn(cls, argv: os.PathLike) -> PTY:
        """s."""
        if isinstance(argv, (list, tuple)):
            raise TypeError()
        
        # Shallow copy of argv so we can modify it
        argv = argv[:]
        command = argv[0]
        subprocess.Popen
        return PTY()

    @staticmethod
    def write_to_stdout(b: bytes) -> int:
        """Write to the standard output file descriptor.
        
        Parameters
        ----------
        b: bytes
            Data to write.

        Returns
        -------
        int:
            Bytes written.
        """
        try:
            return sys.stdout.buffer.write(b)
        except AttributeError:
            # If stdout has been replaced, it may not have .buffer
            return sys.stdout.write(b.decode("ascii", "replace"))

    def close(self, force=True):
        """This closes the connection with the child application. Note that
        calling close() more than once is valid. This emulates standard Python
        behavior with files. Set force to True if you want to make sure that
        the child is terminated (SIGKILL is sent if the child ignores SIGHUP
        and SIGINT). """
        if not self.closed:
            self.flush()
            self.fileobj.close() # Closes the file descriptor
            # Give kernel time to update process status.
            time.sleep(self.delayafterclose)
            if self.isalive():
                if not self.terminate(force):
                    raise PtyProcessError('Could not terminate the child.')
            self.fd = -1
            self.closed = True
            #self.pid = None

    def flush(self):
        """Flush does nothing, but supports an interface for a File-like object."""
        pass

    def __del__(self) -> None:
        """Delete system resources.
        
        Python only garbage collects Python objects. OS file descriptors are not Python
        objects, so they must be handled explicitly. If the child file
        descriptor was opened outside of this class (passed to the constructor)
        then this does not close it. 
        """
        if not self.closed:
            # It is possible for __del__ methods to execute during the
            # teardown of the Python VM itself. Thus self.close() may
            # trigger an exception because os.close may be None.
            try:
                self.close()
            # which exception, shouldn't we catch explicitly .. ?
            except:
                pass



def openpty() -> tuple[int, int]:
    """Open a pty master/slave pair.

    Returns
    -------
    master_fd: int
        Master file descriptor.
    slave_fd: int
        Slave file descriptor.
    """
    try:
        return os.openpty()
    except (AttributeError, OSError):
        pass
    master_fd, slave_name = _open_terminal()
    slave_fd = slave_open(slave_name)
    return master_fd, slave_fd