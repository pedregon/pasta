"""A."""
from __future__ import annotations

import asyncio
import os
import queue
import time
import types
import typing as t
from collections import abc, deque

from . import actions


class Typescript:
    """Typescript is a shell data reader.

    Attributes
    ----------
    linesep
        Cooked mode terminal line separator.
    crlf
        Terminal carriage return and line feed.

    """

    linesep: bytes = os.linesep.encode("ascii")
    crlf: bytes = "\r\n".encode("ascii")

    def __init__(self, histsize: int = 1000) -> None:
        self.histsize = histsize
        self.buffer = []

    def write(self, b: bytes) -> int:
        self.buffer.append(b)
        return len(b)

    def wrap(self, b: bytes) -> bytes:
        self.write(b)
        return b

    # def tokenize(self) -> bytes:
    #     """A."""
    #     try:
    #         b = await anext(self.stream)
    #         return b
    #     except StopAsyncIteration:
    #         return b""
