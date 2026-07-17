"""Runtime evaluation: pipeline behaviour, FPS, and state transitions.

IMPORTANT — what this does and does not measure
------------------------------------------------
No real pool footage and no physical camera were available on this machine, and
the dataset's per-clip frame numbering is NOT a reliable temporal ordinal
(images sharing a "frame index" are different images), so real source clips
cannot be honestly reconstructed in temporal order.

This harness therefore builds **explicitly constructed** clips from *real*
test-split images with *controlled synthetic motion*:

* detections, tracking, FPS and latency are real (real model, real frames, real GPU);
* the temporal composition (how frames are ordered, panned, or blanked) is synthetic.

That makes this a valid test of the *pipeline* — tracking, zones, normalized
motion, temporal persistence, hysteresis, failure handling — and NOT a test of
detector generalization to a real pool (see the detector evaluation for
detector metrics; live-camera generalization remains unknown).

Scenarios needing genuinely continuous real footage or live hardware are
reported as NOT EXECUTED by the report, never faked here.

Usage (from the repository root):

    cv-service\\.venv\\Scripts\\python.exe cv-service\\evaluation\\run_runtime_eval.py
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

EVALUATION_DIR = Path(__file__).resolve().parent
CV_SERVICE_ROOT = EVALUATION_DIR.parent
if str(CV_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(CV_SERVICE_ROOT))

from app.config import Settings  # noqa: E402
from app.pipeline import CvRuntime  # noqa: E402
from app.schemas import VisualState  # noqa: E402
from app.vision import draw_overlay  # noqa: E402

DATASET_TEST = (
    CV_SERVICE_ROOT / "data" / "raw" / "Drowning Detection.v1i.yolov11" / "test" / "images"
)
CLIPS_DIR = CV_SERVICE_ROOT / "runs" / "eval-clips"
OVERLAY_DIR = CV_SERVICE_ROOT / "runs" / "eval-overlays"
REPORT_JSON = EVALUATION_DIR / "runtime_evaluation.json"

# Real test-split images used as the visual content of the harness clips.
SRC_DISTRESS = "105_png_jpg.rf.27bcf89f23d1d9c49305b4c4e2c806bd.jpg"
SRC_NORMAL = "10415_jpg.rf.de1549240937f0596f7c92f8fa6d6e15.jpg"
SRC_MULTI = "-Clipchamp-_mp4-37_jpg.rf.677b0c9b6b7caf20036b624a59a530e1.jpg"

FPS = 25
FINAL_STATES = {VisualState.suspected_distress, VisualState.suspected_inactivity}


# --------------------------------------------------------------------------- #
# Clip construction
# --------------------------------------------------------------------------- #


def load_source(name: str):
    path = DATASET_TEST / name
    image = cv2.imread(str(path))
    if image is None:
        raise SystemExit(f"source image unreadable: {path}")
    return image


def pan(image, dx: float, dy: float):
    matrix = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(image, matrix, (image.shape[1], image.shape[0]))


def sweep(index: int, amplitude: float = 30.0, period: int = 100) -> float:
    """Continuous back-and-forth offset (triangle wave).

    A sawtooth (index % period) teleports the subject on wraparound, which
    breaks ByteTrack and would make the harness, not the pipeline, look like
    it is losing tracks. A triangle wave keeps motion continuous.
    """
    phase = (index % period) / period
    return amplitude * (2.0 * abs(2.0 * phase - 1.0) - 1.0)


def write_clip(frames, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    height, width = frames[0].shape[:2]
    writer = cv2.VideoWriter(
        str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (width, height)
    )
    for frame in frames:
        writer.write(frame)
    writer.release()
    return out_path


def build_clips() -> dict[str, Path]:
    """Construct the harness clips. Returns scenario -> clip path."""
    distress = load_source(SRC_DISTRESS)
    normal = load_source(SRC_NORMAL)
    multi = load_source(SRC_MULTI)
    blank = np.zeros_like(distress)

    clips: dict[str, Path] = {}

    # Static real distress frame: zero motion -> exercises inactivity + distress.
    clips["PERSISTENT_DISTRESS_APPEARANCE"] = write_clip(
        [distress.copy() for _ in range(FPS * 8)], CLIPS_DIR / "persistent_distress.mp4"
    )

    # Moving normal swimmer: the real false-alarm test (must stay NORMAL).
    clips["NORMAL_SWIMMING"] = write_clip(
        [pan(normal, sweep(index), 0) for index in range(FPS * 8)],
        CLIPS_DIR / "normal_swimming.mp4",
    )

    # Empty scene: no pool, no people.
    clips["EMPTY_SCENE"] = write_clip(
        [blank.copy() for _ in range(FPS * 6)], CLIPS_DIR / "empty_scene.mp4"
    )

    # Brief suspicious appearance: normal -> 0.4s distress -> normal.
    brief = (
        [pan(normal, sweep(index), 0) for index in range(FPS * 3)]
        + [distress.copy() for _ in range(int(FPS * 0.4))]
        + [pan(normal, sweep(index + FPS * 3), 0) for index in range(FPS * 4)]
    )
    clips["BRIEF_SUSPICIOUS_APPEARANCE"] = write_clip(
        brief, CLIPS_DIR / "brief_suspicious.mp4"
    )

    # Prolonged low movement on a swimmer that is NOT distress-classified.
    clips["PROLONGED_LOW_MOVEMENT"] = write_clip(
        [normal.copy() for _ in range(FPS * 8)], CLIPS_DIR / "prolonged_low_movement.mp4"
    )

    # Temporary track loss: subject disappears for ~2s, then returns.
    loss = (
        [distress.copy() for _ in range(FPS * 3)]
        + [blank.copy() for _ in range(FPS * 2)]
        + [distress.copy() for _ in range(FPS * 3)]
    )
    clips["TEMPORARY_TRACK_LOSS"] = write_clip(loss, CLIPS_DIR / "temporary_track_loss.mp4")

    # Two swimmers: a real multi-object frame.
    clips["TWO_SWIMMERS"] = write_clip(
        [pan(multi, sweep(index, amplitude=16.0), 0) for index in range(FPS * 6)],
        CLIPS_DIR / "two_swimmers.mp4",
    )

    # Camera disconnect: a short clip that simply ends (source becomes unavailable).
    clips["CAMERA_DISCONNECT"] = write_clip(
        [distress.copy() for _ in range(FPS * 2)], CLIPS_DIR / "camera_disconnect.mp4"
    )
    return clips


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #


@dataclass
class ScenarioResult:
    scenario: str
    clip: str
    frames: int = 0
    # Level A: raw frame-level detections
    raw_detection_frames: int = 0
    raw_suspicious_frames: int = 0
    raw_detections: int = 0
    # Level B: + ByteTrack
    unique_tracks: int = 0
    max_concurrent_tracks: int = 0
    track_lost_events: int = 0
    # Level C: + temporal state
    watch_transitions: int = 0
    final_distress_states: int = 0
    final_inactivity_states: int = 0
    state_changes: int = 0
    states_seen: list = field(default_factory=list)
    escalation_latency_s: float | None = None
    recovery_latency_s: float | None = None
    camera_unavailable_latency_s: float | None = None
    zone_changes: int = 0
    # Performance
    avg_fps: float = 0.0
    min_fps: float = 0.0
    median_frame_ms: float = 0.0
    p95_frame_ms: float = 0.0
    avg_inference_ms: float = 0.0
    events_emitted: int = 0


def evaluate(scenario: str, clip: Path, save_overlay: bool = True,
             realtime: bool = True) -> ScenarioResult:
    # Real-time pacing is what a camera does, so temporal states are only
    # meaningful with it on. Turn it off to measure raw throughput.
    settings = Settings(
        CV_MODE="video", CV_CAMERA_SOURCE=str(clip), CV_LOOP_VIDEO=False,
        CV_VIDEO_REALTIME=realtime,
    )
    runtime = CvRuntime(settings)
    runtime.open()

    result = ScenarioResult(scenario=scenario, clip=clip.name)
    evidence_conf = runtime.engine.config.evidence_confidence

    frame_ms: list[float] = []
    seen_tracks: set[int] = set()
    last_states: dict[int, str] = {}
    last_zones: dict[int, int | None] = {}
    first_frame_t: float | None = None
    escalated_at: float | None = None
    recovered_at: float | None = None
    unavailable_at: float | None = None
    last_good_frame_t: float | None = None
    writer = None

    while True:
        started = time.perf_counter()
        events = runtime.step()
        frame_ms.append((time.perf_counter() - started) * 1000.0)
        result.events_emitted += len(events)

        if runtime.source_ended:
            # Source finished: record how quickly unavailability surfaced, then stop.
            unavailable_at = time.perf_counter()
            if last_good_frame_t is not None:
                result.camera_unavailable_latency_s = round(
                    unavailable_at - last_good_frame_t, 3
                )
            for event in events:
                if (
                    event.visualState is VisualState.camera_unavailable
                    and "camera_unavailable" not in result.states_seen
                ):
                    result.states_seen.append("camera_unavailable")
            break

        result.frames += 1
        now = time.perf_counter()
        first_frame_t = first_frame_t if first_frame_t is not None else now
        last_good_frame_t = now

        # -- Level A: raw detections (no tracking, no temporal logic) --
        detections = runtime.last_detections
        result.raw_detections += len(detections)
        if detections:
            result.raw_detection_frames += 1
        if any(
            d.class_name == "distress_candidate" and d.confidence >= evidence_conf
            for d in detections
        ):
            result.raw_suspicious_frames += 1

        # -- Level B: tracking --
        frame_tracks = {d.track_id for d in detections if d.track_id is not None}
        seen_tracks |= frame_tracks
        result.max_concurrent_tracks = max(result.max_concurrent_tracks, len(frame_tracks))

        # -- Level C: temporal state --
        for evidence in runtime.engine.update(time.monotonic()):
            track_id = evidence.track_id
            if track_id is None:
                continue
            state = evidence.visual_state.value
            previous = last_states.get(track_id)
            if previous != state:
                result.state_changes += 1
                if state not in result.states_seen:
                    result.states_seen.append(state)
                if state == VisualState.watch.value:
                    result.watch_transitions += 1
                if evidence.visual_state is VisualState.suspected_distress:
                    result.final_distress_states += 1
                if evidence.visual_state is VisualState.suspected_inactivity:
                    result.final_inactivity_states += 1
                if evidence.visual_state is VisualState.track_lost:
                    result.track_lost_events += 1
                if evidence.visual_state in FINAL_STATES and escalated_at is None:
                    escalated_at = now
                    result.escalation_latency_s = round(now - first_frame_t, 3)
                if (
                    previous in {s.value for s in FINAL_STATES}
                    and state == VisualState.normal.value
                    and recovered_at is None
                ):
                    recovered_at = now
                last_states[track_id] = state

            if last_zones.get(track_id, evidence.zone_id) != evidence.zone_id:
                result.zone_changes += 1
            last_zones[track_id] = evidence.zone_id

        if save_overlay and runtime.last_frame is not None:
            OVERLAY_DIR.mkdir(parents=True, exist_ok=True)
            annotated = draw_overlay(
                runtime.last_frame, detections, runtime.last_evidence,
                runtime._scaled_zones, runtime.fps, [scenario],
            )
            if writer is None:
                height, width = annotated.shape[:2]
                writer = cv2.VideoWriter(
                    str(OVERLAY_DIR / f"{scenario.lower()}.mp4"),
                    cv2.VideoWriter_fourcc(*"mp4v"), FPS, (width, height),
                )
            writer.write(annotated)

    if writer is not None:
        writer.release()

    result.unique_tracks = len(seen_tracks)
    result.avg_inference_ms = round(runtime.avg_inference_ms, 2)
    if frame_ms:
        result.median_frame_ms = round(statistics.median(frame_ms), 2)
        ordered = sorted(frame_ms)
        result.p95_frame_ms = round(ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))], 2)
        result.avg_fps = round(1000.0 / statistics.mean(frame_ms), 2)
        result.min_fps = round(1000.0 / max(frame_ms), 2)
    runtime.close()
    return result


def evaluate_bad_source() -> dict:
    """A source that cannot be opened must report CAMERA_UNAVAILABLE, not NORMAL."""
    settings = Settings(CV_MODE="video", CV_CAMERA_SOURCE=str(CLIPS_DIR / "does_not_exist.mp4"))
    runtime = CvRuntime(settings)
    outcome = {"scenario": "MISSING_SOURCE", "opened": True, "error": None, "state": None}
    try:
        runtime.open()
    except Exception as exc:
        outcome["opened"] = False
        outcome["error"] = str(exc).splitlines()[0]
        runtime.record_error(str(exc))
    events = runtime.step()
    outcome["state"] = events[0].visualState.value if events else None
    runtime.close()
    return outcome


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-overlay", action="store_true")
    args = parser.parse_args(argv)

    print("Building harness clips from real test-split images...")
    clips = build_clips()

    results = []
    for scenario, clip in clips.items():
        print(f"  evaluating {scenario} (real-time paced) ...", flush=True)
        result = evaluate(scenario, clip, save_overlay=not args.no_overlay, realtime=True)
        results.append(result)

    # Throughput headroom: same pipeline, pacing disabled.
    print("  measuring unpaced throughput ...", flush=True)
    throughput = evaluate(
        "THROUGHPUT", clips["NORMAL_SWIMMING"], save_overlay=False, realtime=False
    )

    bad_source = evaluate_bad_source()

    report = {
        "harness_disclosure": (
            "Detections, tracking, FPS and latency are real (real model, real "
            "test-split frames, real GPU). Temporal composition (ordering, "
            "synthetic pan, blank frames) is CONSTRUCTED: no real pool footage "
            "and no physical camera were available, and the dataset's per-clip "
            "frame numbering is not a reliable temporal ordinal. This validates "
            "the pipeline, not detector generalization to a real pool."
        ),
        "content_caveat": (
            "Source images come from the test split, but ~80% of each source "
            "video's frames are in the training split, so detection quality on "
            "this visual content is optimistic."
        ),
        "pacing_note": (
            "Scenarios run with real-time pacing (CV_VIDEO_REALTIME=1), which is "
            "how the prerecorded fallback behaves in the demo and how a camera "
            "delivers frames; temporal states are only meaningful under it. "
            "'throughput_unpaced' re-runs the same pipeline with pacing off to "
            "show FPS headroom on this GPU."
        ),
        "scenarios": [vars(r) for r in results],
        "throughput_unpaced": vars(throughput),
        "missing_source": bad_source,
        "not_executed": {
            "LIVE_CAMERA": "no physical camera on this host (probed indices 0-2)",
            "REAL_POOL_FOOTAGE": "requires continuous video of the actual demo pool",
            "CAMERA_DISCONNECT_MIDSTREAM": (
                "requires physically unplugging a live camera; end-of-file "
                "unavailability was tested instead"
            ),
        },
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"\n{'scenario':<32}{'fps':>6}{'infer':>7}{'A:susp':>9}{'trk':>4}{'esc_s':>7}  states")
    for result in results:
        escalation = f"{result.escalation_latency_s:.1f}" if result.escalation_latency_s else "-"
        print(
            f"{result.scenario:<32}{result.avg_fps:>6.1f}{result.avg_inference_ms:>7.1f}"
            f"{result.raw_suspicious_frames:>5}/{result.frames:<3}{result.unique_tracks:>4}"
            f"{escalation:>7}  {','.join(result.states_seen) or '-'}"
        )
    print(
        f"\nunpaced throughput: {throughput.avg_fps:.1f} FPS "
        f"(inference {throughput.avg_inference_ms:.1f} ms, p95 frame {throughput.p95_frame_ms:.1f} ms)"
    )
    print(f"missing source -> {bad_source}")
    print(f"\nWrote {REPORT_JSON.relative_to(CV_SERVICE_ROOT.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
