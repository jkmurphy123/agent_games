
from pydantic import BaseModel
from typing import Dict, Any, Optional

class Request(BaseModel):
    session_id: Optional[str] = None
    agent_id: str
    command: str
    args: Dict[str, Any] = {}
    reason: str

class Response(BaseModel):
    ok: bool
    code: str
    message: str
    data: Dict[str, Any]
    turn_advanced: bool
    turn_number: int
    game_over: bool
    winner: Optional[str]
    session_id: Optional[str]
