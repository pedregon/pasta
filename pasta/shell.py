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
    """Typescript is a shell data reader."""

    linesep: bytes = os.linesep.encode("ascii")
    crlf: bytes = "\r\n".encode("ascii")

    def __init__(self, stream: t.AsyncGenerator[bytes, None]) -> None:
        self.stream = stream

    async def tokenize(self) -> bytes:
        """A."""
        try:
            b = await anext(self.stream)
            return b
        except StopAsyncIteration:
            return b""
