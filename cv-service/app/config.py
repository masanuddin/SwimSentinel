import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Matches "scheme://user:password@host..." so RTSP credentials never reach logs.
_CREDENTIALS = re.compile(r"^(?P<scheme>\w+://)(?P<creds>[^/@]+)@(?P<rest>.*)$")


def redact_source(source: str | None) -> str | None:
    """Strip embedded credentials from a capture source for safe display."""
    if not source:
        return source
    match = _CREDENTIALS.match(source)
    if not match:
        return source
    return f"{match.group('scheme')}***@{match.group('rest')}"

# Stable anchors derived from this file's location, independent of CWD.
# config.py lives at <repo>/cv-service/app/config.py
CV_SERVICE_ROOT = Path(__file__).resolve().parents[1]  # <repo>/cv-service
REPO_ROOT = Path(__file__).resolve().parents[2]  # <repo>


def resolve_repo_path(value: str) -> Path:
    """Resolve a configured path deterministically, independent of CWD.

    - Absolute paths are returned unchanged (env overrides stay honoured).
    - Repo-relative defaults such as ``cv-service/config`` resolve against the
      repository root so running from either the repo root or ``cv-service/``
      never produces doubled paths like ``cv-service/cv-service/config``.
    - A path that starts with ``cv-service`` is repo-root relative; any other
      relative path is treated as ``cv-service``-relative.
    """
    path = Path(value)
    if path.is_absolute():
        return path
    parts = path.parts
    if parts and parts[0] == "cv-service":
        return (REPO_ROOT / path).resolve()
    return (CV_SERVICE_ROOT / path).resolve()


class Settings(BaseSettings):
    mode: Literal["mock", "video", "camera"] = Field("mock", alias="CV_MODE")
    camera_source: str | None = Field(None, alias="CV_CAMERA_SOURCE")
    camera_id: str = Field("POOL-CAM-01", alias="CV_CAMERA_ID")
    model_path: str = Field("cv-service/models/best.pt", alias="CV_MODEL_PATH")
    config_dir: str = Field("cv-service/config", alias="CV_CONFIG_DIR")
    zones_file: str = Field("zones.example.json", alias="CV_ZONES_FILE")
    loop_video: bool = Field(False, alias="CV_LOOP_VIDEO")
    # Prerecorded fallback must play at the source's real frame rate: temporal
    # states are measured in wall-clock seconds, so playing a file as fast as
    # the GPU allows would compress the timeline and break persistence gates.
    # Disable only for throughput benchmarking.
    video_realtime: bool = Field(True, alias="CV_VIDEO_REALTIME")
    allowed_origins: str = Field(
        "http://localhost:5173,http://127.0.0.1:5173", alias="CV_ALLOWED_ORIGINS"
    )
    host: str = Field("127.0.0.1", alias="CV_HOST")
    port: int = Field(8000, alias="CV_PORT")
    log_level: str = Field("INFO", alias="CV_LOG_LEVEL")

    # Anchored to absolute paths so they load regardless of CWD. Later files
    # win. `.env.local` at the repo root is the team convention documented in
    # .env.example (Vite reads it too, so one file configures both sides);
    # `.env` and cv-service/.env stay supported as overrides.
    model_config = SettingsConfigDict(
        env_file=(
            REPO_ROOT / ".env",
            REPO_ROOT / ".env.local",
            CV_SERVICE_ROOT / ".env",
        ),
        extra="ignore",
    )

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def config_path(self) -> Path:
        return resolve_repo_path(self.config_dir)

    @property
    def resolved_model_path(self) -> Path:
        return resolve_repo_path(self.model_path)

    @property
    def thresholds_path(self) -> Path:
        return self.config_path / "thresholds.yaml"

    @property
    def zones_path(self) -> Path:
        return self.config_path / self.zones_file

    @property
    def safe_source(self) -> str | None:
        """Camera source with any credentials redacted (safe for logs/status)."""
        return redact_source(self.camera_source)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_thresholds(settings: Settings) -> dict:
    with settings.thresholds_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError("thresholds.yaml must contain a mapping")
    return loaded
