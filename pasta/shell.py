"""A."""
from __future__ import annotations

import os
import queue
import types
import typing as t
from collections import abc, deque

from . import actions


class Typescript:
    """Typescript is a shell data reader."""

    linesep: bytes = os.linesep.encode("ascii")
    crlf: bytes = "\r\n".encode("ascii")

    def __init__(self, stream: deque[bytes]) -> None:
        self.stream = stream

    def tokenize(self) -> abc.Generator[bytes, None, None]:
        """A."""
        try:
            yield self.stream.pop()
        except IndexError:
            pass