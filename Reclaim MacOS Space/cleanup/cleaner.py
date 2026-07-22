"""Safe deletion and command execution for approved categories only."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from cleanup.categories import (
    ActionType,
    CleanupCategory,
    get_category,
)
from cleanup import special

SPECIAL_CLEANERS = {
    "xcode_device_support_old": special.clean_old_device_support,
    "docker_unused": special.clean_docker,
    "maui_xamarin_caches": special.clean_maui_xamarin_paths,
}


@dataclass
class CleanResult:
    id: str
    success: bool
    message: str
    freed_bytes: int = 0


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _validate_delete_path(path: Path, category: CleanupCategory) -> None:
    resolved = path.expanduser().resolve()
    allowed = False
    for allowed_path in category.paths:
        candidate = allowed_path.expanduser()
        target = candidate.resolve() if candidate.exists() else candidate
        if resolved == target or _is_under(resolved, target):
            allowed = True
            break
        if target == resolved or _is_under(target, resolved):
            allowed = True
            break

    if not allowed:
        raise PermissionError(f"Refusing to delete path outside category allowlist: {path}")

    protected = {Path.home().resolve(), Path("/").resolve()}
    if resolved in protected:
        raise PermissionError(f"Refusing to delete protected path: {path}")


def delete_path_contents(path: Path, category: CleanupCategory, *, use_sudo: bool = False) -> tuple[int, str]:
    path = path.expanduser()
    _validate_delete_path(path, category)

    if not path.exists():
        return 0, f"Already absent: {path}"

    from cleanup.fsutil import dir_size

    before = dir_size(path)

    if category.requires_sudo:
        if not use_sudo:
            return 0, f"Skipped — admin required for {path}"
        import shlex

        shell_cmd = f"find {shlex.quote(str(path.resolve()))} -mindepth 1 -maxdepth 1 -exec rm -rf {{}} +"
        result = _run_with_admin_prompt(shell_cmd)
        if result.returncode != 0:
            output = (result.stdout or result.stderr or "").strip()
            return 0, output or f"Failed to clear {path}"
        return before, f"Cleared contents of {path}"

    if path.is_file():
        path.unlink()
        return before, f"Removed file {path}"

    for entry in list(path.iterdir()):
        child = entry
        _validate_delete_path(child, category)
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink(missing_ok=True)

    return before, f"Cleared contents of {path}"


def delete_path_tree(path: Path, category: CleanupCategory) -> tuple[int, str]:
    path = path.expanduser()
    _validate_delete_path(path, category)

    if not path.exists():
        return 0, f"Already absent: {path}"

    from cleanup.fsutil import dir_size

    before = dir_size(path)
    shutil.rmtree(path)
    return before, f"Removed {path}"


CONTENT_ONLY_CATEGORIES = frozenset({"ios_device_backups", "user_logs", "system_caches"})


def _run_with_admin_prompt(shell_command: str) -> subprocess.CompletedProcess[str]:
    script = f'do shell script "{shell_command.replace(chr(34), chr(92) + chr(34))}" with administrator privileges'
    return subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )


def run_command(category: CleanupCategory, use_sudo: bool) -> tuple[int, str]:
    if not category.command:
        return 0, "No command configured"

    import shlex

    cmd = list(category.command)
    shell_cmd = " ".join(shlex.quote(part) for part in cmd)

    try:
        if category.requires_sudo:
            if not use_sudo:
                return 0, "Skipped — enable admin operations to run this step"
            result = _run_with_admin_prompt(shell_cmd)
        else:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=600,
            )
    except subprocess.TimeoutExpired:
        return 0, "Command timed out"
    except FileNotFoundError:
        return 0, f"Command not found: {cmd[0]}"

    output = (result.stdout or result.stderr or "").strip()
    if result.returncode != 0:
        return 0, output or f"Command failed (exit {result.returncode})"

    return 0, output or "Command completed successfully"


def clean_category(category_id: str, *, use_sudo: bool = False) -> CleanResult:
    category = get_category(category_id)
    if category is None:
        return CleanResult(category_id, False, "Unknown category")

    freed = 0
    messages: list[str] = []

    try:
        if category.action == ActionType.SPECIAL:
            handler = SPECIAL_CLEANERS.get(category.id)
            if handler is None:
                return CleanResult(category.id, False, "Unknown special handler")
            freed, message = handler()
            ok = "failed" not in message.lower() and "not running" not in message.lower()
            return CleanResult(category.id, ok, message, freed)

        if category.action == ActionType.RUN_COMMAND:
            freed, message = run_command(category, use_sudo=use_sudo)
            messages.append(message)
            ok = "failed" not in message.lower() and "skipped" not in message.lower()
            return CleanResult(category.id, ok, "; ".join(messages), freed)

        for path in category.paths:
            if not path.expanduser().exists():
                messages.append(f"Skipped missing {path}")
                continue

            if category.id in CONTENT_ONLY_CATEGORIES:
                amount, message = delete_path_contents(path, category, use_sudo=use_sudo)
            else:
                amount, message = delete_path_tree(path, category)

            freed += amount
            messages.append(message)

        return CleanResult(
            category.id,
            True,
            "; ".join(messages) if messages else "Nothing to do",
            freed,
        )
    except Exception as exc:  # noqa: BLE001 — surface safe errors to UI
        return CleanResult(category.id, False, str(exc), freed)
