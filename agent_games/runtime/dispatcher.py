
"""Main request dispatcher for the local-first runtime."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from pydantic import ValidationError

from agent_games.protocol.commands import STANDARD_COMMANDS
from agent_games.protocol.errors import (
    GAME_OVER,
    INTERNAL_ERROR,
    INVALID_ARGS,
    NOT_REGISTERED,
    NOT_SUPPORTED,
    OK,
    UNKNOWN_COMMAND,
)
from agent_games.protocol.models import Request, Response
from agent_games.protocol.version import PROTOCOL_VERSION
from agent_games.runtime.serialization import state_hash
from agent_games.runtime.session_store import SessionStore


FRAMEWORK_COMMANDS = {"ping", "schema", "history", "view", "latest"}


class Dispatcher:
    def __init__(self, plugins: Dict[str, object], session_store: Optional[SessionStore] = None):
        self.plugins = plugins
        self.session_store = session_store or SessionStore()

    def _response(
        self,
        *,
        ok: bool,
        code: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        turn_advanced: bool,
        turn_number: int,
        game_over: bool,
        winner: Optional[str],
        session_id: Optional[str],
    ) -> Dict[str, Any]:
        response = Response(
            ok=ok,
            code=code,
            message=message,
            data=data or {},
            turn_advanced=turn_advanced,
            turn_number=turn_number,
            game_over=game_over,
            winner=winner,
            session_id=session_id,
        )
        return response.model_dump() if hasattr(response, "model_dump") else response.dict()

    def _load_session(self, session_id: str) -> tuple[dict, dict]:
        meta = self.session_store.read_meta(session_id)
        turn_number = self.session_store.latest_turn(session_id)
        snapshot = self.session_store.read_turn(session_id, turn_number)
        return meta, snapshot

    def _log(self, session_id: str, entry: Dict[str, Any]) -> None:
        self.session_store.append_log(session_id, entry)

    def _handle_framework_command(
        self,
        request: Request,
        meta: Dict[str, Any],
        snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        turn_number = snapshot["turn_number"]
        state = snapshot["canonical_state"]
        session_id = meta["session_id"]

        if request.command == "ping":
            return self._response(
                ok=True,
                code=OK,
                message="pong",
                data={"protocol_version": PROTOCOL_VERSION},
                turn_advanced=False,
                turn_number=turn_number,
                game_over=state["game_over"],
                winner=state["winner"],
                session_id=session_id,
            )
        if request.command == "schema":
            return self._response(
                ok=True,
                code=OK,
                message="Schema information",
                data={
                    "protocol_version": PROTOCOL_VERSION,
                    "request_fields": ["session_id", "agent_id", "command", "args", "reason"],
                    "response_fields": [
                        "ok",
                        "code",
                        "message",
                        "data",
                        "turn_advanced",
                        "turn_number",
                        "game_over",
                        "winner",
                        "session_id",
                    ],
                    "standard_commands": STANDARD_COMMANDS,
                },
                turn_advanced=False,
                turn_number=turn_number,
                game_over=state["game_over"],
                winner=state["winner"],
                session_id=session_id,
            )
        if request.command == "history":
            turns = self.session_store.list_turns(session_id)
            return self._response(
                ok=True,
                code=OK,
                message="History retrieved",
                data={"turns": turns},
                turn_advanced=False,
                turn_number=turn_number,
                game_over=state["game_over"],
                winner=state["winner"],
                session_id=session_id,
            )
        if request.command == "latest":
            return self._response(
                ok=True,
                code=OK,
                message="Latest snapshot retrieved",
                data={"snapshot": snapshot},
                turn_advanced=False,
                turn_number=turn_number,
                game_over=state["game_over"],
                winner=state["winner"],
                session_id=session_id,
            )

        requested_turn = request.args.get("turn_number", turn_number)
        try:
            view_snapshot = self.session_store.read_turn(session_id, requested_turn)
        except FileNotFoundError:
            return self._response(
                ok=False,
                code=INVALID_ARGS,
                message=f"Turn {requested_turn} not found",
                turn_advanced=False,
                turn_number=turn_number,
                game_over=state["game_over"],
                winner=state["winner"],
                session_id=session_id,
            )
        return self._response(
            ok=True,
            code=OK,
            message="Turn view retrieved",
            data={"snapshot": view_snapshot},
            turn_advanced=False,
            turn_number=turn_number,
            game_over=state["game_over"],
            winner=state["winner"],
            session_id=session_id,
        )

    def dispatch(self, raw_request: Dict[str, Any]) -> Dict[str, Any]:
        try:
            request = (
                Request.model_validate(raw_request)
                if hasattr(Request, "model_validate")
                else Request.parse_obj(raw_request)
            )
        except ValidationError as exc:
            session_id = raw_request.get("session_id") if isinstance(raw_request, dict) else None
            return self._response(
                ok=False,
                code=INVALID_ARGS,
                message=str(exc),
                turn_advanced=False,
                turn_number=0,
                game_over=False,
                winner=None,
                session_id=session_id,
            )

        if request.command != "register" and not request.session_id:
            return self._response(
                ok=False,
                code=NOT_REGISTERED,
                message="session_id is required for non-register commands",
                turn_advanced=False,
                turn_number=0,
                game_over=False,
                winner=None,
                session_id=None,
            )

        if request.command == "register":
            plugin_id = request.args.get("plugin_id", "tictactoe")
            plugin = self.plugins.get(plugin_id)
            if plugin is None:
                return self._response(
                    ok=False,
                    code=NOT_REGISTERED,
                    message=f"Plugin '{plugin_id}' is not registered",
                    turn_advanced=False,
                    turn_number=0,
                    game_over=False,
                    winner=None,
                    session_id=None,
                )

            options = request.args.get("options", {})
            session_id = self.session_store.create_session(
                plugin_id=plugin_id,
                agent_id=request.agent_id,
                protocol_version=PROTOCOL_VERSION,
                options=options,
            )
            initial_state = plugin.initialize(options)
            initial_state["turn_number"] = 0
            snapshot_events = [
                {
                    "type": "register",
                    "reason": request.reason,
                    "agent_id": request.agent_id,
                    "plugin_id": plugin_id,
                }
            ]
            self.session_store.write_turn_snapshot(
                session_id=session_id,
                turn_number=0,
                canonical_state=initial_state,
                agent_view=plugin.generate_agent_view(initial_state),
                human_view=plugin.generate_human_view(initial_state),
                events_for_turn=snapshot_events,
            )
            response = self._response(
                ok=True,
                code=OK,
                message="Registered",
                data={"plugin_id": plugin_id, "protocol_version": PROTOCOL_VERSION},
                turn_advanced=False,
                turn_number=0,
                game_over=initial_state["game_over"],
                winner=initial_state["winner"],
                session_id=session_id,
            )
            request_payload = (
                request.model_dump() if hasattr(request, "model_dump") else request.dict()
            )
            self._log(
                session_id,
                {
                    "request": request_payload,
                    "response": response,
                    "pre_hash": None,
                    "post_hash": state_hash(initial_state),
                    "turn_advanced": False,
                    "turn_number": 0,
                },
            )
            return response

        try:
            meta, snapshot = self._load_session(request.session_id)
        except FileNotFoundError:
            return self._response(
                ok=False,
                code=NOT_REGISTERED,
                message="Session not found",
                turn_advanced=False,
                turn_number=0,
                game_over=False,
                winner=None,
                session_id=request.session_id,
            )

        plugin_id = meta["plugin_id"]
        plugin = self.plugins.get(plugin_id)
        if plugin is None:
            return self._response(
                ok=False,
                code=INTERNAL_ERROR,
                message=f"Plugin '{plugin_id}' could not be loaded",
                turn_advanced=False,
                turn_number=snapshot["turn_number"],
                game_over=snapshot["canonical_state"]["game_over"],
                winner=snapshot["canonical_state"]["winner"],
                session_id=request.session_id,
            )

        state = deepcopy(snapshot["canonical_state"])
        pre_hash = state_hash(state)
        request_payload = request.model_dump() if hasattr(request, "model_dump") else request.dict()

        if request.command in FRAMEWORK_COMMANDS:
            response = self._handle_framework_command(request, meta, snapshot)
            self._log(
                request.session_id,
                {
                    "request": request_payload,
                    "response": response,
                    "pre_hash": pre_hash,
                    "post_hash": pre_hash,
                    "turn_advanced": False,
                    "turn_number": snapshot["turn_number"],
                },
            )
            return response

        if request.command not in STANDARD_COMMANDS:
            response = self._response(
                ok=False,
                code=UNKNOWN_COMMAND,
                message=f"Unknown command '{request.command}'",
                turn_advanced=False,
                turn_number=snapshot["turn_number"],
                game_over=state["game_over"],
                winner=state["winner"],
                session_id=request.session_id,
            )
            self._log(
                request.session_id,
                {
                    "request": request_payload,
                    "response": response,
                    "pre_hash": pre_hash,
                    "post_hash": pre_hash,
                    "turn_advanced": False,
                    "turn_number": snapshot["turn_number"],
                },
            )
            return response

        supported_commands = set(plugin.manifest().get("supported_commands", []))
        if request.command not in supported_commands:
            response = self._response(
                ok=False,
                code=NOT_SUPPORTED,
                message=f"Command '{request.command}' is not supported by plugin '{plugin_id}'",
                turn_advanced=False,
                turn_number=snapshot["turn_number"],
                game_over=state["game_over"],
                winner=state["winner"],
                session_id=request.session_id,
            )
            self._log(
                request.session_id,
                {
                    "request": request_payload,
                    "response": response,
                    "pre_hash": pre_hash,
                    "post_hash": pre_hash,
                    "turn_advanced": False,
                    "turn_number": snapshot["turn_number"],
                },
            )
            return response

        try:
            result_data, new_state, code, message, action_succeeded = plugin.execute(
                request.command,
                request.args,
                deepcopy(state),
                {
                    "session_id": request.session_id,
                    "agent_id": request.agent_id,
                    "reason": request.reason,
                    "turn_number": snapshot["turn_number"],
                },
            )
        except Exception as exc:
            response = self._response(
                ok=False,
                code=INTERNAL_ERROR,
                message=str(exc),
                turn_advanced=False,
                turn_number=snapshot["turn_number"],
                game_over=state["game_over"],
                winner=state["winner"],
                session_id=request.session_id,
            )
            self._log(
                request.session_id,
                {
                    "request": request_payload,
                    "response": response,
                    "pre_hash": pre_hash,
                    "post_hash": pre_hash,
                    "turn_advanced": False,
                    "turn_number": snapshot["turn_number"],
                },
            )
            return response

        is_action = plugin.is_action(request.command)
        current_turn = snapshot["turn_number"]
        final_state = state
        final_turn_number = current_turn
        turn_advanced = False

        if is_action and action_succeeded and code == OK:
            final_state = deepcopy(new_state)
            events_for_turn = [
                {
                    "type": "action",
                    "command": request.command,
                    "reason": request.reason,
                    "args": request.args,
                    "actor": "agent",
                    "move": final_state.get("last_move"),
                }
            ]
            final_turn_number = current_turn + 1
            final_state["turn_number"] = final_turn_number
            if not final_state["game_over"]:
                final_state = plugin.opponent_step(final_state)
                final_state["turn_number"] = final_turn_number
                if final_state.get("last_move", {}).get("player") == "opponent":
                    events_for_turn.append(
                        {
                            "type": "opponent_step",
                            "actor": "opponent",
                            "move": final_state["last_move"],
                        }
                    )
            self.session_store.write_turn_snapshot(
                session_id=request.session_id,
                turn_number=final_turn_number,
                canonical_state=final_state,
                agent_view=plugin.generate_agent_view(final_state),
                human_view=plugin.generate_human_view(final_state),
                events_for_turn=events_for_turn,
            )
            turn_advanced = True
        elif not is_action:
            final_state = deepcopy(new_state)

        response = self._response(
            ok=(code == OK),
            code=code,
            message=message,
            data=result_data,
            turn_advanced=turn_advanced,
            turn_number=final_turn_number if turn_advanced else current_turn,
            game_over=final_state["game_over"],
            winner=final_state["winner"],
            session_id=request.session_id,
        )
        self._log(
            request.session_id,
            {
                "request": request_payload,
                "response": response,
                "pre_hash": pre_hash,
                "post_hash": state_hash(final_state if turn_advanced else state),
                "turn_advanced": turn_advanced,
                "turn_number": response["turn_number"],
            },
        )
        return response
