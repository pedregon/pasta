"""The `action` module contains the interactive action performed by the user."""
import time
import uuid
from datetime import datetime

import pydantic


class Action(pydantic.BaseModel):
    """Action is an interactive action performed."""

    id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid4)
    prompt_ps1: bytes
    command_input: bytes
    command_output: bytes
    command_error: bytes = b""
    typescript: bytes
    time_started: datetime
    time_elapsed: float
    # shell_guess: str
