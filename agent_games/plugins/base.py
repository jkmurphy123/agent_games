"""Plugin contract for AgentGames.

Plugins must remain pure with respect to persistence: they receive state, return
state, and never write session files directly. Unsupported standard commands
must return `NOT_SUPPORTED`; unknown commands are handled by the framework.
"""

from __future__ import annotations

from typing import Any, Dict, Protocol, Tuple


class GamePlugin(Protocol):
    def manifest(self) -> Dict[str, Any]:
        ...

    def initialize(self, options: Dict[str, Any]) -> Dict[str, Any]:
        ...

    def is_action(self, command: str) -> bool:
        ...

    def execute(
        self,
        command: str,
        args: Dict[str, Any],
        state: Dict[str, Any],
        request_meta: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Dict[str, Any], str, str, bool]:
        ...

    def opponent_step(self, state: Dict[str, Any]) -> Dict[str, Any]:
        ...

    def generate_agent_view(self, state: Dict[str, Any]) -> Dict[str, Any]:
        ...

    def generate_human_view(self, state: Dict[str, Any]) -> Dict[str, Any]:
        ...
