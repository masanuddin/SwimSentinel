"""Tests for the shared producer, emission policy, and failure handling.

These never load a model or open a camera: the runtime is stubbed so the
orchestration contract can be tested deterministically.
"""

import asyncio
import json

import pytest

from app.config import Settings, redact_source
from app.pipeline import (
    Broadcaster,
    RuntimeProducer,
    encode_sse,
    event_stream,
    mock_event_stream,
)
from app.schemas import MotionState, Visibility, VisualEvidenceEvent, VisualState
from app.state import SseEvent, TrackEvidence


# -- mock mode isolation ---------------------------------------------------- #


def test_importing_app_does_not_load_detector_libraries():
    """Mock mode must never pull in OpenCV/Torch/Ultralytics."""
    import subprocess
    import sys
    from pathlib import Path

    script = (
        "import sys; import app.main; "
        "print([m for m in ('ultralytics','torch','cv2') if m in sys.modules])"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]"


def test_event_stream_uses_mock_stream_in_mock_mode():
    settings = Settings(CV_MODE="mock")
    stream = event_stream(settings)
    assert stream.__qualname__.startswith(mock_event_stream.__name__)


# -- credential redaction --------------------------------------------------- #


@pytest.mark.parametrize(
    "source, expected",
    [
        ("rtsp://user:secret@10.0.0.5/stream", "rtsp://***@10.0.0.5/stream"),
        ("rtsp://10.0.0.5/stream", "rtsp://10.0.0.5/stream"),
        ("0", "0"),
        ("C:/videos/pool.mp4", "C:/videos/pool.mp4"),
        (None, None),
    ],
)
def test_redact_source(source, expected):
    assert redact_source(source) == expected


def test_settings_safe_source_redacts_credentials():
    settings = Settings(CV_CAMERA_SOURCE="rtsp://admin:hunter2@cam.local/1")
    assert "hunter2" not in settings.safe_source
    assert settings.safe_source == "rtsp://***@cam.local/1"


# -- broadcaster ------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_broadcaster_fans_out_to_all_subscribers():
    broadcaster = Broadcaster()
    first = broadcaster.subscribe()
    second = broadcaster.subscribe()

    broadcaster.publish("payload")

    assert await first.get() == "payload"
    assert await second.get() == "payload"


@pytest.mark.asyncio
async def test_broadcaster_drops_oldest_when_subscriber_is_slow():
    """A stalled client must never block the producer or grow without bound."""
    broadcaster = Broadcaster(maxsize=3)
    queue = broadcaster.subscribe()

    for index in range(10):
        broadcaster.publish(f"event-{index}")

    assert queue.qsize() == 3
    # Oldest were dropped; the newest survive.
    drained = [queue.get_nowait() for _ in range(3)]
    assert drained == ["event-7", "event-8", "event-9"]


@pytest.mark.asyncio
async def test_broadcaster_unsubscribe_stops_delivery():
    broadcaster = Broadcaster()
    queue = broadcaster.subscribe()
    broadcaster.unsubscribe(queue)
    broadcaster.publish("payload")
    assert broadcaster.subscriber_count == 0
    assert queue.empty()


@pytest.mark.asyncio
async def test_stream_unsubscribes_on_client_disconnect():
    producer = RuntimeProducer(Settings(CV_MODE="video"))
    stream = producer.stream()
    await anext(stream)  # initial heartbeat -> subscribed
    assert producer.broadcaster.subscriber_count == 1
    await stream.aclose()  # client disconnects
    assert producer.broadcaster.subscriber_count == 0


# -- single shared producer ------------------------------------------------- #


@pytest.mark.asyncio
async def test_all_subscribers_share_one_producer_and_runtime():
    settings = Settings(CV_MODE="video")
    producer = RuntimeProducer(settings)
    first = producer.stream()
    second = producer.stream()
    await anext(first)
    await anext(second)
    # Two clients, one broadcaster, one runtime -> one camera + one model.
    assert producer.broadcaster.subscriber_count == 2
    assert producer.runtime is None  # not started: no model/camera touched yet
    await first.aclose()
    await second.aclose()


# -- serialization ---------------------------------------------------------- #


def test_encode_sse_formats_named_event():
    event = VisualEvidenceEvent(
        timestamp="2026-01-01T00:00:00Z",
        cameraId="POOL-CAM-01",
        trackId=3,
        zoneId=2,
        rawClass="distress_candidate",
        detectionConfidence=0.81,
        motionState="low",
        lowMotionDurationMs=3200,
        classPersistenceMs=2000,
        visibility="clear",
        visualState="suspected_distress",
        evidence=["persistent_distress_appearance"],
        normalizedMovement=0.004,
    )
    frame = encode_sse(SseEvent.visual_evidence, event)
    assert frame.startswith("event: visual_evidence\ndata: ")
    assert frame.endswith("\n\n")
    payload = json.loads(frame.split("data: ", 1)[1].strip())
    assert payload["visualState"] == "suspected_distress"
    assert payload["normalizedMovement"] == 0.004


def test_camera_unavailable_event_serializes_with_null_track_and_zone():
    """States without a track/zone must still satisfy the schema."""
    event = VisualEvidenceEvent(
        timestamp="2026-01-01T00:00:00Z",
        cameraId="POOL-CAM-01",
        motionState="unknown",
        lowMotionDurationMs=0,
        classPersistenceMs=0,
        visibility="unavailable",
        visualState="camera_unavailable",
        evidence=["capture_source_unavailable"],
    )
    payload = json.loads(event.model_dump_json())
    assert payload["trackId"] is None
    assert payload["zoneId"] is None
    assert payload["rawClass"] is None
    assert payload["visualState"] == "camera_unavailable"


# -- emission policy -------------------------------------------------------- #


class StubRuntime:
    """Minimal CvRuntime stand-in exercising only the emission policy."""

    def __init__(self, settings):
        from app.pipeline import CvRuntime

        self.settings = settings
        self.periodic_event_s = 2.0
        self.min_event_interval_s = 0.4
        self._last_emitted = {}
        self._to_event = lambda ev: CvRuntime._to_event(self, ev)
        self.camera_id = settings.camera_id
        self._emit = lambda evidences, now: CvRuntime._emit(self, evidences, now)


def evidence(state: VisualState, track_id: int = 1) -> TrackEvidence:
    return TrackEvidence(
        track_id=track_id,
        zone_id=1,
        raw_class="normal_swimming",
        detection_confidence=0.8,
        motion_state=MotionState.normal,
        normalized_movement=0.5,
        low_motion_duration_ms=0,
        class_persistence_ms=500,
        visibility=Visibility.clear,
        visual_state=state,
        evidence=["normal_swimming_appearance"],
    )


def test_emits_first_observation_then_stays_quiet():
    runtime = StubRuntime(Settings())
    assert len(runtime._emit([evidence(VisualState.normal)], 100.0)) == 1
    # Unchanged state well inside the periodic window -> no event per frame.
    assert runtime._emit([evidence(VisualState.normal)], 100.1) == []
    assert runtime._emit([evidence(VisualState.normal)], 101.0) == []


def test_emits_on_state_change():
    runtime = StubRuntime(Settings())
    runtime._emit([evidence(VisualState.normal)], 100.0)
    events = runtime._emit([evidence(VisualState.suspected_distress)], 100.5)
    assert len(events) == 1
    assert events[0].visualState is VisualState.suspected_distress


def test_state_change_respects_min_event_interval():
    """Rapid flip-flop cannot flood the stream."""
    runtime = StubRuntime(Settings())
    runtime._emit([evidence(VisualState.normal)], 100.0)
    assert runtime._emit([evidence(VisualState.watch)], 100.1) == []


def test_periodic_refresh_for_unchanged_state():
    runtime = StubRuntime(Settings())
    runtime._emit([evidence(VisualState.normal)], 100.0)
    assert runtime._emit([evidence(VisualState.normal)], 101.0) == []
    assert len(runtime._emit([evidence(VisualState.normal)], 102.1)) == 1


def test_disappeared_track_is_forgotten_by_emitter():
    runtime = StubRuntime(Settings())
    runtime._emit([evidence(VisualState.normal, track_id=1)], 100.0)
    runtime._emit([], 100.5)
    assert runtime._last_emitted == {}


def test_tracks_emit_independently():
    runtime = StubRuntime(Settings())
    runtime._emit([evidence(VisualState.normal, track_id=1)], 100.0)
    events = runtime._emit(
        [evidence(VisualState.normal, track_id=1), evidence(VisualState.normal, track_id=2)],
        100.5,
    )
    assert [e.trackId for e in events] == [2]


# -- prerecorded playback pacing ------------------------------------------- #


class FakeSource:
    def __init__(self, declared_fps: float):
        self.declared_fps = declared_fps


def make_pacer(mode: str, realtime: bool, declared_fps: float):
    """A CvRuntime with only the fields _pace_playback touches."""
    from app.pipeline import CvRuntime

    runtime = object.__new__(CvRuntime)
    runtime.settings = Settings(CV_MODE=mode, CV_VIDEO_REALTIME=realtime)
    runtime.source = FakeSource(declared_fps)
    runtime._playback_start = None
    runtime._playback_frames = 0
    return runtime


def test_video_mode_paces_playback_to_source_fps():
    """A file must not replay faster than real time, or persistence gates break."""
    import time

    runtime = make_pacer("video", realtime=True, declared_fps=50.0)
    started = time.monotonic()
    for _ in range(5):
        runtime._pace_playback()
    elapsed = time.monotonic() - started
    # 5 frames at 50 FPS ~= 0.1s; without pacing this loop is ~instant.
    assert elapsed >= 0.07


def test_pacing_disabled_runs_at_full_speed():
    import time

    runtime = make_pacer("video", realtime=False, declared_fps=50.0)
    started = time.monotonic()
    for _ in range(5):
        runtime._pace_playback()
    assert time.monotonic() - started < 0.02


def test_camera_mode_is_never_paced():
    """A live camera already delivers frames in real time."""
    import time

    runtime = make_pacer("camera", realtime=True, declared_fps=50.0)
    started = time.monotonic()
    for _ in range(5):
        runtime._pace_playback()
    assert time.monotonic() - started < 0.02


def test_pacing_skipped_when_source_fps_unknown():
    import time

    runtime = make_pacer("video", realtime=True, declared_fps=0.0)
    started = time.monotonic()
    for _ in range(5):
        runtime._pace_playback()
    assert time.monotonic() - started < 0.02


# -- failure handling ------------------------------------------------------- #


@pytest.mark.asyncio
async def test_producer_records_error_when_runtime_open_fails(monkeypatch):
    """A model/source failure must surface, not crash the service."""
    settings = Settings(CV_MODE="video", CV_CAMERA_SOURCE="missing.mp4")
    producer = RuntimeProducer(settings)

    class FailingRuntime:
        source_healthy = False

        def __init__(self, _settings):
            self.errors = []

        def open(self):
            raise RuntimeError("could not open capture source: missing.mp4")

        def step(self):
            return []

        def record_error(self, message):
            self.errors.append(message)

        def close(self):
            pass

    monkeypatch.setattr("app.pipeline.CvRuntime", FailingRuntime)
    await producer.start()
    await asyncio.sleep(0.05)
    assert producer.runtime.errors
    assert "missing.mp4" in producer.runtime.errors[0]
    await producer.stop()
