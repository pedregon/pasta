import errno
import os
import termios
import typing as t
import warnings

import pytest
import fcntl
import sys
import pasta

_HAS_WINSZ = hasattr(termios, "TIOCGWINSZ") and hasattr(termios, "TIOCSWINSZ")

@pytest.fixture
def tcrestorewinsize(monkeypatch) -> t.Generator[tuple[int, int], None, None]:
    tty_fd = os.open("/dev/tty", os.O_RDWR)
    fcntl.ioctl(pasta.STDIN_FILENO, termios.TIOCSCTTY, 0)
    os.dup2(tty_fd, pasta.STDIN_FILENO)
    os.close(tty_fd)
    assert os.isatty(pasta.STDIN_FILENO)
    x, y = termios.tcgetwinsize(pasta.STDIN_FILENO)
    yield x, y
    termios.tcsetwinsize(pasta.STDIN_FILENO, (x, y))


@pytest.fixture
def openpty() -> t.Generator[tuple[int, int], None, None]:
    master, slave = pasta.openpty()
    yield master, slave
    os.close(master)
    os.close(slave)
   
def test_openpty(openpty, tcrestorewinsize) -> None:
    try:
        mode = termios.tcgetattr(pasta.STDIN_FILENO)
    except termios.error:
        warnings.warn("Failed to get pasta.STDIN_FILENO terminal mode.")
        mode = None
    
    if not hasattr(os, "openpty"):
        pytest.skip("os.openpty() not available.")

    master, slave = openpty
    if not os.isatty(slave):
        pytest.fail("Slave-end of pty is not a terminal.")
    
    if mode:
        assert termios.tcgetattr(slave) == mode

    stdin_dim = None
    new_dim = None
    if not _HAS_WINSZ:
        try:
            stdin_dim = tcrestorewinsize
        except termios.error:
            pass

    if stdin_dim:
        try:
            target_dim = (stdin_dim[0] + 1, stdin_dim[1] + 1)
            termios.tcsetwinsize(pasta.STDIN_FILENO, target_dim)
            new_dim = termios.tcgetwinsize(pasta.STDIN_FILENO)
            assert new_dim == target_dim
        except OSError:
            warnings.warn("Failed to set pasta.STDIN_FILENO window size.")
            pass

    if new_dim:
        assert termios.tcgetwinsize(slave) == new_dim

    blocking = os.get_blocking(master)
    try:
        os.set_blocking(master, False)
        try:
            s1 = os.read(master, 1024)
            assert s1 == b""
        except OSError as e:
            if e.errno != errno.EAGAIN:
                raise
    finally:
        os.set_blocking(master, blocking)

    os.write(slave, b"Ping!")
    assert os.read(master, 1024) == b"Ping!"