"""Obsidian Hermes deterministic bridge kernel."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("obsidian-hermes")
except PackageNotFoundError:  # pragma: no cover - source tree without installation
    __version__ = "0.1.0a0"

__all__ = ["__version__"]
