"""Shared filesystem helpers."""

from __future__ import annotations

import os
from pathlib import Path


def format_bytes(num: int) -> str:
    if num <= 0:
        return "0 B"
    units = ("B", "KB", "MB", "GB", "TB")
    size = float(num)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{num} B"


def dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0

    total = 0
    try:
        for root, _dirs, files in os.walk(path, followlinks=False):
            for name in files:
                file_path = Path(root) / name
                try:
                    total += file_path.stat().st_size
                except OSError:
                    continue
    except OSError:
        return 0
    return total
