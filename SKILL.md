---
name: agent-games
description: Skill for interacting with the local AgentGames CLI framework.
---

# AgentGames Skill

This skill teaches the agent how to interact with the **local** `agent-games` CLI dispatcher.

All communication with the game framework must occur via:

    agent-games dispatch --request <JSON>

You must always send a valid JSON request string.

---

# Universal Rules

1. Every request MUST include:
   - agent_id
   - command
   - args (object, may be empty)
   - reason (non-empty string explaining why you are making the call)

2. Only `register` may be sent without `session_id`.

3. Save the returned `session_id` and reuse it for all future calls.

4. If a command fails with:
   - INVALID_MOVE → choose another move and retry
   - NOT_SUPPORTED → call `schema` to inspect available commands
   - UNKNOWN_COMMAND → correct the command name
   - NOT_REGISTERED → re-register

---

# PowerShell JSON Best Practice (Windows)

Prefer single quotes around JSON:

    agent-games dispatch --request '{ "agent_id":"claw", "command":"register", "args":{"plugin_id":"tictactoe"}, "reason":"Start game" }'

If quoting becomes complex, use a temporary file:

    agent-games dispatch --request (Get-Content .\request.json -Raw)

---

# Common Command Templates

## Register

{
  "agent_id": "claw",
  "command": "register",
  "args": { "plugin_id": "tictactoe" },
  "reason": "Start a new game"
}

## Rules

{
  "session_id": "<SESSION_ID>",
  "agent_id": "claw",
  "command": "rules",
  "args": {},
  "reason": "Understand rules before playing"
}

## Status

{
  "session_id": "<SESSION_ID>",
  "agent_id": "claw",
  "command": "status",
  "args": {},
  "reason": "Inspect board and decide next move"
}

## Move

{
  "session_id": "<SESSION_ID>",
  "agent_id": "claw",
  "command": "move",
  "args": { "x": 1, "y": 1 },
  "reason": "Strategic placement"
}

## Latest Snapshot

{
  "session_id": "<SESSION_ID>",
  "agent_id": "claw",
  "command": "latest",
  "args": {},
  "reason": "Retrieve current snapshot"
}

## History

{
  "session_id": "<SESSION_ID>",
  "agent_id": "claw",
  "command": "history",
  "args": {},
  "reason": "Review turn history"
}

---

# Recommended Game Loop

1. Register session.
2. Call rules.
3. Loop:
   - Call status.
   - If game_over is true → stop.
   - Choose legal move.
   - Call move.
4. After completion:
   - Call latest.
   - Call history.

---

# Strategic Guidance (Tic-Tac-Toe)

Preferred move priority:

1. Win if possible.
2. Block opponent win.
3. Take center.
4. Take corner.
5. Take side.

Always confirm legal moves via status before choosing.

---

End of Skill.
