from __future__ import annotations

import json

from agent_games.protocol.errors import INVALID_MOVE, NOT_SUPPORTED, OK, UNKNOWN_COMMAND
from agent_games.registry import load_plugins
from agent_games.runtime.dispatcher import Dispatcher
from agent_games.runtime.session_store import SessionStore


def make_dispatcher(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_GAMES_SESSIONS_DIR", str(tmp_path))
    return Dispatcher(load_plugins(), session_store=SessionStore())


def register(dispatcher):
    response = dispatcher.dispatch(
        {
            "agent_id": "agent-1",
            "command": "register",
            "args": {"plugin_id": "tictactoe"},
            "reason": "start game",
        }
    )
    assert response["code"] == OK
    return response["session_id"]


def test_missing_reason_rejected(tmp_path, monkeypatch):
    dispatcher = make_dispatcher(tmp_path, monkeypatch)
    response = dispatcher.dispatch({"agent_id": "agent-1", "command": "register", "args": {}})
    assert response["ok"] is False
    assert response["code"] == "INVALID_ARGS"


def test_register_creates_session_and_turn0_snapshot(tmp_path, monkeypatch):
    dispatcher = make_dispatcher(tmp_path, monkeypatch)
    session_id = register(dispatcher)

    session_dir = tmp_path / session_id
    assert session_dir.exists()
    assert json.loads((session_dir / "meta.json").read_text(encoding="utf-8"))["plugin_id"] == "tictactoe"

    snapshot = json.loads((session_dir / "turns" / "0000.json").read_text(encoding="utf-8"))
    assert snapshot["turn_number"] == 0
    assert snapshot["canonical_state"]["board"] == [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]]


def test_rules_and_status_do_not_advance_turn(tmp_path, monkeypatch):
    dispatcher = make_dispatcher(tmp_path, monkeypatch)
    session_id = register(dispatcher)

    for command in ("rules", "status"):
        response = dispatcher.dispatch(
            {
                "session_id": session_id,
                "agent_id": "agent-1",
                "command": command,
                "args": {},
                "reason": f"check {command}",
            }
        )
        assert response["code"] == OK
        assert response["turn_advanced"] is False
        assert response["turn_number"] == 0


def test_valid_move_advances_turn_and_opponent_moves(tmp_path, monkeypatch):
    dispatcher = make_dispatcher(tmp_path, monkeypatch)
    session_id = register(dispatcher)

    response = dispatcher.dispatch(
        {
            "session_id": session_id,
            "agent_id": "agent-1",
            "command": "move",
            "args": {"x": 0, "y": 0},
            "reason": "take a corner",
        }
    )

    assert response["code"] == OK
    assert response["turn_advanced"] is True
    assert response["turn_number"] == 1

    snapshot = json.loads((tmp_path / session_id / "turns" / "0001.json").read_text(encoding="utf-8"))
    board = snapshot["canonical_state"]["board"]
    assert board[0][0] == "X"
    assert board[1][1] == "O"
    assert len(snapshot["events"]) == 2


def test_invalid_move_does_not_advance_turn(tmp_path, monkeypatch):
    dispatcher = make_dispatcher(tmp_path, monkeypatch)
    session_id = register(dispatcher)

    first = dispatcher.dispatch(
        {
            "session_id": session_id,
            "agent_id": "agent-1",
            "command": "move",
            "args": {"x": 0, "y": 0},
            "reason": "first move",
        }
    )
    assert first["code"] == OK

    response = dispatcher.dispatch(
        {
            "session_id": session_id,
            "agent_id": "agent-1",
            "command": "move",
            "args": {"x": 0, "y": 0},
            "reason": "repeat invalid move",
        }
    )

    assert response["ok"] is False
    assert response["code"] == INVALID_MOVE
    assert response["turn_advanced"] is False
    assert response["turn_number"] == 1


def test_history_view_latest_work(tmp_path, monkeypatch):
    dispatcher = make_dispatcher(tmp_path, monkeypatch)
    session_id = register(dispatcher)
    dispatcher.dispatch(
        {
            "session_id": session_id,
            "agent_id": "agent-1",
            "command": "move",
            "args": {"x": 0, "y": 0},
            "reason": "advance one turn",
        }
    )

    history = dispatcher.dispatch(
        {
            "session_id": session_id,
            "agent_id": "agent-1",
            "command": "history",
            "args": {},
            "reason": "list turns",
        }
    )
    assert history["data"]["turns"] == [0, 1]

    latest = dispatcher.dispatch(
        {
            "session_id": session_id,
            "agent_id": "agent-1",
            "command": "latest",
            "args": {},
            "reason": "read latest snapshot",
        }
    )
    assert latest["data"]["snapshot"]["turn_number"] == 1

    view = dispatcher.dispatch(
        {
            "session_id": session_id,
            "agent_id": "agent-1",
            "command": "view",
            "args": {"turn_number": 0},
            "reason": "read initial turn",
        }
    )
    assert view["data"]["snapshot"]["turn_number"] == 0


def test_not_supported_command_returns_not_supported(tmp_path, monkeypatch):
    dispatcher = make_dispatcher(tmp_path, monkeypatch)
    session_id = register(dispatcher)

    response = dispatcher.dispatch(
        {
            "session_id": session_id,
            "agent_id": "agent-1",
            "command": "reset",
            "args": {},
            "reason": "try unsupported reset",
        }
    )

    assert response["ok"] is False
    assert response["code"] == NOT_SUPPORTED


def test_unknown_command_returns_unknown_command(tmp_path, monkeypatch):
    dispatcher = make_dispatcher(tmp_path, monkeypatch)
    session_id = register(dispatcher)

    response = dispatcher.dispatch(
        {
            "session_id": session_id,
            "agent_id": "agent-1",
            "command": "dance",
            "args": {},
            "reason": "nonsense",
        }
    )

    assert response["ok"] is False
    assert response["code"] == UNKNOWN_COMMAND
