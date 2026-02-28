"""Deterministic local Tic-Tac-Toe plugin."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from agent_games.protocol.errors import GAME_OVER, INVALID_ARGS, INVALID_MOVE, OK


Board = List[List[str]]


class Plugin:
    def __init__(self) -> None:
        manifest_path = Path(__file__).with_name("plugin.json")
        self._manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    def manifest(self) -> Dict[str, Any]:
        return deepcopy(self._manifest)

    def initialize(self, options: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "board": [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]],
            "agent_token": "X",
            "opponent_token": "O",
            "next_player": "agent",
            "turn_number": 0,
            "game_over": False,
            "winner": None,
            "last_move": None,
        }

    def is_action(self, command: str) -> bool:
        return command == "move"

    def execute(
        self,
        command: str,
        args: Dict[str, Any],
        state: Dict[str, Any],
        request_meta: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Dict[str, Any], str, str, bool]:
        if command == "rules":
            return (
                {
                    "rules": "Place three of your marks in a row. The agent plays X and moves first.",
                    "reason_echo": request_meta["reason"],
                },
                state,
                OK,
                "Rules retrieved",
                False,
            )

        if command in {"status", "agent_view"}:
            return (
                self.generate_agent_view(state),
                state,
                OK,
                "Status retrieved",
                False,
            )

        if command != "move":
            return ({}, state, INVALID_ARGS, f"Unexpected command '{command}'", False)

        if state["game_over"]:
            return ({}, state, GAME_OVER, "Game is already over", False)
        if state["next_player"] != "agent":
            return ({}, state, INVALID_MOVE, "It is not the agent's turn", False)

        x = args.get("x")
        y = args.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            return ({}, state, INVALID_ARGS, "Move requires integer x and y", False)
        if x not in range(3) or y not in range(3):
            return ({}, state, INVALID_MOVE, "Move is out of range", False)
        if state["board"][y][x] != " ":
            return ({}, state, INVALID_MOVE, "Cell is already occupied", False)

        next_state = deepcopy(state)
        next_state["board"][y][x] = next_state["agent_token"]
        next_state["last_move"] = {"player": "agent", "token": next_state["agent_token"], "x": x, "y": y}

        winner = _winner_for_board(next_state["board"], next_state["agent_token"], next_state["opponent_token"])
        if winner is not None:
            next_state["game_over"] = True
            next_state["winner"] = winner
            next_state["next_player"] = "agent"
        elif _board_full(next_state["board"]):
            next_state["game_over"] = True
            next_state["winner"] = "draw"
            next_state["next_player"] = "agent"
        else:
            next_state["next_player"] = "opponent"

        return (
            self.generate_agent_view(next_state),
            next_state,
            OK,
            "Move applied",
            True,
        )

    def opponent_step(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if state["game_over"] or state["next_player"] != "opponent":
            return state

        next_state = deepcopy(state)
        move = _choose_opponent_move(next_state["board"], next_state["agent_token"], next_state["opponent_token"])
        if move is None:
            next_state["game_over"] = True
            next_state["winner"] = "draw"
            next_state["next_player"] = "agent"
            return next_state

        x, y = move
        next_state["board"][y][x] = next_state["opponent_token"]
        next_state["last_move"] = {
            "player": "opponent",
            "token": next_state["opponent_token"],
            "x": x,
            "y": y,
        }

        winner = _winner_for_board(next_state["board"], next_state["agent_token"], next_state["opponent_token"])
        if winner is not None:
            next_state["game_over"] = True
            next_state["winner"] = winner
        elif _board_full(next_state["board"]):
            next_state["game_over"] = True
            next_state["winner"] = "draw"
        else:
            next_state["next_player"] = "agent"
            return next_state

        next_state["next_player"] = "agent"
        return next_state

    def generate_agent_view(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "board": deepcopy(state["board"]),
            "next_player": state["next_player"],
            "game_over": state["game_over"],
            "winner": state["winner"],
            "last_move": deepcopy(state["last_move"]),
            "turn_number": state["turn_number"],
        }

    def generate_human_view(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "board": deepcopy(state["board"]),
            "rendered_board": _render_board(state["board"]),
            "next_player": state["next_player"],
            "game_over": state["game_over"],
            "winner": state["winner"],
            "last_move": deepcopy(state["last_move"]),
            "turn_number": state["turn_number"],
        }


def _render_board(board: Board) -> str:
    return "\n".join(" | ".join(row) for row in board)


def _lines(board: Board) -> Iterable[List[str]]:
    for row in board:
        yield row
    for column_index in range(3):
        yield [board[row_index][column_index] for row_index in range(3)]
    yield [board[0][0], board[1][1], board[2][2]]
    yield [board[0][2], board[1][1], board[2][0]]


def _winner_for_board(board: Board, agent_token: str, opponent_token: str) -> Optional[str]:
    for line in _lines(board):
        if all(cell == agent_token for cell in line):
            return "agent"
        if all(cell == opponent_token for cell in line):
            return "opponent"
    return None


def _board_full(board: Board) -> bool:
    return all(cell != " " for row in board for cell in row)


def _empty_cells(board: Board) -> List[Tuple[int, int]]:
    return [(x, y) for y in range(3) for x in range(3) if board[y][x] == " "]


def _find_winning_move(board: Board, token: str) -> Optional[Tuple[int, int]]:
    for x, y in _empty_cells(board):
        probe = deepcopy(board)
        probe[y][x] = token
        if any(all(cell == token for cell in line) for line in _lines(probe)):
            return (x, y)
    return None


def _choose_opponent_move(board: Board, agent_token: str, opponent_token: str) -> Optional[Tuple[int, int]]:
    winning_move = _find_winning_move(board, opponent_token)
    if winning_move is not None:
        return winning_move

    blocking_move = _find_winning_move(board, agent_token)
    if blocking_move is not None:
        return blocking_move

    if board[1][1] == " ":
        return (1, 1)

    for move in ((0, 0), (2, 0), (0, 2), (2, 2)):
        x, y = move
        if board[y][x] == " ":
            return move

    for move in ((1, 0), (0, 1), (2, 1), (1, 2)):
        x, y = move
        if board[y][x] == " ":
            return move

    return None
