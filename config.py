"""Configuration loading and repository path resolution."""
from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml


def repo_root() -> Path:
    """Locate the project root (the folder that holds ``configs`` and ``data``)."""
    env = os.environ.get("ZONEMIND_HOME")
    if env:
        return Path(env).resolve()
    cwd = Path.cwd()
    if (cwd / "configs" / "default.yaml").exists():
        return cwd
    return Path(__file__).resolve().parents[2]


class Config(dict):
    """A dictionary with attribute access, so ``cfg.sim.dt_seconds`` reads naturally."""

    def __getattr__(self, key: str) -> Any:
        try:
            value = self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc
        return value

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value

    def __deepcopy__(self, memo: dict) -> "Config":
        return _wrap(copy.deepcopy(dict(self), memo))


def _wrap(obj: Any) -> Any:
    if isinstance(obj, dict):
        return Config({k: _wrap(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_wrap(v) for v in obj]
    return obj


def _merge(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def load_config(path: str | Path | None = None, overrides: dict | None = None) -> Config:
    """Load the default configuration, then layer an optional file and overrides on top."""
    root = repo_root()
    with open(root / "configs" / "default.yaml", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    path = path or os.environ.get("ZONEMIND_CONFIG")
    if path is not None:
        with open(path, encoding="utf-8") as fh:
            _merge(data, yaml.safe_load(fh) or {})
    if overrides:
        _merge(data, copy.deepcopy(overrides))
    return _wrap(data)
