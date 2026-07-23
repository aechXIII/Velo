"""Config typing helpers.

Runtime config is still a JSON-shaped dict (loaded/saved as config.json).
ConfigMap documents that intent without pretending every key is always present.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, MutableMapping

# Snapshot / patch maps. Keys and defaults are defined in velo.defaults.DEFAULTS.
ConfigMap = Dict[str, Any]
ConfigView = Mapping[str, Any]
ConfigPatch = MutableMapping[str, Any]
