"""Special cleanup handlers (old-only deletes, Docker, etc.)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from cleanup.fsutil import dir_size, format_bytes

DEVICE_SUPPORT_ROOT = Path.home() / "Library/Developer/Xcode/iOS DeviceSupport"
KEEP_DEVICE_SUPPORT = 2


def _device_support_entries() -> list[Path]:
    if not DEVICE_SUPPORT_ROOT.is_dir():
        return []
    return [p for p in DEVICE_SUPPORT_ROOT.iterdir() if p.is_dir() and not p.is_symlink()]


def _sort_device_support(entries: list[Path]) -> list[Path]:
    return sorted(entries, key=lambda p: p.stat().st_mtime, reverse=True)


def old_device_support_targets() -> list[Path]:
    entries = _sort_device_support(_device_support_entries())
    if len(entries) <= KEEP_DEVICE_SUPPORT:
        return []
    return entries[KEEP_DEVICE_SUPPORT:]


def scan_old_device_support() -> tuple[int, str, list[str]]:
    targets = old_device_support_targets()
    total = sum(dir_size(path) for path in targets)
    kept = _sort_device_support(_device_support_entries())[:KEEP_DEVICE_SUPPORT]
    if not targets:
        detail = (
            f"Nothing old to remove (keeping {len(kept)} newest folder(s))"
            if kept
            else "No DeviceSupport folders found"
        )
        return 0, detail, []
    detail = f"Remove {len(targets)} old folder(s), keep {len(kept)} newest"
    return total, detail, [str(p) for p in targets]


def clean_old_device_support() -> tuple[int, str]:
    freed = 0
    removed: list[str] = []
    for path in old_device_support_targets():
        size = dir_size(path)
        shutil.rmtree(path)
        freed += size
        removed.append(path.name)
    if not removed:
        return 0, "No old DeviceSupport folders to remove"
    return freed, f"Removed {len(removed)} old folder(s): {', '.join(removed[:5])}"


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def scan_docker() -> tuple[int, str, list[str]]:
    if not _docker_available():
        return 0, "Docker not installed", []

    try:
        result = subprocess.run(
            ["docker", "system", "df", "--format", "{{.Type}}\t{{.TotalCount}}\t{{.Size}}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return 0, "Could not inspect Docker", []

    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        if "Cannot connect" in err or "Is the docker daemon running" in err.lower():
            return 0, "Docker installed but not running — start Docker Desktop first", []
        return 0, err or "Docker inspect failed", []

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    reclaimable = [line for line in lines if "Reclaimable" not in line]
    detail = "; ".join(reclaimable[:4]) if reclaimable else "Docker data present"
    return 0, detail, ["docker system prune", "docker builder prune"]


def clean_docker() -> tuple[int, str]:
    if not _docker_available():
        return 0, "Docker not installed"

    messages: list[str] = []
    for cmd in (
        ["docker", "builder", "prune", "-af"],
        ["docker", "system", "prune", "-af"],
    ):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=600,
            )
        except subprocess.SubprocessError:
            return 0, "Docker cleanup timed out"

        label = cmd[1] + " " + cmd[2]
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            if "Cannot connect" in err:
                return 0, "Docker is not running"
            return 0, err or f"{label} failed"

        line = (result.stdout or result.stderr or "").strip().splitlines()
        messages.append(line[-1] if line else f"{label} done")

    return 0, "; ".join(messages)


def scan_maui_xamarin_extra() -> tuple[int, list[str]]:
    """Scan paths not covered by generic android/dotnet categories."""
    paths = maui_xamarin_paths()
    existing = [p for p in paths if p.exists()]
    total = sum(dir_size(p) for p in existing)
    return total, [str(p) for p in existing]


def maui_xamarin_paths() -> list[Path]:
    home = Path.home()
    return [
        home / "Library/Caches/Xamarin",
        home / "Library/Caches/com.microsoft.visualstudio",
        home / "Library/Developer/Xamarin",
        home / ".local/share/Xamarin",
        home / ".android/build-cache",
        home / "Library/Logs/Xamarin",
        home / "Library/Logs/MonoDevelop",
    ]


def clean_maui_xamarin_paths() -> tuple[int, str]:
    freed = 0
    cleaned: list[str] = []
    for path in maui_xamarin_paths():
        if not path.exists():
            continue
        size = dir_size(path)
        if path.name in {"Xamarin", "MonoDevelop"} and path.parent.name == "Logs":
            for child in list(path.iterdir()):
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink(missing_ok=True)
        else:
            shutil.rmtree(path)
        freed += size
        cleaned.append(str(path))
    if not cleaned:
        return 0, "No MAUI/Xamarin caches found"
    return freed, f"Cleared {len(cleaned)} path(s), freed ~{format_bytes(freed)}"
