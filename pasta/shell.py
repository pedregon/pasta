"""A."""
from __future__ import annotations

import asyncio
import enum
import os
import queue
import readline
import sys
import time
import types
import typing as t
from collections import abc, deque

from . import actions


class Event(enum.IntEnum):
    STDIN = 0
    STDOUT = 1
    STDERR = 2


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

    def __init__(
        self,
        histsize: int = 1000,
    ) -> None:
        self.stdin = deque[bytes](maxlen=histsize)
        self.stdout = deque[bytes](maxlen=histsize)
        self.stderr = deque[bytes](maxlen=histsize)
        self.buf_i = b""
        self.buf_o = b""
        self.buf_e = b""
        self.handlers = {}
        self.io = True

    def addHandler(self, event: Event, handler: t.Callable[[bytes], bytes]) -> None:
        self.handlers[event] = self.handlers.get(event, []) + [handler]

    def read(self) -> bytes:
        pass

    def write(self, b: bytes) -> int:
        self.stdout.append(b)
        return len(b)

    async def capture() -> t.AsyncGenerator[actions.Action, None]:
        yield actions.Action()

    def wrap(self, event: Event, b: bytes) -> bytes:
        if handlers := self.handlers.get(event):
            for handler in handlers:
                b = handler(b)

        match event:
            case Event.STDIN:
                self.buf_i += b
            case Event.STDOUT:
                self.buf_o += b
            case Event.STDERR:
                self.buf_e += b

        if (event is Event.STDOUT or event is Event.STDERR) and (
            not self.buf_o and not self.buf_e
        ):
            self.stdout.append(self.buf_i)
            self.buf_i = b""

        return b

    # def tokenize(self) -> bytes:
    #     """A."""
    #     try:
    #         b = await anext(self.stream)
    #         return b
    #     except StopAsyncIteration:
    #         return b""