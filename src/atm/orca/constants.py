"""
SRF constants — large data dictionaries loaded from YAML.

These are pure data (no code logic) extracted from the monolith.
The original monolith uses accented strings as dictionary keys
(matching the CT317 Excel source). This file preserves the EXACT original
keys to maintain lookup correctness. Do NOT normalize accents on keys.
"""

import os
from pathlib import Path

# Lazy-loaded constants
_DEPARA = None
_CT317_HH = None
_COMPARATIVO = None
_FASE_CORES = None


def _load_constants():
    """Load constants from YAML on first access."""
    global _DEPARA, _CT317_HH, _COMPARATIVO, _FASE_CORES
    if _DEPARA is not None:
        return

    yaml_path = Path(__file__).with_name("constants.yaml")
    if not yaml_path.exists():
        raise FileNotFoundError(f"Constants YAML not found at {yaml_path}")

    import yaml
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    _DEPARA = data["DEFAULT_DEPARA_EXAME_CT317"]
    _CT317_HH = data["CT317_HARDCODE_HH_BASE"]
    _COMPARATIVO = data["COMPARATIVO_MANUAL_MEC"]
    _FASE_CORES = data["_FASE_CORES_HEX"]


# Public API — backward compatible (dict-like access)
def _ensure_loaded():
    if _DEPARA is None:
        _load_constants()


# Module-level dict proxies for backward compatibility
class _LazyDict(dict):
    def __init__(self, loader_name):
        self._loader_name = loader_name
        super().__init__()

    def __getitem__(self, key):
        _ensure_loaded()
        source = globals()[f"_{self._loader_name}"]
        return source[key]

    def __contains__(self, key):
        _ensure_loaded()
        source = globals()[f"_{self._loader_name}"]
        return key in source

    def get(self, key, default=None):
        _ensure_loaded()
        source = globals()[f"_{self._loader_name}"]
        return source.get(key, default)

    def items(self):
        _ensure_loaded()
        source = globals()[f"_{self._loader_name}"]
        return source.items()

    def keys(self):
        _ensure_loaded()
        source = globals()[f"_{self._loader_name}"]
        return source.keys()

    def values(self):
        _ensure_loaded()
        source = globals()[f"_{self._loader_name}"]
        return source.values()

    def __len__(self):
        _ensure_loaded()
        source = globals()[f"_{self._loader_name}"]
        return len(source)

    def __iter__(self):
        _ensure_loaded()
        source = globals()[f"_{self._loader_name}"]
        return iter(source)

    def __repr__(self):
        _ensure_loaded()
        source = globals()[f"_{self._loader_name}"]
        return repr(source)

    def __str__(self):
        _ensure_loaded()
        source = globals()[f"_{self._loader_name}"]
        return str(source)

    def copy(self):
        _ensure_loaded()
        source = globals()[f"_{self._loader_name}"]
        return source.copy()

    def update(self, *args, **kwargs):
        _ensure_loaded()
        source = globals()[f"_{self._loader_name}"]
        return source.update(*args, **kwargs)


# Create lazy dict proxies
DEFAULT_DEPARA_EXAME_CT317 = _LazyDict("DEPARA")
CT317_HARDCODE_HH_BASE = _LazyDict("CT317_HH")
COMPARATIVO_MANUAL_MEC = _LazyDict("COMPARATIVO")
_FASE_CORES_HEX = _LazyDict("FASE_CORES")