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
from datetime import datetime

import stransi

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
        # self.stdin = deque[bytes](maxlen=histsize)
        # self.ps1 = deque[bytes](maxlen=histsize)
        # self.stdout = deque[bytes](maxlen=histsize)
        # self.stderr = deque[bytes](maxlen=histsize)
        self.buf_i = b""
        self.buf_ps1 = b""
        self.buf_o = b""
        self.buf_e = b""
        self.buf_c = b""
        self.start_time = datetime.utcnow()
        self.handlers = {}
        self.actions = deque[actions.Action](maxlen=histsize)

    def addHandler(self, event: Event, handler: t.Callable[[bytes], bytes]) -> None:
        self.handlers[event] = self.handlers.get(event, []) + [handler]

    def read(self) -> bytes:
        pass

    def write(self, b: bytes) -> int:
        # self.buf_o += b
        return len(b)

    async def capture() -> t.AsyncGenerator[actions.Action, None]:
        yield actions.Action()

    def wrap(self, event: Event, b: bytes) -> bytes:
        if handlers := self.handlers.get(event):
            for handler in handlers:
                b = handler(b)

        match event:
            case Event.STDIN:
                if self.buf_i and self.buf_c:
                    self.actions.append(
                        actions.Action(
                            prompt_ps1=self.buf_ps1,
                            command_input=self.buf_i,
                            command_output=self.buf_o,
                            command_error=self.buf_e,
                            typescript=self.buf_ps1 + self.buf_i + self.buf_c,
                            time_started=self.start_time,
                            time_elapsed=datetime.utcnow().timestamp()
                            - self.start_time.timestamp(),
                        )
                    )
                    self.buf_ps1 = b""
                    self.buf_i = b""
                    self.buf_o = b""
                    self.buf_e = b""
                    self.buf_c = b""

                if not self.buf_i and not self.buf_c:
                    self.start_time = datetime.utcnow()

                if b"\r" in b:
                    self.buf_ps1 += b
                else:
                    self.buf_i += b
            case Event.STDOUT:
                if not self.buf_i:
                    self.buf_ps1 += b
                else:
                    self.buf_o += b
                    self.buf_c += b
            case Event.STDERR:
                if not self.buf_i:
                    self.buf_ps1 += b
                else:
                    self.buf_e += b
                    self.buf_c += b

        return b

    # def tokenize(self) -> bytes:
    #     """A."""
    #     try:
    #         b = await anext(self.stream)
    #         return b
    #     except StopAsyncIteration:
    #         return b""
