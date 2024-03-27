from __future__ import annotations

import logging
import os
import pathlib
import re
import tomllib
import typing as t

import pydantic

__config__ = f"{__package__}.toml"


class PromptRule(pydantic.BaseModel):
    command: t.Pattern[str]
    description: str = ""
    pattern: t.Pattern[str]


class LogConfig(pydantic.BaseModel):
    level: int = logging.INFO
    directory: str | os.PathLike[str] = str(
        pathlib.Path(
            os.environ.get(
                "XDG_STATE_HOME",
                pathlib.Path.home().joinpath(".local", "state", __package__),
            )
        )
    )
    max_size: int = 2048
    backups: int = 3
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)


class Config(pydantic.BaseModel):
    """Config is a TOML configuration for Pasta.

    Attributes
    ----------
    plugins
        List of Python modules to load.
    """

    logging: LogConfig = pydantic.Field(default_factory=LogConfig)
    prompt: list[PromptRule] = [
        PromptRule(
            command=re.compile(r"zsh"),
            description="zle reset-prompt",
            pattern=re.compile(r"\w+\r\r"),
        ),
    ]

    @classmethod
    def _dumps_value(cls, value: t.Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            return f'"{value}"'
        elif isinstance(value, t.Pattern):
            return f"'{value.pattern}'"
        elif isinstance(value, list):
            return f"[{', '.join(cls._dumps_value(v) for v in value)}]"
        elif isinstance(value, t.Mapping):
            if len(value) == 0:
                return "{}"

            toml = ["{"]
            for k, v in value.items():
                toml.append(f"\t{k} = {cls._dumps_value(v)},")

            return "\n".join(toml + ["}"])
        else:
            raise TypeError(f"{type(value).__name__} {value!r} is not supported")

    @classmethod
    def _dumps_table(
        cls,
        data: t.Mapping[str, t.Any],
        table: str = "",
    ) -> str:
        toml = []
        for key, value in data.items():
            if isinstance(value, t.Mapping):
                table_key = f"{table}.{key}" if table else key
                toml.append(f"\n[{table_key}]\n{cls._dumps_table(value, table_key)}")
            elif isinstance(value, list):
                for obj in value:
                    if isinstance(obj, t.Mapping):
                        table_key = f"{table}.{key}" if table else key
                        toml.append(f"\n[[{table_key}]]")
                        for k, v in obj.items():
                            toml.append(f"{k} = {cls._dumps_value(v)}")
                    else:
                        toml.append(f"{key} = {cls._dumps_value(value)}")
                        break
            else:
                toml.append(f"{key} = {cls._dumps_value(value)}")

        return "\n".join(toml).lstrip("\n")

    def dumps(self, comment: bool = False) -> str:
        """Dump to a TOML string."""
        if comment:
            data = self.model_dump(exclude_none=True)
            document = self._dumps_table(data, table=__package__)
            return "# " + "\n# ".join(document.split("\n"))

        data = self.model_dump(exclude_none=True, exclude_unset=True)
        document = self._dumps_table(data, table=__package__)
        return document

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