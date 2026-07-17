from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class RawClass(str, Enum):
    normal_swimming = "normal_swimming"
    distress_candidate = "distress_candidate"
    out_of_water = "out_of_water"


class MotionState(str, Enum):
    normal = "normal"
    low = "low"
    unknown = "unknown"


class Visibility(str, Enum):
    clear = "clear"
    limited = "limited"
    lost = "lost"
    unavailable = "unavailable"


class VisualState(str, Enum):
    normal = "normal"
    watch = "watch"
    suspected_distress = "suspected_distress"
    suspected_inactivity = "suspected_inactivity"
    visibility_limited = "visibility_limited"
    track_lost = "track_lost"
    camera_unavailable = "camera_unavailable"


class VisualEvidenceEvent(BaseModel):
    """One track's visual evidence at a point in time.

    Four fields are nullable because some visual states have no track or no
    zone by definition:

    * ``camera_unavailable`` — the source failed: no track, zone, or class.
    * ``track_lost`` — the track is gone: no live confidence.
    * a detection outside the pool ROI — a real track with ``zoneId = None``.

    Consumers must treat ``zoneId = None`` as "not in a pool zone" and must
    never escalate it as in-pool evidence.
    """

    timestamp: datetime
    cameraId: str
    trackId: int | None = None
    zoneId: Literal[1, 2, 3, 4] | None = None
    rawClass: RawClass | None = None
    detectionConfidence: float | None = Field(default=None, ge=0, le=1)
    motionState: MotionState
    lowMotionDurationMs: int = Field(ge=0)
    classPersistenceMs: int = Field(ge=0)
    visibility: Visibility
    visualState: VisualState
    evidence: list[str]
    # Normalized movement = displacement / bbox diagonal / second.
    # None when there is not enough history to measure it (never "low").
    normalizedMovement: float | None = None


class HeartbeatEvent(BaseModel):
    timestamp: datetime
    cameraId: str
    mode: str
    status: Literal["ok"] = "ok"


class StatusResponse(BaseModel):
    service: Literal["cv-service"] = "cv-service"
    mode: str
    cameraId: str
    ready: bool
    status: str
    modelPath: str
    configDir: str
    thresholdsLoaded: bool
    allowedOrigins: list[str]
    timestamp: datetime
    # Runtime fields (video/camera modes). Null/zero in mock mode.
    modelLoaded: bool = False
    sourceAvailable: bool = False
    # Capture source with any credentials redacted.
    source: str | None = None
    device: str | None = None
    fps: float = 0.0
    avgInferenceMs: float = 0.0
    activeTracks: int = 0
    latestFrameTimestamp: datetime | None = None
    latestError: str | None = None
    classNames: dict[int, str] | None = None
