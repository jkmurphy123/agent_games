
import importlib
import os

def load_plugins():
    plugins = {}
    base = "agent_games.plugins"
    for name in os.listdir(os.path.dirname(__file__) + "/plugins"):
        if name == "__pycache__":
            continue
        try:
            module = importlib.import_module(f"{base}.{name}.game")
            plugins[name] = module.Plugin()
        except Exception:
            continue
    return plugins
