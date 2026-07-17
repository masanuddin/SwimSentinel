"""Detection, tracking, and capture.

Owns model loading, the video/camera source, YOLO11s inference, ByteTrack
association, anonymous track IDs, boxes/classes/confidences/centroids, FPS and
inference timing, an optional debug overlay, and model/source error reporting.

This module imports OpenCV, Torch, and Ultralytics at import time, so it must
only be imported for `video`/`camera` modes. Mock mode never imports it.

Track IDs are anonymous and temporary. A track ID identifies a tracked box
across frames; it is not a person, an identity, or a wristband owner. Detection
confidence is an object-detection score, never a drowning probability.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import yaml

EXPECTED_CLASS_NAMES = {
    0: "distress_candidate",
    1: "out_of_water",
    2: "normal_swimming",
}


class VisionError(RuntimeError):
    """Model or capture-source failure."""


@dataclass(frozen=True)
class Detection:
    """One tracked detection in one frame."""

    track_id: int | None
    class_id: int
    class_name: str
    confidence: float
    xyxy: tuple[float, float, float, float]

    @property
    def centroid(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.xyxy
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @property
    def diagonal(self) -> float:
        x1, y1, x2, y2 = self.xyxy
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


@dataclass
class FrameResult:
    frame_index: int
    timestamp: float  # monotonic seconds
    width: int
    height: int
    detections: list[Detection]
    inference_ms: float
    frame: object | None = field(default=None, repr=False)


def stretch_to_square(frame, size: int):
    """Stretch a frame to size×size, returning (frame, scale_x, scale_y).

    The training dataset was exported with every image *stretched* to 640×640
    (aspect ratio not preserved), so the detector learned people in that
    distorted geometry. Inference must distort the same way: letterboxing a
    16:9 frame instead measurably costs recall (in-domain 640→1280×720 probe:
    96.5% stretched vs 89.5% letterboxed) and skews uncertain detections
    toward distress_candidate. Scale factors map box coordinates back to the
    original frame so zones and motion stay in real pixel space.
    """
    height, width = frame.shape[:2]
    if (width, height) == (size, size):
        return frame, 1.0, 1.0
    stretched = cv2.resize(frame, (size, size), interpolation=cv2.INTER_LINEAR)
    return stretched, width / size, height / size


def scale_xyxy(
    xyxy: tuple[float, float, float, float], scale_x: float, scale_y: float
) -> tuple[float, float, float, float]:
    """Map a box from stretched-input space back to original-frame space."""
    x1, y1, x2, y2 = xyxy
    return (x1 * scale_x, y1 * scale_y, x2 * scale_x, y2 * scale_y)


def resolve_source(source: str | None, mode: str) -> str | int:
    """Turn a configured source into an OpenCV-compatible source.

    Numeric strings become camera indices; everything else is passed through
    (file path, RTSP/HTTP URL). Camera index 0 is never assumed.
    """
    if source is None or str(source).strip() == "":
        raise VisionError(
            f"CV_CAMERA_SOURCE is required for mode '{mode}' "
            "(a video file path, a camera index like '0', or a stream URL)."
        )
    text = str(source).strip()
    if text.isdigit():
        return int(text)
    return text


class VideoSource:
    """OpenCV capture wrapper with explicit end-of-stream/failure handling."""

    def __init__(self, source: str | int, loop: bool = False) -> None:
        self.source = source
        self.loop = loop
        self.ended = False
        self._capture = cv2.VideoCapture(source)
        if not self._capture.isOpened():
            raise VisionError(f"could not open capture source: {_display(source)}")
        self.width = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)) or 0
        self.height = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 0
        self.declared_fps = float(self._capture.get(cv2.CAP_PROP_FPS)) or 0.0

    def read(self):
        """Return the next frame, or None at end-of-stream / on failure."""
        ok, frame = self._capture.read()
        if ok and frame is not None:
            return frame
        if self.loop:
            self._capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self._capture.read()
            if ok and frame is not None:
                return frame
        self.ended = True
        return None

    def release(self) -> None:
        try:
            self._capture.release()
        except Exception:
            pass


def _display(source: str | int) -> str:
    """Never echo credentials from a stream URL."""
    from app.config import redact_source

    return str(redact_source(str(source)))


class Detector:
    """YOLO11s + ByteTrack. Validates that the checkpoint has our classes."""

    def __init__(
        self,
        model_path: Path,
        tracker_config: Path,
        device: str = "auto",
        input_size: int = 640,
        tracking_confidence: float = 0.15,
        preprocess: str = "stretch",
    ) -> None:
        if preprocess not in ("stretch", "letterbox"):
            raise VisionError(
                f"detection.preprocess must be 'stretch' or 'letterbox', got {preprocess!r}"
            )
        self.preprocess = preprocess
        if not Path(model_path).is_file():
            raise VisionError(
                f"model checkpoint not found: {model_path}\n"
                "Train it (cv-service/training/train.py) or copy an approved "
                "best.pt to cv-service/models/best.pt (see cv-service/README.md)."
            )
        from ultralytics import YOLO  # deferred: slow import

        try:
            self.model = YOLO(str(model_path))
        except Exception as exc:  # pragma: no cover - depends on checkpoint file
            raise VisionError(f"failed to load model {model_path}: {exc}") from exc

        self.names: dict[int, str] = dict(self.model.names)
        unexpected = {
            class_id: name
            for class_id, name in self.names.items()
            if EXPECTED_CLASS_NAMES.get(class_id) != name
        }
        if unexpected:
            raise VisionError(
                f"model classes {self.names} do not match expected "
                f"{EXPECTED_CLASS_NAMES}; mismatched: {unexpected}"
            )

        self.tracker_config = Path(tracker_config)
        self.device = None if device == "auto" else device
        self.input_size = input_size
        self.tracking_confidence = tracking_confidence

    def track(self, frame) -> tuple[list[Detection], float]:
        """Run detection + ByteTrack on one frame. Returns (detections, ms).

        Box coordinates are always in the original frame's pixel space,
        regardless of the preprocess mode.
        """
        started = time.perf_counter()
        if self.preprocess == "stretch":
            model_input, scale_x, scale_y = stretch_to_square(frame, self.input_size)
        else:
            model_input, scale_x, scale_y = frame, 1.0, 1.0
        try:
            results = self.model.track(
                source=model_input,
                persist=True,
                tracker=str(self.tracker_config),
                conf=self.tracking_confidence,
                imgsz=self.input_size,
                device=self.device,
                verbose=False,
            )
        except Exception as exc:
            raise VisionError(f"inference failed: {exc}") from exc
        inference_ms = (time.perf_counter() - started) * 1000.0

        detections: list[Detection] = []
        if not results:
            return detections, inference_ms
        boxes = results[0].boxes
        if boxes is None or boxes.id is None and len(boxes) == 0:
            return detections, inference_ms

        track_ids = boxes.id.tolist() if boxes.id is not None else [None] * len(boxes)
        for xyxy, class_id, confidence, track_id in zip(
            boxes.xyxy.tolist(), boxes.cls.tolist(), boxes.conf.tolist(), track_ids
        ):
            class_index = int(class_id)
            detections.append(
                Detection(
                    track_id=int(track_id) if track_id is not None else None,
                    class_id=class_index,
                    class_name=self.names.get(class_index, str(class_index)),
                    confidence=float(confidence),
                    xyxy=scale_xyxy(
                        (float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])),
                        scale_x,
                        scale_y,
                    ),
                )
            )
        return detections, inference_ms

    def reset_tracker(self) -> None:
        """Drop tracker state (e.g. when a source restarts)."""
        predictor = getattr(self.model, "predictor", None)
        trackers = getattr(predictor, "trackers", None) if predictor else None
        if trackers:
            for tracker in trackers:
                if hasattr(tracker, "reset"):
                    tracker.reset()


def write_tracker_config(thresholds: dict, out_path: Path) -> Path:
    """Materialize an Ultralytics ByteTrack config from thresholds.yaml.

    thresholds.yaml stays the single source of truth; Ultralytics needs its own
    tracker YAML. `track_buffer` is expressed in frames, so it is derived from
    track_lost_timeout_ms using the configured nominal FPS. Authoritative,
    time-based track-loss is still enforced by the state engine, which is what
    makes variable real FPS safe.
    """
    tracking = thresholds.get("tracking", {}) or {}
    nominal_fps = float(tracking.get("nominal_fps", 30) or 30)
    timeout_ms = float(tracking.get("track_lost_timeout_ms", 1500))
    track_buffer = max(1, round(timeout_ms / 1000.0 * nominal_fps))
    config = {
        "tracker_type": "bytetrack",
        "track_high_thresh": float(tracking.get("track_high_thresh", 0.40)),
        "track_low_thresh": float(tracking.get("track_low_thresh", 0.10)),
        "new_track_thresh": float(tracking.get("new_track_thresh", 0.40)),
        "track_buffer": track_buffer,
        "match_thresh": float(tracking.get("match_thresh", 0.80)),
        "fuse_score": True,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, sort_keys=False)
    return out_path


class FpsMeter:
    """Rolling FPS + frame-latency statistics over a bounded window."""

    def __init__(self, window: int = 60) -> None:
        self.window = window
        self._frame_ms: list[float] = []
        self._last: float | None = None

    def tick(self, now: float) -> None:
        if self._last is not None:
            self._frame_ms.append((now - self._last) * 1000.0)
            if len(self._frame_ms) > self.window:
                self._frame_ms.pop(0)
        self._last = now

    @property
    def fps(self) -> float:
        if not self._frame_ms:
            return 0.0
        mean_ms = sum(self._frame_ms) / len(self._frame_ms)
        return 1000.0 / mean_ms if mean_ms > 0 else 0.0

    def percentile_ms(self, pct: float) -> float:
        if not self._frame_ms:
            return 0.0
        ordered = sorted(self._frame_ms)
        index = min(len(ordered) - 1, max(0, round(pct / 100.0 * (len(ordered) - 1))))
        return ordered[index]


STATE_COLORS = {
    "normal": (0, 200, 0),
    "watch": (0, 200, 255),
    "suspected_distress": (0, 0, 255),
    "suspected_inactivity": (0, 0, 255),
    "track_lost": (128, 128, 128),
}


def draw_overlay(frame, detections, evidence_by_track, zone_map, fps, extra_lines=None):
    """Annotate a frame for debugging: boxes, class+conf, track, zone, state.

    `evidence_by_track` maps track id -> object with .visualState / .zoneId /
    .normalizedMovement (may be missing for untracked boxes).
    """
    annotated = frame.copy()

    if zone_map is not None:
        roi_points = [(int(x), int(y)) for x, y in zone_map.roi]
        for index in range(len(roi_points)):
            cv2.line(
                annotated, roi_points[index], roi_points[(index + 1) % len(roi_points)],
                (255, 200, 0), 1, cv2.LINE_AA,
            )

    for detection in detections:
        x1, y1, x2, y2 = (int(v) for v in detection.xyxy)
        evidence = evidence_by_track.get(detection.track_id)
        state = getattr(evidence, "visual_state", None) or "normal"
        state_text = state.value if hasattr(state, "value") else str(state)
        color = STATE_COLORS.get(state_text, (200, 200, 200))
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

        label = f"{detection.class_name} {detection.confidence:.2f}"
        if detection.track_id is not None:
            label += f" #{detection.track_id}"
        cv2.putText(annotated, label, (x1, max(12, y1 - 18)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

        detail = state_text
        if evidence is not None:
            zone = getattr(evidence, "zone_id", None)
            detail += f" z{zone if zone is not None else '-'}"
            movement = getattr(evidence, "normalized_movement", None)
            if movement is not None:
                detail += f" m{movement:.3f}"
        cv2.putText(annotated, detail, (x1, max(24, y1 - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

    lines = [f"FPS {fps:.1f}"] + list(extra_lines or [])
    for index, line in enumerate(lines):
        cv2.putText(annotated, line, (8, 20 + index * 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return annotated


def iter_frames(source: VideoSource) -> Iterator:
    """Yield frames until end-of-stream."""
    while True:
        frame = source.read()
        if frame is None:
            return
        yield frame
