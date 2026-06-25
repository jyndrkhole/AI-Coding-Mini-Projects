"""Configuration loaded from environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MAUI project
    project_root: Path = Path("/Users/jayendra/Desktop/AgentVizion2Go")
    csproj_path: Path = Path(
        "/Users/jayendra/Desktop/AgentVizion2Go/AgentVizion2Go.MAUI/AgentVizion2Go.MAUI.csproj"
    )
    dotnet_configuration: str = "Release"

    # iOS
    ios_framework: str = "net9.0-ios"
    ios_runtime_identifier: str = "ios-arm64"
    ipa_filename: str = "AgentVizion2Go.MAUI.ipa"

    # Android
    android_framework: str = "net9.0-android"
    android_keystore_path: Path = Path(
        "/Users/jayendra/Documents/Magnifact/Certs/AgentVizion2Go/AgentVizion2Go.keystore"
    )
    android_keystore_pass: str = ""
    android_key_alias: str = "AgentVizion2Go"
    android_key_pass: str = ""

    # Apple credentials (app-specific password, not Apple ID password)
    apple_id: str = ""
    apple_app_password: str = ""

    # Groq (optional — used for log analysis / AI assistant)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Server
    host: str = "127.0.0.1"
    port: int = 8787

    @property
    def ios_publish_dir(self) -> Path:
        return (
            self.project_root
            / "AgentVizion2Go.MAUI"
            / "bin"
            / self.dotnet_configuration
            / self.ios_framework
            / self.ios_runtime_identifier
            / "publish"
        )

    @property
    def ipa_path(self) -> Path:
        return self.ios_publish_dir / self.ipa_filename

    @property
    def android_publish_dir(self) -> Path:
        return (
            self.project_root
            / "AgentVizion2Go.MAUI"
            / "bin"
            / self.dotnet_configuration
            / self.android_framework
            / "publish"
        )

    def find_signed_aab(self) -> Path | None:
        publish_dir = self.android_publish_dir
        if not publish_dir.exists():
            return None
        signed = sorted(publish_dir.glob("*-Signed.aab"))
        return signed[-1] if signed else None

    @property
    def android_configured(self) -> bool:
        return bool(
            self.android_keystore_path
            and self.android_keystore_pass
            and self.android_key_alias
            and self.android_key_pass
        )


settings = Settings()
