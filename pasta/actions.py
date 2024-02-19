"""The `action` module contains the interactive action performed by the user."""
import dataclasses
import datetime
import uuid


@dataclasses.dataclass
class Action:
    """Action is an interactive action performed."""
    
    id: uuid.UUID
    prompt_ps1: bytes
    command_input: bytes
    command_output: bytes
    typescript: bytes
    time_started: datetime.datetime
    time_elapsed: datetime.datetime
    shell_guess: str
    