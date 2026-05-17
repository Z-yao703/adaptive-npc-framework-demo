"""
Simple ASCII-safe logging helpers for Windows terminals.
"""

from __future__ import annotations

from typing import Any


def log_info(message: str, *args: Any) -> None:
    _print("INFO", message, *args)


def log_warn(message: str, *args: Any) -> None:
    _print("WARN", message, *args)


def log_error(message: str, *args: Any) -> None:
    _print("ERROR", message, *args)


def _print(level: str, message: str, *args: Any) -> None:
    if args:
        message = message.format(*args)
    print(f"[{level}] {message}")
