"""Scan cleanup targets and report reclaimable space."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from cleanup.fsutil import dir_size, format_bytes
from cleanup.categories import CATEGORIES, ActionType, CleanupCategory
from cleanup import special


def _scan_maui_xamarin() -> tuple[int, str, list[str]]:
    total, paths = special.scan_maui_xamarin_extra()
    detail = f"{len(paths)} path(s) found" if paths else "Nothing to clean"
    return total, detail, paths


SPECIAL_SCANNERS = {
    "xcode_device_support_old": special.scan_old_device_support,
    "docker_unused": special.scan_docker,
    "maui_xamarin_caches": _scan_maui_xamarin,
}


@dataclass
class ScanResult:
    id: str
    name: str
    description: str
    risk: str
    requires_sudo: bool
    warning: str | None
    available: bool
    size_bytes: int
    size_human: str
    detail: str
    paths: list[str]


def snapshot_size_hint() -> tuple[int, str]:
    try:
        result = subprocess.run(
            ["tmutil", "listlocalsnapshots", "/"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        count = len(lines)
        if count == 0:
            return 0, "No local snapshots found"
        return 0, f"{count} local snapshot(s) — size requires admin cleanup to reclaim"
    except (subprocess.SubprocessError, FileNotFoundError):
        return 0, "Time Machine tools unavailable"


def scan_category(category: CleanupCategory) -> ScanResult:
    if category.exists_check is not None and not category.exists_check():
        return ScanResult(
            id=category.id,
            name=category.name,
            description=category.description,
            risk=category.risk.value,
            requires_sudo=category.requires_sudo,
            warning=category.warning,
            available=False,
            size_bytes=0,
            size_human="0 B",
            detail="Tool not installed on this Mac",
            paths=[str(p) for p in category.paths],
        )

    if category.action == ActionType.SPECIAL:
        scanner = SPECIAL_SCANNERS.get(category.id)
        if scanner is None:
            return ScanResult(
                id=category.id,
                name=category.name,
                description=category.description,
                risk=category.risk.value,
                requires_sudo=category.requires_sudo,
                warning=category.warning,
                available=False,
                size_bytes=0,
                size_human="0 B",
                detail="Unknown special handler",
                paths=[str(p) for p in category.paths],
            )
        total, detail, paths = scanner()
        if category.id == "docker_unused":
            unavailable = any(
                phrase in detail.lower()
                for phrase in ("not installed", "not running", "could not inspect", "inspect failed")
            )
            available = not unavailable
        else:
            available = bool(paths) or total > 0
        size_human = format_bytes(total) if total else ("Command" if category.id == "docker_unused" else "0 B")
        return ScanResult(
            id=category.id,
            name=category.name,
            description=category.description,
            risk=category.risk.value,
            requires_sudo=category.requires_sudo,
            warning=category.warning,
            available=available,
            size_bytes=total,
            size_human=size_human,
            detail=detail,
            paths=paths or [str(p) for p in category.paths],
        )

    if category.action == ActionType.RUN_COMMAND and category.id == "tm_local_snapshots":
        _size, detail = snapshot_size_hint()
        return ScanResult(
            id=category.id,
            name=category.name,
            description=category.description,
            risk=category.risk.value,
            requires_sudo=category.requires_sudo,
            warning=category.warning,
            available=True,
            size_bytes=0,
            size_human="Unknown",
            detail=detail,
            paths=[],
        )

    if category.action == ActionType.RUN_COMMAND:
        return ScanResult(
            id=category.id,
            name=category.name,
            description=category.description,
            risk=category.risk.value,
            requires_sudo=category.requires_sudo,
            warning=category.warning,
            available=True,
            size_bytes=0,
            size_human="Command",
            detail="Runs a cleanup command (no fixed folder size)",
            paths=[],
        )

    total = 0
    existing: list[str] = []
    for path in category.paths:
        if path.exists():
            total += dir_size(path)
            existing.append(str(path))

    return ScanResult(
        id=category.id,
        name=category.name,
        description=category.description,
        risk=category.risk.value,
        requires_sudo=category.requires_sudo,
        warning=category.warning,
        available=bool(existing) or category.action == ActionType.RUN_COMMAND,
        size_bytes=total,
        size_human=format_bytes(total),
        detail=f"{len(existing)} path(s) found" if existing else "Nothing to clean",
        paths=[str(p) for p in category.paths],
    )


def scan_all() -> list[ScanResult]:
    return [scan_category(category) for category in CATEGORIES]
