
import argparse
import json
from agent_games.runtime.dispatcher import Dispatcher
from agent_games.registry import load_plugins

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["list-plugins", "dispatch"])
    parser.add_argument("--request", help="JSON request string")
    args = parser.parse_args()

    plugins = load_plugins()
    dispatcher = Dispatcher(plugins)

    if args.command == "list-plugins":
        print(json.dumps(list(plugins.keys()), indent=2))
    elif args.command == "dispatch":
        req = json.loads(args.request)
        resp = dispatcher.dispatch(req)
        print(json.dumps(resp, indent=2))
