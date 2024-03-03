"""The `action` module contains the interactive action performed by the user."""
import datetime
import uuid

import pydantic


class Action(pydantic.BaseModel):
    """Action is an interactive action performed."""

    id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid4)
    # prompt_ps1: bytes
    # command_input: bytes
    # command_output: bytes
    # typescript: bytes
    # time_started: datetime.datetime
    # time_elapsed: datetime.datetime
    # shell_guess: str
