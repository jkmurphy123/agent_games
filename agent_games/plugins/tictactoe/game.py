
class Plugin:

    def initialize(self):
        return {
            "board": [[" "]*3 for _ in range(3)],
            "game_over": False,
            "winner": None
        }

    def execute(self, command, args, state):
        if command == "rules":
            return ({"rules": "3 in a row wins."}, state)

        if command == "status":
            return ({"board": state["board"]}, state)

        if command == "move":
            x = args.get("x")
            y = args.get("y")
            if state["board"][y][x] != " ":
                return ({"error": "Invalid move"}, state)
            state["board"][y][x] = "X"
            return ({"board": state["board"]}, state)

        return ({"error": "Unknown command"}, state)
