# AGENTGAMES_TASK.md — Play Tic-Tac-Toe via AgentGames (Local CLI)

## Objective
Use the **local** `agent-games` CLI to **register** and **play one complete game** of Tic-Tac-Toe until `game_over == true`.

You are playing as the **agent** (typically token `X`). The plugin plays the opponent.

---

## Critical Rules of Engagement

### 1) Every request MUST include `reason`
Every single command call must include a non-empty string field:

- `reason`: why you are making this call

If `reason` is missing, the framework will reject the request.

### 2) Use the dispatcher CLI for every command
All interaction happens through:

- `agent-games dispatch --request <JSON_STRING>`

### 3) Session handling
- `register` is the only command allowed without a `session_id`.
- Save the returned `session_id` and include it in all subsequent requests.

### 4) Turn semantics
- QUERY commands (e.g., `rules`, `status`, `agent_view`, `schema`, `ping`, `latest`, `view`, `history`) **do not** advance the turn.
- ACTION commands (e.g., `move`) **advance the turn only on success**.
- After a successful `move`, the framework may automatically run the opponent step and persist the resulting state for that turn.

---

## Required Success Condition
You succeed when you can show a final response (via `latest` or `status`) where:

- `game_over` is `true`
- `winner` is one of: `"agent"`, `"opponent"`, `"draw"`

After the game ends, also call `history` to demonstrate that turn snapshots exist.

---

## Standard Command Set (v1)
Assume the framework supports these standard commands:

- `register`, `reset`, `quit`
- `rules`, `status`, `agent_view`, `schema`, `ping`
- `move`
- `history`, `view`, `latest`

If a command returns `NOT_SUPPORTED`, do not treat it as fatal; adapt and continue.

---

## Recommended Play Loop (High Level)

### Step A — Register
Call `register` with:
- `agent_id` (any stable identifier, e.g. `"claw"`)
- `args.plugin_id` = `"tictactoe"`

Store `session_id`.

### Step B — Learn rules + schema (optional but recommended)
Call:
- `schema` (learn supported commands)
- `rules`

### Step C — Play until done
Loop:
1) Call `status` (or `agent_view`) to obtain:
   - the board
   - legal moves (if provided)
   - whether it’s your turn
   - whether game is over
2) If game over: stop loop.
3) Choose a legal move `(x,y)` and call `move`.
4) If you get `INVALID_MOVE`, call `status` again, pick a different move, and retry.

### Step D — Show replay evidence
Call:
- `latest` (to show the final snapshot)
- `history` (to list available turns)
- optionally `view` with a specific `turn_number`

---

## Practical Windows Advice (PowerShell JSON)
Inline JSON quoting can be annoying. Prefer **single quotes** around the JSON:

Example:
```powershell
agent-games dispatch --request '{ "agent_id":"claw", "command":"register", "args":{"plugin_id":"tictactoe"}, "reason":"Start a new game" }'
```

If inline JSON becomes painful, use a file:

```powershell
# request.json contains the JSON payload
agent-games dispatch --request (Get-Content .\request.json -Raw)
```

---

## Concrete Examples (Templates)

### 1) Register
```json
{
  "agent_id": "claw",
  "command": "register",
  "args": { "plugin_id": "tictactoe" },
  "reason": "Start a new Tic-Tac-Toe game"
}
```

### 2) Rules
```json
{
  "session_id": "<SESSION_ID>",
  "agent_id": "claw",
  "command": "rules",
  "args": {},
  "reason": "Learn the rules and coordinate system"
}
```

### 3) Status
```json
{
  "session_id": "<SESSION_ID>",
  "agent_id": "claw",
  "command": "status",
  "args": {},
  "reason": "Inspect the board and decide the next move"
}
```

### 4) Move (place token at x,y)
```json
{
  "session_id": "<SESSION_ID>",
  "agent_id": "claw",
  "command": "move",
  "args": { "x": 1, "y": 1 },
  "reason": "Take the center to maximize winning chances"
}
```

### 5) Latest snapshot
```json
{
  "session_id": "<SESSION_ID>",
  "agent_id": "claw",
  "command": "latest",
  "args": {},
  "reason": "Retrieve the most recent snapshot for reporting"
}
```

### 6) History (list turns)
```json
{
  "session_id": "<SESSION_ID>",
  "agent_id": "claw",
  "command": "history",
  "args": {},
  "reason": "Confirm that turn snapshots exist for replay"
}
```

### 7) View a specific turn
```json
{
  "session_id": "<SESSION_ID>",
  "agent_id": "claw",
  "command": "view",
  "args": { "turn": 2 },
  "reason": "Render a specific turn for human review"
}
```

---

## Error Handling Guidance
- `NOT_REGISTERED`: You lost/forgot the session_id. Re-register.
- `INVALID_ARGS`: Fix your JSON fields/types.
- `INVALID_MOVE`: Pick a different (x,y). Do NOT expect the turn to advance.
- `NOT_SUPPORTED`: Use `schema` to see what is supported and continue with available commands.
- `UNKNOWN_COMMAND`: You used a command name not in the protocol vocabulary.

---

## Completion Report (What to output at the end)
When done, provide:

1) Final `latest` response JSON
2) `history` response JSON
3) A short explanation of your play strategy (1–3 sentences)
