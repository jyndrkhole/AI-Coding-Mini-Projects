"""Release pipeline: separate iOS (increment + TestFlight) and Android (AAB only)."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Literal

from config import settings

Platform = Literal["ios", "android"]


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class PipelineStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class PipelineStep:
    id: str
    label: str
    status: StepStatus = StepStatus.PENDING
    detail: str = ""


@dataclass
class ReleaseState:
    status: PipelineStatus = PipelineStatus.IDLE
    platform: Platform | None = None
    steps: list[PipelineStep] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    started_at: str | None = None
    finished_at: str | None = None
    current_build: int | None = None
    new_build: int | None = None
    error: str | None = None
    ipa_path: str | None = None
    aab_path: str | None = None

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "platform": self.platform,
            "steps": [
                {"id": s.id, "label": s.label, "status": s.status.value, "detail": s.detail}
                for s in self.steps
            ],
            "logs": self.logs[-500:],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "current_build": self.current_build,
            "new_build": self.new_build,
            "error": self.error,
            "ipa_path": self.ipa_path,
            "aab_path": self.aab_path,
        }


BUILD_PATTERN = re.compile(
    r"(<ApplicationVersion>)(\d+)(</ApplicationVersion>)",
    re.IGNORECASE,
)

STEP_DEFINITIONS: dict[Platform, list[tuple[str, str]]] = {
    "ios": [
        ("increment", "Increment build number"),
        ("publish_ios", "Build iOS (.ipa)"),
        ("upload_ios", "Upload TestFlight"),
    ],
    "android": [
        ("publish_android", "Build signed Android (.aab)"),
    ],
}


def read_build_number(csproj: Path) -> int:
    content = csproj.read_text(encoding="utf-8")
    match = BUILD_PATTERN.search(content)
    if not match:
        raise ValueError(f"Could not find <ApplicationVersion> in {csproj}")
    return int(match.group(2))


def increment_build_number(csproj: Path) -> tuple[int, int]:
    content = csproj.read_text(encoding="utf-8")
    match = BUILD_PATTERN.search(content)
    if not match:
        raise ValueError(f"Could not find <ApplicationVersion> in {csproj}")

    old = int(match.group(2))
    new = old + 1
    updated = BUILD_PATTERN.sub(rf"\g<1>{new}\g<3>", content, count=1)
    csproj.write_text(updated, encoding="utf-8")
    return old, new


def build_steps(platform: Platform) -> list[PipelineStep]:
    return [PipelineStep(step_id, label) for step_id, label in STEP_DEFINITIONS[platform]]


class ReleasePipeline:
    def __init__(self) -> None:
        self.state = ReleaseState()
        self._lock = asyncio.Lock()
        self._log_callbacks: list[Callable[[str], None]] = []

    def subscribe_logs(self, callback: Callable[[str], None]) -> None:
        self._log_callbacks.append(callback)

    def _emit_log(self, line: str) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        entry = f"[{timestamp}] {line}"
        self.state.logs.append(entry)
        for cb in self._log_callbacks:
            cb(entry)

    def _set_step(self, step_id: str, status: StepStatus, detail: str = "") -> None:
        for step in self.state.steps:
            if step.id == step_id:
                step.status = status
                if detail:
                    step.detail = detail
                break

    async def _run_command(
        self,
        cmd: list[str],
        cwd: Path | None = None,
        redact: list[str] | None = None,
    ) -> tuple[int, str]:
        display = " ".join(cmd)
        for secret in redact or []:
            if secret:
                display = display.replace(secret, "****")
        self._emit_log(f"$ {display}")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd) if cwd else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        output_lines: list[str] = []
        assert proc.stdout is not None
        while True:
            chunk = await proc.stdout.readline()
            if not chunk:
                break
            line = chunk.decode("utf-8", errors="replace").rstrip()
            output_lines.append(line)
            self._emit_log(line)

        code = await proc.wait()
        return code, "\n".join(output_lines)

    async def run(self, platform: Platform) -> ReleaseState:
        async with self._lock:
            if self.state.status == PipelineStatus.RUNNING:
                raise RuntimeError("A release is already in progress")

            self.state = ReleaseState(
                platform=platform,
                steps=build_steps(platform),
                status=PipelineStatus.RUNNING,
                started_at=datetime.now(timezone.utc).isoformat(),
            )

            try:
                if platform == "ios":
                    self._emit_log("=== iOS TestFlight release ===")
                    await self._step_increment()
                    await self._step_publish_ios()
                    await self._step_upload_ios()
                else:
                    self._emit_log("=== Android AAB build ===")
                    await self._step_publish_android()

                self.state.status = PipelineStatus.SUCCESS
                self._emit_log("Done.")
            except Exception as exc:
                self.state.status = PipelineStatus.FAILED
                self.state.error = str(exc)
                self._emit_log(f"ERROR: {exc}")
            finally:
                self.state.finished_at = datetime.now(timezone.utc).isoformat()

            return self.state

    async def _step_increment(self) -> None:
        self._set_step("increment", StepStatus.RUNNING)
        csproj = settings.csproj_path
        if not csproj.exists():
            self._set_step("increment", StepStatus.FAILED, "csproj not found")
            raise FileNotFoundError(f"Project file not found: {csproj}")

        old, new = await asyncio.to_thread(increment_build_number, csproj)
        self.state.current_build = old
        self.state.new_build = new
        self._emit_log(f"iOS build number: {old} → {new}")
        self._set_step("increment", StepStatus.SUCCESS, f"{old} → {new}")

    async def _step_publish_ios(self) -> None:
        self._set_step("publish_ios", StepStatus.RUNNING)
        csproj = settings.csproj_path
        cmd = [
            "dotnet",
            "publish",
            str(csproj),
            "-f",
            settings.ios_framework,
            "-c",
            settings.dotnet_configuration,
            f"-p:RuntimeIdentifier={settings.ios_runtime_identifier}",
            "-p:ArchiveOnBuild=true",
        ]
        code, _ = await self._run_command(cmd, cwd=settings.project_root)
        if code != 0:
            self._set_step("publish_ios", StepStatus.FAILED, f"exit code {code}")
            raise RuntimeError(f"iOS dotnet publish failed with exit code {code}")

        ipa = settings.ipa_path
        if not ipa.exists():
            self._set_step("publish_ios", StepStatus.FAILED, "IPA not found")
            raise FileNotFoundError(f"Expected IPA at {ipa}")

        self.state.ipa_path = str(ipa)
        size_mb = ipa.stat().st_size / (1024 * 1024)
        self._set_step("publish_ios", StepStatus.SUCCESS, f"{ipa.name} ({size_mb:.1f} MB)")

    async def _step_upload_ios(self) -> None:
        self._set_step("upload_ios", StepStatus.RUNNING)

        if not settings.apple_id or not settings.apple_app_password:
            self._set_step("upload_ios", StepStatus.FAILED, "Missing Apple credentials")
            raise ValueError(
                "Set APPLE_ID and APPLE_APP_PASSWORD in .env before uploading"
            )

        ipa = settings.ipa_path
        cmd = [
            "xcrun",
            "altool",
            "--upload-app",
            "-f",
            str(ipa),
            "-t",
            "ios",
            "-u",
            settings.apple_id,
            "-p",
            settings.apple_app_password,
        ]
        code, _ = await self._run_command(
            cmd,
            cwd=settings.ios_publish_dir,
            redact=[settings.apple_app_password],
        )
        if code != 0:
            self._set_step("upload_ios", StepStatus.FAILED, f"exit code {code}")
            raise RuntimeError(f"TestFlight upload failed with exit code {code}")

        self._set_step("upload_ios", StepStatus.SUCCESS, "Uploaded to App Store Connect")

    async def _step_publish_android(self) -> None:
        self._set_step("publish_android", StepStatus.RUNNING)

        if not settings.android_configured:
            self._set_step("publish_android", StepStatus.FAILED, "Missing Android signing config")
            raise ValueError(
                "Set ANDROID_KEYSTORE_PATH, ANDROID_KEYSTORE_PASS, "
                "ANDROID_KEY_ALIAS, and ANDROID_KEY_PASS in .env"
            )

        keystore = settings.android_keystore_path
        if not keystore.exists():
            self._set_step("publish_android", StepStatus.FAILED, "Keystore not found")
            raise FileNotFoundError(f"Keystore not found: {keystore}")

        csproj = settings.csproj_path
        cmd = [
            "dotnet",
            "publish",
            str(csproj),
            "-f",
            settings.android_framework,
            "-c",
            settings.dotnet_configuration,
            "-p:AndroidPackageFormat=aab",
            "-p:AndroidKeyStore=true",
            f"-p:AndroidSigningKeyStore={keystore}",
            f"-p:AndroidSigningStorePass={settings.android_keystore_pass}",
            f"-p:AndroidSigningKeyAlias={settings.android_key_alias}",
            f"-p:AndroidSigningKeyPass={settings.android_key_pass}",
        ]
        code, _ = await self._run_command(
            cmd,
            cwd=settings.project_root,
            redact=[settings.android_keystore_pass, settings.android_key_pass],
        )
        if code != 0:
            self._set_step("publish_android", StepStatus.FAILED, f"exit code {code}")
            raise RuntimeError(f"Android dotnet publish failed with exit code {code}")

        aab = settings.find_signed_aab()
        if not aab or not aab.exists():
            self._set_step("publish_android", StepStatus.FAILED, "AAB not found")
            raise FileNotFoundError(
                f"Expected signed AAB in {settings.android_publish_dir}"
            )

        self.state.aab_path = str(aab)
        size_mb = aab.stat().st_size / (1024 * 1024)
        self._set_step(
            "publish_android",
            StepStatus.SUCCESS,
            f"{aab.name} ({size_mb:.1f} MB)",
        )
        self._emit_log(f"Android AAB ready: {aab}")


pipeline = ReleasePipeline()


async def get_current_build_preview() -> dict:
    csproj = settings.csproj_path
    signed_aab = settings.find_signed_aab()
    base = {
        "csproj_path": str(csproj),
        "ipa_path": str(settings.ipa_path),
        "aab_path": str(signed_aab) if signed_aab else str(settings.android_publish_dir),
    }
    if not csproj.exists():
        return {"current": None, "next": None, **base}

    current = read_build_number(csproj)
    return {"current": current, "next": current + 1, **base}
