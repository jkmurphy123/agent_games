
"""Plugin discovery utilities."""

from __future__ import annotations

import importlib
import json
import warnings
from pathlib import Path
from typing import Dict


REQUIRED_PLUGIN_METHODS = (
    "manifest",
    "initialize",
    "is_action",
    "execute",
    "opponent_step",
    "generate_agent_view",
    "generate_human_view",
)


def _validate_plugin(plugin: object, manifest: dict) -> None:
    for method_name in REQUIRED_PLUGIN_METHODS:
        if not callable(getattr(plugin, method_name, None)):
            raise TypeError(f"missing required method: {method_name}")

    plugin_manifest = plugin.manifest()
    if not isinstance(plugin_manifest, dict):
        raise TypeError("manifest() must return a dictionary")
    if plugin_manifest.get("id") != manifest.get("id"):
        raise ValueError("manifest id does not match plugin.json")


def load_plugins() -> Dict[str, object]:
    plugins: Dict[str, object] = {}
    plugins_dir = Path(__file__).resolve().parent / "plugins"

    for manifest_path in sorted(plugins_dir.glob("*/plugin.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            plugin_id = manifest["id"]
            module_name = f"agent_games.plugins.{manifest_path.parent.name}.game"
            module = importlib.import_module(module_name)
            plugin = module.Plugin()
            _validate_plugin(plugin, manifest)
            plugins[plugin_id] = plugin
        except Exception as exc:
            warnings.warn(
                f"Skipping plugin at {manifest_path}: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )

    return plugins
