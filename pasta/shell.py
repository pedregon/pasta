"""A."""
from __future__ import annotations

import os
import types
import typing as t
from collections import abc

from . import actions


class Typescript:
    """Typescript is a shell data reader."""

    linesep: bytes = os.linesep.encode("ascii")
    crlf: bytes = "\r\n".encode("ascii")

    def tokenize(self) -> abc.Generator[actions.Action, None, None]:
        yield actions.Action()

    def __enter__(self) -> Typescript:
        return self

    @t.overload
    def __exit__(self, exc_type: None, exc_val: None, exc_tb: None) -> None:
        ...

    @t.overload
    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: types.TracebackType,
    ) -> None:
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        pass