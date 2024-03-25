from __future__ import annotations

import os
import pathlib
import tomllib
import typing as t

import pydantic

__config__ = f"{__package__}.toml"


class Config(pydantic.BaseModel):
    """Config is a TOML configuration for Pasta.

    Attributes
    ----------
    plugins
        List of Python modules to load.
    """

    plugins: list[str] = []

    @classmethod
    def load(cls, handle: t.BinaryIO) -> Config:
        """Load a TOML file.

        Parameters
        ----------
        handle
            TOML file.

        Returns
        -------
        Config.

        Raises
        ------
        TOMLDecodeError
        """
        data = tomllib.load(handle)
        return cls.model_validate(data.get(__package__, {}))

    @classmethod
    def loads(cls, document: str) -> Config:
        """Load a TOML string.

        Parameters
        ----------
        document
            TOML string.

        Returns
        -------
        Config.

        Raises
        ------
        TOMLDecodeError
        """
        data = tomllib.loads(document)
        return cls.model_validate(data.get(__package__, {}))

    @classmethod
    def find(cls) -> str | os.PathLike[str] | None:
        """Find a config.

        Preferences:
        1. Current working directory.
        2. $XDG_CONFIG_HOME/pasta
        3. Recursive search up to root.

        Returns
        -------
        Config path if found.
        """
        candidate = pathlib.Path.cwd().joinpath(__config__)
        if candidate.exists():
            return candidate

        XDG_CONFIG_HOME = pathlib.Path(
            os.environ.get("XDG_CONFIG_HOME", pathlib.Path.home().joinpath(".config"))
        )

        usrpath = XDG_CONFIG_HOME.joinpath(__package__, __config__)
        if usrpath.exists():
            return usrpath

        root_dir = os.path.abspath("/")
        while str(candidate.parent.parent) != root_dir:
            candidate = candidate.parent.parent.joinpath(__config__)
            if candidate.exists():
                return candidate

        return None