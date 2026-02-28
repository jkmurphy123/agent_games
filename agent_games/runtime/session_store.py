"""Disk-backed session storage for replayable local sessions."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_games.runtime.serialization import stable_json_dumps


def _load_config_sessions_dir() -> Optional[str]:
    config_path = Path("config.toml")
    if not config_path.exists():
        return None

    try:
        import tomllib

        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    return config.get("storage", {}).get("sessions_dir")


class SessionStore:
    def __init__(self, root_dir: Optional[str] = None):
        configured = (
            root_dir
            or os.environ.get("AGENT_GAMES_SESSIONS_DIR")
            or _load_config_sessions_dir()
            or "sessions"
        )
        self.root_dir = Path(configured)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _session_dir(self, session_id: str) -> Path:
        return self.root_dir / session_id

    def _meta_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "meta.json"

    def _log_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "log.ndjson"

    def _turns_dir(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "turns"

    def create_session(
        self,
        plugin_id: str,
        agent_id: str,
        protocol_version: str,
        options: Dict[str, Any],
    ) -> str:
        session_id = str(uuid.uuid4())
        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=False)
        self._turns_dir(session_id).mkdir(parents=True, exist_ok=True)
        self._log_path(session_id).touch()
        self.write_meta(
            session_id,
            {
                "session_id": session_id,
                "plugin_id": plugin_id,
                "agent_id": agent_id,
                "protocol_version": protocol_version,
                "options": options,
            },
        )
        return session_id

    def write_meta(self, session_id: str, meta: Dict[str, Any]) -> None:
        self._meta_path(session_id).write_text(
            stable_json_dumps(meta),
            encoding="utf-8",
        )

    def read_meta(self, session_id: str) -> Dict[str, Any]:
        return json.loads(self._meta_path(session_id).read_text(encoding="utf-8"))

    def append_log(self, session_id: str, entry: Dict[str, Any]) -> None:
        with self._log_path(session_id).open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(stable_json_dumps(entry))
            handle.write("\n")

    def write_turn_snapshot(
        self,
        session_id: str,
        turn_number: int,
        canonical_state: Dict[str, Any],
        agent_view: Dict[str, Any],
        human_view: Dict[str, Any],
        events_for_turn: List[Dict[str, Any]],
    ) -> None:
        snapshot = {
            "turn_number": turn_number,
            "canonical_state": canonical_state,
            "agent_view": agent_view,
            "human_view": human_view,
            "events": events_for_turn,
        }
        path = self._turns_dir(session_id) / f"{turn_number:04d}.json"
        path.write_text(stable_json_dumps(snapshot), encoding="utf-8")

    def list_turns(self, session_id: str) -> List[int]:
        turns_dir = self._turns_dir(session_id)
        if not turns_dir.exists():
            return []
        return sorted(int(path.stem) for path in turns_dir.glob("*.json"))

    def read_turn(self, session_id: str, turn_number: int) -> Dict[str, Any]:
        path = self._turns_dir(session_id) / f"{turn_number:04d}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def latest_turn(self, session_id: str) -> int:
        turns = self.list_turns(session_id)
        if not turns:
            raise FileNotFoundError(f"No turns found for session {session_id}")
        return turns[-1]
