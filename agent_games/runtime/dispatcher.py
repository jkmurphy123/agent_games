
from agent_games.protocol.models import Response
from agent_games.protocol.errors import NOT_SUPPORTED, OK
import uuid

class Dispatcher:

    def __init__(self, plugins):
        self.plugins = plugins
        self.sessions = {}

    def dispatch(self, request):
        cmd = request.get("command")
        plugin_id = request.get("plugin_id", "tictactoe")

        if cmd == "register":
            session_id = str(uuid.uuid4())
            plugin = self.plugins[plugin_id]
            state = plugin.initialize()
            self.sessions[session_id] = {
                "plugin": plugin,
                "state": state,
                "turn": 0
            }
            return Response(
                ok=True,
                code=OK,
                message="Registered",
                data={},
                turn_advanced=False,
                turn_number=0,
                game_over=False,
                winner=None,
                session_id=session_id
            ).dict()

        session_id = request.get("session_id")
        session = self.sessions.get(session_id)
        if not session:
            return Response(
                ok=False,
                code="NOT_REGISTERED",
                message="Invalid session",
                data={},
                turn_advanced=False,
                turn_number=0,
                game_over=False,
                winner=None,
                session_id=session_id
            ).dict()

        plugin = session["plugin"]
        if not hasattr(plugin, "execute"):
            return Response(
                ok=False,
                code=NOT_SUPPORTED,
                message="Command not supported",
                data={},
                turn_advanced=False,
                turn_number=session["turn"],
                game_over=False,
                winner=None,
                session_id=session_id
            ).dict()

        result, new_state = plugin.execute(cmd, request.get("args", {}), session["state"])
        session["state"] = new_state

        return Response(
            ok=True,
            code=OK,
            message="Success",
            data=result,
            turn_advanced=False,
            turn_number=session["turn"],
            game_over=new_state.get("game_over", False),
            winner=new_state.get("winner"),
            session_id=session_id
        ).dict()
