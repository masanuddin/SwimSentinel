"""Tests for history, motion, and the temporal visual-state engine.

Time is injected explicitly (monotonic seconds), so these scenarios run
instantly and deterministically without sleeping or a real camera.
"""

import pytest

from app.schemas import MotionState, VisualState
from app.state import (
    EngineConfig,
    MotionConfig,
    StateConfig,
    TemporalStateEngine,
    TrackHistory,
    TrackSample,
)

CONFIG = EngineConfig(
    history_window_ms=5000,
    track_lost_timeout_ms=1500,
    track_expiry_ms=8000,
    evidence_confidence=0.35,
    motion=MotionConfig(
        smoothing_window_ms=800,
        displacement_window_ms=1000,
        low_motion_ratio_per_sec=0.02,
        inactivity_ms=3000,
        min_box_diagonal_px=12,
    ),
    state=StateConfig(
        watch_min_ms=300,
        distress_persistence_ms=1800,
        inactivity_persistence_ms=3000,
        recovery_ms=1500,
    ),
)

DIAGONAL = 100.0
STEP = 0.1  # 10 FPS


def feed(
    engine: TemporalStateEngine,
    *,
    start: float,
    duration: float,
    class_name: str,
    confidence: float = 0.9,
    zone_id: int | None = 1,
    track_id: int = 1,
    speed_px_per_s: float = 0.0,
    step: float = STEP,
    x0: float = 100.0,
):
    """Feed frames for `duration` seconds; returns the last timestamp used."""
    t = start
    end = start + duration
    while t <= end + 1e-9:
        x = x0 + speed_px_per_s * (t - start)
        engine.observe(
            track_id=track_id,
            now=t,
            centroid=(x, 200.0),
            diagonal=DIAGONAL,
            class_name=class_name,
            confidence=confidence,
            zone_id=zone_id,
            in_roi=zone_id is not None,
        )
        engine.update(t)
        t += step
    return t - step


def state_of(engine: TemporalStateEngine, now: float, track_id: int = 1) -> VisualState:
    for evidence in engine.update(now):
        if evidence.track_id == track_id:
            return evidence.visual_state
    raise AssertionError(f"track {track_id} not present")


# -- history / motion ------------------------------------------------------ #


def test_history_is_bounded_by_window():
    history = TrackHistory(window_ms=1000)
    for index in range(50):
        history.add(TrackSample(index * 0.1, (0.0, 0.0), 10.0, "normal_swimming", 0.9, 1, True))
    assert history.span_s <= 1.0 + 1e-9
    assert len(history.samples) <= 11


def test_smoothing_averages_trailing_window():
    history = TrackHistory(window_ms=5000)
    for index in range(11):
        # x jumps between 0 and 10 -> smoothed value sits in the middle.
        history.add(
            TrackSample(index * 0.1, (0.0 if index % 2 else 10.0, 0.0), 50.0,
                        "normal_swimming", 0.9, 1, True)
        )
    smoothed = history.smoothed_centroid_at(1.0, 0.5)
    assert smoothed is not None
    assert 3.0 <= smoothed[0] <= 7.0


def test_normalized_movement_scales_with_box_size():
    """Same pixel speed on a bigger body = smaller normalized movement."""

    def movement(diagonal: float) -> float:
        history = TrackHistory(window_ms=5000)
        t = 0.0
        while t <= 3.0 + 1e-9:
            history.add(TrackSample(t, (100.0 * t, 0.0), diagonal, "normal_swimming", 0.9, 1, True))
            t += 0.1
        return history.normalized_movement(3.0, CONFIG.motion)

    small = movement(50.0)
    large = movement(200.0)
    assert small is not None and large is not None
    # 100 px/s over a 50px body is 4x the normalized motion of a 200px body.
    assert small == pytest.approx(large * 4, rel=0.15)


def test_normalized_movement_unknown_without_enough_history():
    history = TrackHistory(window_ms=5000)
    history.add(TrackSample(0.0, (0.0, 0.0), 50.0, "normal_swimming", 0.9, 1, True))
    assert history.normalized_movement(0.1, CONFIG.motion) is None


def test_normalized_movement_unknown_for_tiny_boxes():
    history = TrackHistory(window_ms=5000)
    t = 0.0
    while t <= 3.0 + 1e-9:
        history.add(TrackSample(t, (0.0, 0.0), 5.0, "normal_swimming", 0.9, 1, True))
        t += 0.1
    # Below min_box_diagonal_px -> unmeasurable, never reported as low motion.
    assert history.normalized_movement(3.0, CONFIG.motion) is None


def test_stationary_track_reports_low_motion_not_unknown():
    engine = TemporalStateEngine(CONFIG)
    end = feed(engine, start=0.0, duration=2.0, class_name="normal_swimming", speed_px_per_s=0.0)
    evidence = engine.update(end)[0]
    assert evidence.motion_state is MotionState.low
    assert evidence.normalized_movement == pytest.approx(0.0, abs=1e-6)


# -- required state scenarios ---------------------------------------------- #


def test_single_suspicious_frame_produces_watch_only():
    engine = TemporalStateEngine(CONFIG)
    engine.observe(1, 0.0, (100.0, 200.0), DIAGONAL, "distress_candidate", 0.9, 1, True)
    engine.update(0.0)
    # One frame cannot reach WATCH yet (needs watch_min_ms), and certainly not distress.
    assert state_of(engine, 0.0) is VisualState.normal
    engine.observe(1, 0.4, (100.0, 200.0), DIAGONAL, "distress_candidate", 0.9, 1, True)
    assert state_of(engine, 0.4) is VisualState.watch
    # Still only WATCH well before distress_persistence_ms.
    engine.observe(1, 1.0, (100.0, 200.0), DIAGONAL, "distress_candidate", 0.9, 1, True)
    assert state_of(engine, 1.0) is VisualState.watch


def test_persistent_distress_produces_suspected_distress():
    engine = TemporalStateEngine(CONFIG)
    # Move fast enough that inactivity never triggers first.
    end = feed(engine, start=0.0, duration=2.0, class_name="distress_candidate",
               speed_px_per_s=30.0)
    assert state_of(engine, end) is VisualState.suspected_distress


def test_brief_distress_then_stable_normal_returns_to_normal():
    engine = TemporalStateEngine(CONFIG)
    end = feed(engine, start=0.0, duration=0.6, class_name="distress_candidate",
               speed_px_per_s=30.0)
    assert state_of(engine, end) is VisualState.watch

    # Normal evidence resumes; recovery is hysteretic, not instant.
    end2 = feed(engine, start=end + STEP, duration=0.5, class_name="normal_swimming",
                speed_px_per_s=30.0, x0=200.0)
    assert state_of(engine, end2) is VisualState.watch

    end3 = feed(engine, start=end2 + STEP, duration=1.6, class_name="normal_swimming",
                speed_px_per_s=30.0, x0=300.0)
    assert state_of(engine, end3) is VisualState.normal


def test_persistent_low_movement_produces_suspected_inactivity():
    engine = TemporalStateEngine(CONFIG)
    end = feed(engine, start=0.0, duration=5.0, class_name="normal_swimming",
               speed_px_per_s=0.0)
    assert state_of(engine, end) is VisualState.suspected_inactivity


def test_inactivity_escalation_latency_includes_motion_warmup():
    """Pin the real inactivity latency: motion warm-up + persistence.

    Normalized movement cannot be measured until history spans
    displacement_window (1.0s) + smoothing_window (0.8s) = 1.8s. Only then can
    low-motion duration start accruing toward inactivity_persistence_ms (3.0s),
    so escalation lands at ~4.8s, not 3.0s. Before the warm-up, movement is
    unknown - and unknown is never treated as low motion.
    """
    engine = TemporalStateEngine(CONFIG)

    feed(engine, start=0.0, duration=1.5, class_name="normal_swimming", speed_px_per_s=0.0)
    # Still warming up: motion unknown, so no inactivity clock yet.
    assert engine.tracks[1].low_motion_since is None
    assert state_of(engine, 1.5) is VisualState.normal

    feed(engine, start=1.6, duration=2.6, class_name="normal_swimming", speed_px_per_s=0.0)
    assert state_of(engine, 4.2) is VisualState.normal  # ~2.4s of low motion

    end = feed(engine, start=4.3, duration=0.7, class_name="normal_swimming",
               speed_px_per_s=0.0)
    assert state_of(engine, end) is VisualState.suspected_inactivity  # ~4.8s


def test_one_missed_frame_retains_track():
    engine = TemporalStateEngine(CONFIG)
    feed(engine, start=0.0, duration=1.0, class_name="normal_swimming", speed_px_per_s=30.0)
    # A single dropped frame (0.1s < track_lost_timeout_ms) keeps the track.
    assert state_of(engine, 1.1) is not VisualState.track_lost
    assert 1 in engine.tracks


def test_prolonged_missing_track_produces_track_lost():
    engine = TemporalStateEngine(CONFIG)
    feed(engine, start=0.0, duration=1.0, class_name="normal_swimming", speed_px_per_s=30.0)
    assert state_of(engine, 1.0 + 1.6) is VisualState.track_lost


def test_stale_track_is_cleaned_up():
    engine = TemporalStateEngine(CONFIG)
    feed(engine, start=0.0, duration=1.0, class_name="normal_swimming", speed_px_per_s=30.0)
    engine.update(1.0 + 8.5)  # beyond track_expiry_ms
    assert engine.tracks == {}


def test_source_failure_produces_camera_unavailable():
    engine = TemporalStateEngine(CONFIG)
    feed(engine, start=0.0, duration=1.0, class_name="normal_swimming", speed_px_per_s=30.0)
    engine.set_source_healthy(False)
    evidences = engine.update(1.1)
    assert len(evidences) == 1
    assert evidences[0].visual_state is VisualState.camera_unavailable
    assert evidences[0].track_id is None
    assert evidences[0].zone_id is None


def test_camera_failure_is_never_reported_as_normal():
    engine = TemporalStateEngine(CONFIG)
    engine.set_source_healthy(False)
    assert all(e.visual_state is not VisualState.normal for e in engine.update(0.0))


def test_out_of_water_does_not_escalate_inactivity():
    engine = TemporalStateEngine(CONFIG)
    # A motionless person on the deck for well over inactivity_persistence_ms.
    end = feed(engine, start=0.0, duration=5.0, class_name="out_of_water", speed_px_per_s=0.0)
    assert state_of(engine, end) is VisualState.normal


def test_out_of_roi_track_does_not_escalate():
    engine = TemporalStateEngine(CONFIG)
    end = feed(engine, start=0.0, duration=5.0, class_name="distress_candidate",
               zone_id=None, speed_px_per_s=0.0)
    assert state_of(engine, end) is VisualState.normal


# -- confidence gating ----------------------------------------------------- #


def test_low_confidence_keeps_track_but_never_escalates():
    engine = TemporalStateEngine(CONFIG)
    # Below evidence_confidence (0.35) but above tracking admission.
    end = feed(engine, start=0.0, duration=3.0, class_name="distress_candidate",
               confidence=0.20, speed_px_per_s=30.0)
    assert 1 in engine.tracks  # track stayed alive
    assert state_of(engine, end) is VisualState.normal  # but produced no evidence


def test_confident_distress_after_low_confidence_escalates_normally():
    engine = TemporalStateEngine(CONFIG)
    feed(engine, start=0.0, duration=1.0, class_name="distress_candidate",
         confidence=0.20, speed_px_per_s=30.0)
    end = feed(engine, start=1.1, duration=2.0, class_name="distress_candidate",
               confidence=0.90, speed_px_per_s=30.0, x0=200.0)
    assert state_of(engine, end) is VisualState.suspected_distress


# -- hysteresis ------------------------------------------------------------ #


def test_distress_holds_through_brief_normal_flicker():
    engine = TemporalStateEngine(CONFIG)
    end = feed(engine, start=0.0, duration=2.0, class_name="distress_candidate",
               speed_px_per_s=30.0)
    assert state_of(engine, end) is VisualState.suspected_distress
    # A brief normal misclassification must not immediately clear the state.
    end2 = feed(engine, start=end + STEP, duration=0.5, class_name="normal_swimming",
                speed_px_per_s=30.0, x0=500.0)
    assert state_of(engine, end2) is VisualState.suspected_distress


def test_multiple_tracks_are_independent():
    engine = TemporalStateEngine(CONFIG)
    feed(engine, start=0.0, duration=2.0, class_name="distress_candidate",
         track_id=1, speed_px_per_s=30.0)
    feed(engine, start=0.0, duration=2.0, class_name="normal_swimming",
         track_id=2, zone_id=2, speed_px_per_s=30.0)
    assert state_of(engine, 2.0, track_id=1) is VisualState.suspected_distress
    assert state_of(engine, 2.0, track_id=2) is VisualState.normal


def test_variable_frame_rate_uses_elapsed_time_not_frame_count():
    """Only 3 frames over 2s still escalates: timing drives the state, not FPS."""
    engine = TemporalStateEngine(CONFIG)
    for t in (0.0, 1.0, 2.0):
        engine.observe(1, t, (100.0 + 30 * t, 200.0), DIAGONAL,
                       "distress_candidate", 0.9, 1, True)
        engine.update(t)
    assert state_of(engine, 2.0) is VisualState.suspected_distress
