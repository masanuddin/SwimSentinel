"""Mode selection, orchestration, and bounded SSE distribution.

Mock mode is deterministic and never imports vision/YOLO.

Video and camera modes run **one** shared runtime producer regardless of how
many SSE clients connect: the producer owns the capture source, the detector,
the tracker, and the state engine, and fans events out to bounded per-client
queues. A slow or disconnected client can never stall the pipeline or grow a
queue without bound — its oldest events are dropped instead.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from app.config import Settings, load_thresholds
from app.schemas import HeartbeatEvent, VisualEvidenceEvent
from app.state import EngineConfig, SseEvent, TemporalStateEngine, TrackEvidence
from app.zones import ZoneMap, anchor_point

logger = logging.getLogger(__name__)

# Fallbacks used only when thresholds config is missing/unreadable.
DEFAULT_HEARTBEAT_MS = 3000
DEFAULT_MOCK_EVENT_MS = 1000

# Bounded per-subscriber queue: drop oldest rather than block the producer.
SUBSCRIBER_QUEUE_SIZE = 32


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def event_intervals(settings: Settings) -> tuple[float, float]:
    """Read heartbeat and mock-event cadence (seconds) from thresholds config."""
    heartbeat_ms = DEFAULT_HEARTBEAT_MS
    mock_event_ms = DEFAULT_MOCK_EVENT_MS
    try:
        events = load_thresholds(settings).get("events", {}) or {}
        heartbeat_ms = int(events.get("heartbeat_ms", heartbeat_ms))
        mock_event_ms = int(events.get("mock_event_ms", mock_event_ms))
    except Exception:
        pass
    return heartbeat_ms / 1000.0, mock_event_ms / 1000.0


def mock_visual_evidence(settings: Settings, sequence: int = 0) -> VisualEvidenceEvent:
    zone_id = (sequence % 4) + 1
    is_watch = sequence % 2 == 0
    return VisualEvidenceEvent(
        timestamp=utc_now(),
        cameraId=settings.camera_id,
        trackId=7 + sequence,
        zoneId=zone_id,
        rawClass="distress_candidate" if is_watch else "normal_swimming",
        detectionConfidence=0.84 if is_watch else 0.76,
        motionState="low" if is_watch else "normal",
        lowMotionDurationMs=2800 if is_watch else 0,
        classPersistenceMs=2200 if is_watch else 400,
        visibility="clear",
        visualState="suspected_distress" if is_watch else "normal",
        evidence=(
            ["persistent_distress_appearance", "limited_displacement"]
            if is_watch
            else ["normal_swimming_appearance"]
        ),
    )


def heartbeat(settings: Settings) -> HeartbeatEvent:
    return HeartbeatEvent(timestamp=utc_now(), cameraId=settings.camera_id, mode=settings.mode)


def encode_sse(event: SseEvent, payload: object) -> str:
    if hasattr(payload, "model_dump_json"):
        data = payload.model_dump_json()
    else:
        data = json.dumps(payload)
    return f"event: {event.value}\ndata: {data}\n\n"


async def mock_event_stream(settings: Settings) -> AsyncIterator[str]:
    heartbeat_s, mock_event_s = event_intervals(settings)
    tick = min(heartbeat_s, mock_event_s)

    # Emit both once immediately so a fresh connection has data right away.
    yield encode_sse(SseEvent.heartbeat, heartbeat(settings))
    yield encode_sse(SseEvent.visual_evidence, mock_visual_evidence(settings, 0))

    sequence = 1
    since_heartbeat = 0.0
    since_mock = 0.0
    while True:
        await asyncio.sleep(tick)
        since_heartbeat += tick
        since_mock += tick
        if since_heartbeat + 1e-9 >= heartbeat_s:
            yield encode_sse(SseEvent.heartbeat, heartbeat(settings))
            since_heartbeat = 0.0
        if since_mock + 1e-9 >= mock_event_s:
            yield encode_sse(SseEvent.visual_evidence, mock_visual_evidence(settings, sequence))
            sequence += 1
            since_mock = 0.0


# --------------------------------------------------------------------------- #
# Runtime orchestration (video / camera modes)
# --------------------------------------------------------------------------- #


class CvRuntime:
    """One capture source -> detector -> tracker -> zones -> state engine.

    Blocking work (`open`/`step`/`close`) is called from a worker thread by
    `RuntimeProducer`. `app.vision` is imported lazily so that importing this
    module in mock mode never pulls in OpenCV/Torch/Ultralytics.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.thresholds = load_thresholds(settings)
        self.engine = TemporalStateEngine(EngineConfig.from_thresholds(self.thresholds))

        events = self.thresholds.get("events", {}) or {}
        self.periodic_event_s = float(events.get("periodic_event_ms", 2000)) / 1000.0
        self.min_event_interval_s = float(events.get("min_event_interval_ms", 400)) / 1000.0
        self.zone_anchor = str(
            (self.thresholds.get("zones", {}) or {}).get("anchor", "centroid")
        )

        self.zone_map: ZoneMap | None = None
        self._scaled_zones: ZoneMap | None = None
        self.detector = None
        self.source = None
        self.fps_meter = None

        self.model_loaded = False
        self.source_healthy = False
        self.source_ended = False
        self.latest_error: str | None = None
        self.latest_frame_ts: datetime | None = None
        self.frame_index = 0
        self.last_frame = None
        self.last_detections: list = []
        self.last_evidence: dict[int, TrackEvidence] = {}

        self._inference_ms: deque[float] = deque(maxlen=60)
        self._last_emitted: dict[object, tuple[float, str]] = {}
        self._playback_start: float | None = None
        self._playback_frames = 0

    # -- lifecycle -------------------------------------------------------- #

    def open(self) -> None:
        from app.vision import (  # deferred: keeps mock mode free of cv2/torch
            Detector,
            FpsMeter,
            VideoSource,
            resolve_source,
            write_tracker_config,
        )
        from app.config import CV_SERVICE_ROOT

        self.zone_map = ZoneMap.from_file(self.settings.zones_path)
        self.fps_meter = FpsMeter()

        tracker_config = write_tracker_config(
            self.thresholds, CV_SERVICE_ROOT / "runs" / "bytetrack.runtime.yaml"
        )
        detection = self.thresholds.get("detection", {}) or {}
        self.detector = Detector(
            model_path=self.settings.resolved_model_path,
            tracker_config=tracker_config,
            device=str(detection.get("device", "auto")),
            input_size=int(detection.get("input_size", 640)),
            tracking_confidence=float(detection.get("tracking_confidence", 0.15)),
            preprocess=str(detection.get("preprocess", "stretch")),
        )
        self.model_loaded = True

        source = resolve_source(self.settings.camera_source, self.settings.mode)
        self.source = VideoSource(source, loop=self.settings.loop_video)
        self.source_healthy = True
        self.source_ended = False
        self.latest_error = None
        self.engine.set_source_healthy(True)

    def close(self) -> None:
        if self.source is not None:
            self.source.release()
            self.source = None
        self.source_healthy = False

    def record_error(self, message: str) -> None:
        self.latest_error = message
        self.source_healthy = False
        self.engine.set_source_healthy(False)

    # -- per-frame -------------------------------------------------------- #

    def step(self) -> list[VisualEvidenceEvent]:
        """Process one frame. Returns the SSE events to publish (may be empty)."""
        now = time.monotonic()

        if self.source is None:
            self.engine.set_source_healthy(False)
            return self._emit(self.engine.update(now), now)

        frame = self.source.read()
        if frame is None:
            # End-of-video or a read failure: never report this as NORMAL.
            if not self.source_ended:
                self.source_ended = True
                reason = "capture source ended" if self.source.ended else "capture read failed"
                self.record_error(reason)
                logger.warning("CV source unavailable: %s", reason)
            # Stale detections must not linger and look live once the source is gone.
            self.last_detections = []
            self.last_evidence = {}
            return self._emit(self.engine.update(now), now)

        if not self.source_healthy:
            # Source recovered (e.g. a looped video restarted).
            self.source_healthy = True
            self.source_ended = False
            self.latest_error = None
            self.engine.set_source_healthy(True)

        self._pace_playback()
        now = time.monotonic()

        self.frame_index += 1
        self.fps_meter.tick(now)
        self.latest_frame_ts = utc_now()

        detections, inference_ms = self.detector.track(frame)
        self._inference_ms.append(inference_ms)
        self.last_frame = frame
        self.last_detections = detections

        height, width = frame.shape[:2]
        if self._scaled_zones is None or (
            self._scaled_zones.frame_width,
            self._scaled_zones.frame_height,
        ) != (width, height):
            self._scaled_zones = self.zone_map.scaled_to(width, height)

        for detection in detections:
            if detection.track_id is None:
                continue  # untracked box: shown in debug, contributes no evidence
            x, y = anchor_point(detection.xyxy, self.zone_anchor)
            zone_id = self._scaled_zones.zone_for_point(x, y)
            self.engine.observe(
                track_id=detection.track_id,
                now=now,
                centroid=detection.centroid,
                diagonal=detection.diagonal,
                class_name=detection.class_name,
                confidence=detection.confidence,
                zone_id=zone_id,
                in_roi=self._scaled_zones.in_roi(x, y),
            )

        evidences = self.engine.update(now)
        self.last_evidence = {
            evidence.track_id: evidence
            for evidence in evidences
            if evidence.track_id is not None
        }
        return self._emit(evidences, now)

    def _pace_playback(self) -> None:
        """Hold a prerecorded file to its real frame rate.

        A camera delivers frames in real time, so wall-clock elapsed time and
        video time agree. A file does not: decoding as fast as the GPU allows
        would replay 8s of video in ~2s and silently defeat every persistence
        gate. Pacing makes the prerecorded fallback behave like the camera it
        stands in for. A source slower than real time is never sped up.
        """
        if self.settings.mode != "video" or not self.settings.video_realtime:
            return
        fps = getattr(self.source, "declared_fps", 0.0) or 0.0
        if fps <= 0:
            return
        if self._playback_start is None:
            self._playback_start = time.monotonic()
            self._playback_frames = 0
        self._playback_frames += 1
        target = self._playback_start + self._playback_frames / fps
        delay = target - time.monotonic()
        if delay > 0:
            time.sleep(delay)

    # -- emission policy -------------------------------------------------- #

    def _emit(self, evidences: list[TrackEvidence], now: float) -> list[VisualEvidenceEvent]:
        """Emit on meaningful state change, plus a bounded periodic refresh."""
        events: list[VisualEvidenceEvent] = []
        live_keys = set()
        for evidence in evidences:
            key = evidence.track_id
            live_keys.add(key)
            state = evidence.visual_state.value
            previous = self._last_emitted.get(key)

            if previous is None:
                should_emit = True
            else:
                last_time, last_state = previous
                elapsed = now - last_time
                if elapsed < self.min_event_interval_s:
                    should_emit = False
                elif state != last_state:
                    should_emit = True
                else:
                    should_emit = (
                        self.periodic_event_s > 0 and elapsed >= self.periodic_event_s
                    )

            if should_emit:
                self._last_emitted[key] = (now, state)
                events.append(self._to_event(evidence))

        for key in list(self._last_emitted):
            if key not in live_keys:
                del self._last_emitted[key]
        return events

    def _to_event(self, evidence: TrackEvidence) -> VisualEvidenceEvent:
        return VisualEvidenceEvent(
            timestamp=utc_now(),
            cameraId=self.settings.camera_id,
            trackId=evidence.track_id,
            zoneId=evidence.zone_id,
            rawClass=evidence.raw_class,
            detectionConfidence=evidence.detection_confidence,
            motionState=evidence.motion_state,
            lowMotionDurationMs=evidence.low_motion_duration_ms,
            classPersistenceMs=evidence.class_persistence_ms,
            visibility=evidence.visibility,
            visualState=evidence.visual_state,
            evidence=evidence.evidence,
            normalizedMovement=evidence.normalized_movement,
        )

    # -- status ----------------------------------------------------------- #

    @property
    def avg_inference_ms(self) -> float:
        if not self._inference_ms:
            return 0.0
        return sum(self._inference_ms) / len(self._inference_ms)

    @property
    def fps(self) -> float:
        return self.fps_meter.fps if self.fps_meter else 0.0

    def status(self) -> dict:
        return {
            "modelLoaded": self.model_loaded,
            "sourceAvailable": self.source_healthy,
            "source": self.settings.safe_source,
            "device": _device_label(self.thresholds),
            "fps": round(self.fps, 2),
            "avgInferenceMs": round(self.avg_inference_ms, 2),
            "activeTracks": len(self.engine.tracks),
            "latestFrameTimestamp": self.latest_frame_ts,
            "latestError": self.latest_error,
            "classNames": dict(self.detector.names) if self.detector else None,
        }


def _device_label(thresholds: dict) -> str:
    configured = str((thresholds.get("detection", {}) or {}).get("device", "auto"))
    if configured != "auto":
        return configured
    try:
        import torch

        return "cuda:0" if torch.cuda.is_available() else "cpu"
    except Exception:
        return configured


# --------------------------------------------------------------------------- #
# Shared runtime producer (video / camera modes)
# --------------------------------------------------------------------------- #


class Broadcaster:
    """Fan-out to bounded subscriber queues; drops oldest on overflow."""

    def __init__(self, maxsize: int = SUBSCRIBER_QUEUE_SIZE) -> None:
        self.maxsize = maxsize
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self.maxsize)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    def publish(self, frame: str) -> None:
        for queue in list(self._subscribers):
            if queue.full():
                # Slow client: drop its oldest event rather than block or grow.
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:  # pragma: no cover - race only
                    pass
            try:
                queue.put_nowait(frame)
            except asyncio.QueueFull:  # pragma: no cover - race only
                pass


class RuntimeProducer:
    """Owns the single capture+inference+state loop and publishes SSE frames."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.broadcaster = Broadcaster()
        self._task: asyncio.Task | None = None
        self._runtime = None  # app.runtime.CvRuntime, imported lazily
        self._stopping = False

    @property
    def runtime(self):
        return self._runtime

    async def start(self) -> None:
        if self._task is not None:
            return
        self._runtime = CvRuntime(self.settings)
        self._stopping = False
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stopping = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        if self._runtime is not None:
            await asyncio.to_thread(self._runtime.close)

    async def _run(self) -> None:
        runtime = self._runtime
        heartbeat_s, _ = event_intervals(self.settings)
        last_heartbeat = 0.0
        loop = asyncio.get_running_loop()

        try:
            await asyncio.to_thread(runtime.open)
        except Exception as exc:
            logger.error("CV runtime failed to start: %s", exc)
            runtime.record_error(str(exc))

        while not self._stopping:
            try:
                # Blocking capture+inference runs off the event loop.
                events = await asyncio.to_thread(runtime.step)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("CV runtime step failed")
                runtime.record_error(str(exc))
                events = []

            for event in events:
                self.broadcaster.publish(encode_sse(SseEvent.visual_evidence, event))

            now = loop.time()
            if now - last_heartbeat >= heartbeat_s:
                self.broadcaster.publish(encode_sse(SseEvent.heartbeat, heartbeat(self.settings)))
                last_heartbeat = now

            if not runtime.source_healthy:
                # Source failed or ended: keep the service responsive and keep
                # reporting CAMERA_UNAVAILABLE rather than spinning hot.
                await asyncio.sleep(0.5)
            else:
                await asyncio.sleep(0)  # yield to the loop

    async def stream(self) -> AsyncIterator[str]:
        """One subscriber's view of the shared producer."""
        queue = self.broadcaster.subscribe()
        try:
            yield encode_sse(SseEvent.heartbeat, heartbeat(self.settings))
            while True:
                frame = await queue.get()
                yield frame
        finally:
            self.broadcaster.unsubscribe(queue)


_producer: RuntimeProducer | None = None


def get_producer(settings: Settings) -> RuntimeProducer:
    global _producer
    if _producer is None:
        _producer = RuntimeProducer(settings)
    return _producer


async def shutdown_producer() -> None:
    global _producer
    if _producer is not None:
        await _producer.stop()
        _producer = None


def event_stream(settings: Settings) -> AsyncIterator[str]:
    """Mode-aware SSE stream: unchanged mock, or the shared runtime producer."""
    if settings.mode == "mock":
        return mock_event_stream(settings)
    return get_producer(settings).stream()
