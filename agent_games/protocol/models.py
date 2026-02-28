
"""Protocol request and response models."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, StrictBool, StrictInt, StrictStr


class Request(BaseModel):
    """Incoming framework request. `reason` is mandatory for every command."""

    session_id: Optional[StrictStr] = None
    agent_id: StrictStr
    command: StrictStr
    args: Dict[str, Any] = Field(default_factory=dict)
    reason: StrictStr

    class Config:
        extra = "forbid"
        anystr_strip_whitespace = False


class Response(BaseModel):
    """Stable response envelope used by the dispatcher and CLI."""

    ok: StrictBool
    code: StrictStr
    message: StrictStr
    data: Dict[str, Any] = Field(default_factory=dict)
    turn_advanced: StrictBool
    turn_number: StrictInt
    game_over: StrictBool
    winner: Optional[StrictStr] = None
    session_id: Optional[StrictStr] = None

    class Config:
        extra = "forbid"
