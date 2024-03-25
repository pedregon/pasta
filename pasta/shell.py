"""A."""
from __future__ import annotations

import asyncio
import enum
import logging
import os
import queue
import re
import readline
import sys
import termios
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
        eof: bytes = bytes([termios.CEOF]),
        histsize: int = 1000,
        ps1: bool = False,
        logger: logging.Logger | None = None,
    ) -> None:
        # self.stdin = deque[bytes](maxlen=histsize)
        # self.ps1 = deque[bytes](maxlen=histsize)
        # self.stdout = deque[bytes](maxlen=histsize)
        # self.stderr = deque[bytes](maxlen=histsize)
        self.eof = eof
        self.logger = logger
        self.ps1 = ps1
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
                if self.buf_i.endswith(b"\n") and self.buf_c:
                    action = actions.Action(
                        prompt_ps1=self.buf_ps1,
                        command_input=self.buf_i,
                        command_output=self.buf_o,
                        command_error=self.buf_e,
                        typescript=self.buf_ps1 + self.buf_i + self.buf_c,
                        time_started=self.start_time,
                        time_elapsed=datetime.utcnow().timestamp()
                        - self.start_time.timestamp(),
                    )
                    self.actions.append(action)
                    if self.logger is not None:
                        self.logger.info("Command completed: %d", action.time_elapsed)

                    self.buf_ps1 = b""
                    self.buf_i = b""
                    self.buf_o = b""
                    self.buf_e = b""
                    self.buf_c = b""
                    if b == self.eof + self.crlf:
                        return b""

                if not self.buf_i and not self.buf_ps1 and not self.buf_c:
                    self.start_time = datetime.utcnow()
                    if self.logger is not None:
                        self.logger.info("New command: %s", self.start_time.isoformat())

                if not self.buf_i and self.buf_c and not self.buf_c.endswith(self.eof):
                    if self.logger is not None:
                        self.logger.info("Capturing PS1 w/ CRLF")

                    self.buf_ps1 += b
                else:
                    if self.logger is not None:
                        self.logger.info("Capturing command input " + b.hex())

                    self.buf_i += b
            case Event.STDOUT:
                if not self.buf_i and b != self.eof:
                    if self.logger is not None:
                        self.logger.info("Capturing PS1")

                    self.buf_ps1 += b
                else:
                    if self.logger is not None:
                        self.logger.info("Capturing command output " + b.hex())

                    self.buf_o += b
                    self.buf_c += b
            case Event.STDERR:
                if not self.buf_i:
                    if self.logger is not None:
                        self.logger.info("Capturing PS1")

                    self.buf_ps1 += b
                else:
                    if self.logger is not None:
                        self.logger.info("Capturing command error")

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