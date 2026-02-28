
"""CLI entrypoint for AgentGames."""

from __future__ import annotations

import argparse
import json
from typing import Optional

from agent_games.registry import load_plugins
from agent_games.runtime.dispatcher import Dispatcher


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="agent-games")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-plugins")
    dispatch_parser = subparsers.add_parser("dispatch")
    dispatch_parser.add_argument("--request", required=True, help="JSON request string")

    args = parser.parse_args(argv)

    plugins = load_plugins()
    dispatcher = Dispatcher(plugins)

    if args.command == "list-plugins":
        print(json.dumps(sorted(plugins.keys()), indent=2))
        return 0

    request = json.loads(args.request)
    response = dispatcher.dispatch(request)
    print(json.dumps(response, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
