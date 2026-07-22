"""Cleanup category definitions — only known-safe developer junk paths."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionType(str, Enum):
    DELETE_PATHS = "delete_paths"
    RUN_COMMAND = "run_command"
    SPECIAL = "special"


@dataclass(frozen=True)
class CleanupCategory:
    id: str
    name: str
    description: str
    risk: RiskLevel
    action: ActionType
    paths: tuple[Path, ...] = field(default_factory=tuple)
    command: tuple[str, ...] = field(default_factory=tuple)
    requires_sudo: bool = False
    warning: str | None = None
    exists_check: Callable[[], bool] | None = None


def _home() -> Path:
    return Path.home()


CATEGORIES: tuple[CleanupCategory, ...] = (
    CleanupCategory(
        id="xcode_derived_data",
        name="Xcode DerivedData",
        description="Build intermediates and indexes. Regenerated on the next build.",
        risk=RiskLevel.LOW,
        action=ActionType.DELETE_PATHS,
        paths=(_home() / "Library/Developer/Xcode/DerivedData",),
    ),
    CleanupCategory(
        id="xcode_archives",
        name="Xcode Archives",
        description="Old .xcarchive export bundles from Archive builds. Remove if you no longer need them for App Store uploads.",
        risk=RiskLevel.MEDIUM,
        action=ActionType.DELETE_PATHS,
        paths=(_home() / "Library/Developer/Xcode/Archives",),
        warning="You will lose archived builds. Re-archive from source if you still need them.",
    ),
    CleanupCategory(
        id="xcode_device_support_old",
        name="Old iOS DeviceSupport only",
        description="Removes outdated device symbol folders. Keeps the 2 most recently used versions.",
        risk=RiskLevel.LOW,
        action=ActionType.SPECIAL,
        paths=(_home() / "Library/Developer/Xcode/iOS DeviceSupport",),
    ),
    CleanupCategory(
        id="core_simulator",
        name="iOS Simulators (CoreSimulator)",
        description="Simulator runtimes, devices, and caches. Simulators are recreated when you run apps again.",
        risk=RiskLevel.MEDIUM,
        action=ActionType.DELETE_PATHS,
        paths=(_home() / "Library/Developer/CoreSimulator",),
        warning="All simulator devices and data will be removed.",
    ),
    CleanupCategory(
        id="nuget_packages",
        name="NuGet package cache",
        description="Downloaded NuGet packages under ~/.nuget/packages. Restored automatically on dotnet restore.",
        risk=RiskLevel.LOW,
        action=ActionType.DELETE_PATHS,
        paths=(_home() / ".nuget/packages",),
    ),
    CleanupCategory(
        id="dotnet_nuget_locals",
        name=".NET NuGet locals",
        description="Clears NuGet HTTP cache, temp, and global-packages via dotnet nuget locals all --clear.",
        risk=RiskLevel.LOW,
        action=ActionType.RUN_COMMAND,
        command=("dotnet", "nuget", "locals", "all", "--clear"),
        exists_check=lambda: _which("dotnet") is not None,
    ),
    CleanupCategory(
        id="android_avd",
        name="Android emulator images (AVD)",
        description="Emulator disk images in ~/.android/avd. Emulators can be recreated from AVD Manager.",
        risk=RiskLevel.MEDIUM,
        action=ActionType.DELETE_PATHS,
        paths=(_home() / ".android/avd",),
        warning="Emulator snapshots and virtual devices will be deleted.",
    ),
    CleanupCategory(
        id="android_build_cache",
        name="Android build caches",
        description="Gradle and Android Studio caches only — not your SDK or project files.",
        risk=RiskLevel.LOW,
        action=ActionType.DELETE_PATHS,
        paths=(
            _home() / ".gradle/caches",
            _home() / "Library/Caches/Google/AndroidStudio",
            _home() / "Library/Caches/Android",
        ),
    ),
    CleanupCategory(
        id="maui_xamarin_caches",
        name="MAUI / Xamarin caches",
        description=".NET mobile build caches: Xamarin, Visual Studio, MonoDevelop logs, and Android build-cache.",
        risk=RiskLevel.LOW,
        action=ActionType.SPECIAL,
        paths=(_home() / "Library/Caches/Xamarin",),
    ),
    CleanupCategory(
        id="docker_unused",
        name="Docker unused data",
        description="Removes stopped containers, dangling images, and build cache. Does not remove named volumes.",
        risk=RiskLevel.MEDIUM,
        action=ActionType.SPECIAL,
        command=("docker", "system", "prune", "-af"),
        exists_check=lambda: _which("docker") is not None,
        warning="Unused Docker images will be removed. Named volumes are kept; restart Docker Desktop first if it is not running.",
    ),
    CleanupCategory(
        id="ios_device_backups",
        name="iTunes / Finder iOS backups",
        description="Local iPhone/iPad backups in MobileSync. Does not touch iCloud backups.",
        risk=RiskLevel.HIGH,
        action=ActionType.DELETE_PATHS,
        paths=(_home() / "Library/Application Support/MobileSync/Backup",),
        warning="Local device backups will be permanently deleted. Ensure important backups are elsewhere.",
    ),
    CleanupCategory(
        id="developer_caches",
        name="Developer app caches",
        description="Caches from Xcode, SwiftPM, CocoaPods, npm, pip, yarn, and Homebrew — not all app caches.",
        risk=RiskLevel.LOW,
        action=ActionType.DELETE_PATHS,
        paths=(
            _home() / "Library/Caches/com.apple.dt.Xcode",
            _home() / "Library/Caches/org.swift.swiftpm",
            _home() / "Library/Caches/CocoaPods",
            _home() / "Library/Caches/pip",
            _home() / "Library/Caches/Yarn",
            _home() / "Library/Caches/Homebrew",
            _home() / "Library/Caches/node-gyp",
        ),
    ),
    CleanupCategory(
        id="user_logs",
        name="User logs",
        description="Application log files under ~/Library/Logs. Does not remove system logs.",
        risk=RiskLevel.LOW,
        action=ActionType.DELETE_PATHS,
        paths=(_home() / "Library/Logs",),
    ),
    CleanupCategory(
        id="tm_local_snapshots",
        name="Time Machine local snapshots",
        description="APFS local snapshots that inflate 'System Data'. Requires admin password.",
        risk=RiskLevel.MEDIUM,
        action=ActionType.RUN_COMMAND,
        command=("tmutil", "thinlocalsnapshots", "/", "999999999999", "4"),
        requires_sudo=True,
        warning="Requires administrator password. Safe for most setups; snapshots are recreated by Time Machine.",
    ),
    CleanupCategory(
        id="system_caches",
        name="System /Library/Caches",
        description="Shared system cache folder. Requires admin password. Apps rebuild caches as needed.",
        risk=RiskLevel.MEDIUM,
        action=ActionType.DELETE_PATHS,
        paths=(Path("/Library/Caches"),),
        requires_sudo=True,
        warning="Requires administrator password. Some apps may be slower on first launch after cleanup.",
    ),
)


def _which(name: str) -> str | None:
    import shutil

    return shutil.which(name)


def get_category(category_id: str) -> CleanupCategory | None:
    for category in CATEGORIES:
        if category.id == category_id:
            return category
    return None


def allowed_delete_roots() -> frozenset[Path]:
    """Resolved roots that deletion is permitted under."""
    roots: set[Path] = set()
    for category in CATEGORIES:
        if category.action == ActionType.DELETE_PATHS:
            for path in category.paths:
                roots.add(path.resolve() if path.exists() else path)
    return frozenset(roots)
