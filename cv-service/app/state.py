"""Temporal reasoning over tracked detections.

Owns bounded per-track history, centroid smoothing, normalized movement,
inactivity duration, class persistence, hysteresis/recovery, stale-track
cleanup, and the temporal visual-state transitions.

Design rules:

* A single suspicious frame can only ever produce WATCH. Escalation to
  SUSPECTED_DISTRESS requires the evidence class to persist for
  `state.distress_persistence_ms`.
* Only detections at/above `detection.evidence_confidence` contribute evidence.
  Lower-confidence detections still keep a track alive (continuity) but can
  never escalate a state.
* Motion is normalized (displacement / bbox diagonal / seconds), so it is
  independent of camera distance and frame rate.
* De-escalation is hysteretic: a track returns to NORMAL only after stable
  normal evidence persists through `state.recovery_ms`.
* All timing uses a monotonic clock supplied by the caller, so variable FPS,
  dropped frames, and long gaps are handled by elapsed time, not frame counts.
* `out_of_water` and out-of-ROI tracks never escalate to in-pool states.

Nothing here is a medical judgement: states describe persistent *visual*
patterns and are corroborating evidence for a lifeguard, not a diagnosis.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum

from app.schemas import MotionState, RawClass, Visibility, VisualState


class SseEvent(str, Enum):
    heartbeat = "heartbeat"
    visual_evidence = "visual_evidence"


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class MotionConfig:
    smoothing_window_ms: float = 800
    displacement_window_ms: float = 1000
    low_motion_ratio_per_sec: float = 0.02
    inactivity_ms: float = 3000
    min_box_diagonal_px: float = 12


@dataclass(frozen=True)
class StateConfig:
    watch_min_ms: float = 300
    distress_persistence_ms: float = 1800
    inactivity_persistence_ms: float = 3000
    recovery_ms: float = 1500


@dataclass(frozen=True)
class EngineConfig:
    history_window_ms: float = 5000
    track_lost_timeout_ms: float = 1500
    track_expiry_ms: float = 8000
    evidence_confidence: float = 0.35
    motion: MotionConfig = field(default_factory=MotionConfig)
    state: StateConfig = field(default_factory=StateConfig)

    @classmethod
    def from_thresholds(cls, thresholds: dict) -> "EngineConfig":
        detection = thresholds.get("detection", {}) or {}
        tracking = thresholds.get("tracking", {}) or {}
        history = thresholds.get("history", {}) or {}
        motion = thresholds.get("motion", {}) or {}
        state = thresholds.get("state", {}) or {}
        return cls(
            history_window_ms=float(history.get("window_ms", 5000)),
            track_lost_timeout_ms=float(tracking.get("track_lost_timeout_ms", 1500)),
            track_expiry_ms=float(tracking.get("track_expiry_ms", 8000)),
            evidence_confidence=float(detection.get("evidence_confidence", 0.35)),
            motion=MotionConfig(
                smoothing_window_ms=float(motion.get("smoothing_window_ms", 800)),
                displacement_window_ms=float(motion.get("displacement_window_ms", 1000)),
                low_motion_ratio_per_sec=float(motion.get("low_motion_ratio_per_sec", 0.02)),
                inactivity_ms=float(motion.get("inactivity_ms", 3000)),
                min_box_diagonal_px=float(motion.get("min_box_diagonal_px", 12)),
            ),
            state=StateConfig(
                watch_min_ms=float(state.get("watch_min_ms", 300)),
                distress_persistence_ms=float(state.get("distress_persistence_ms", 1800)),
                inactivity_persistence_ms=float(state.get("inactivity_persistence_ms", 3000)),
                recovery_ms=float(state.get("recovery_ms", 1500)),
            ),
        )


# --------------------------------------------------------------------------- #
# History
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class TrackSample:
    t: float  # monotonic seconds
    centroid: tuple[float, float]
    diagonal: float
    class_name: str
    confidence: float
    zone_id: int | None
    in_roi: bool


class TrackHistory:
    """Bounded time-windowed sample history for one track."""

    def __init__(self, window_ms: float) -> None:
        self.window_s = window_ms / 1000.0
        self.samples: deque[TrackSample] = deque()

    def add(self, sample: TrackSample) -> None:
        self.samples.append(sample)
        self.prune(sample.t)

    def prune(self, now: float) -> None:
        cutoff = now - self.window_s
        while self.samples and self.samples[0].t < cutoff:
            self.samples.popleft()

    @property
    def span_s(self) -> float:
        if len(self.samples) < 2:
            return 0.0
        return self.samples[-1].t - self.samples[0].t

    def smoothed_centroid_at(self, t_end: float, window_s: float) -> tuple[float, float] | None:
        """Trailing mean centroid over (t_end - window_s, t_end]."""
        points = [
            s.centroid for s in self.samples if t_end - window_s <= s.t <= t_end
        ]
        if not points:
            return None
        count = len(points)
        return (
            sum(p[0] for p in points) / count,
            sum(p[1] for p in points) / count,
        )

    def median_diagonal(self, t_start: float, t_end: float) -> float | None:
        diagonals = sorted(
            s.diagonal for s in self.samples if t_start <= s.t <= t_end
        )
        if not diagonals:
            return None
        middle = len(diagonals) // 2
        if len(diagonals) % 2:
            return diagonals[middle]
        return (diagonals[middle - 1] + diagonals[middle]) / 2.0

    def normalized_movement(self, now: float, motion: MotionConfig) -> float | None:
        """Displacement / bbox diagonal / second, or None when undeterminable.

        Returns None (unknown, never "low") when there is not enough history,
        or when boxes are too small for the measurement to mean anything.
        """
        smoothing_s = motion.smoothing_window_ms / 1000.0
        displacement_s = motion.displacement_window_ms / 1000.0
        if displacement_s <= 0:
            return None
        t_ref = now - displacement_s
        # Need history reaching back past the reference window.
        if not self.samples or self.samples[0].t > t_ref - smoothing_s:
            return None

        now_point = self.smoothed_centroid_at(now, smoothing_s)
        ref_point = self.smoothed_centroid_at(t_ref, smoothing_s)
        if now_point is None or ref_point is None:
            return None

        diagonal = self.median_diagonal(t_ref, now)
        if diagonal is None or diagonal < motion.min_box_diagonal_px:
            return None

        displacement = (
            (now_point[0] - ref_point[0]) ** 2 + (now_point[1] - ref_point[1]) ** 2
        ) ** 0.5
        return displacement / diagonal / displacement_s


# --------------------------------------------------------------------------- #
# Per-track context and evidence
# --------------------------------------------------------------------------- #


@dataclass
class TrackEvidence:
    """One track's current visual evidence — the payload for an SSE event."""

    track_id: int | None
    zone_id: int | None
    raw_class: str | None
    detection_confidence: float | None
    motion_state: MotionState
    normalized_movement: float | None
    low_motion_duration_ms: int
    class_persistence_ms: int
    visibility: Visibility
    visual_state: VisualState
    evidence: list[str]


@dataclass
class TrackContext:
    track_id: int
    history: TrackHistory
    state: VisualState = VisualState.normal
    state_since: float = 0.0
    last_seen: float = 0.0
    last_zone: int | None = None
    last_class: str | None = None
    last_confidence: float | None = None
    evidence_class: str | None = None
    evidence_class_since: float | None = None
    distress_since: float | None = None
    low_motion_since: float | None = None
    normal_since: float | None = None
    reported_lost: bool = False


class TemporalStateEngine:
    """Turns per-frame tracked detections into persistent visual states."""

    def __init__(self, config: EngineConfig) -> None:
        self.config = config
        self.tracks: dict[int, TrackContext] = {}
        self.source_healthy = True

    # -- ingestion -------------------------------------------------------- #

    def observe(
        self,
        track_id: int,
        now: float,
        centroid: tuple[float, float],
        diagonal: float,
        class_name: str,
        confidence: float,
        zone_id: int | None,
        in_roi: bool,
    ) -> None:
        """Record one detection for one track in the current frame."""
        context = self.tracks.get(track_id)
        if context is None:
            context = TrackContext(
                track_id=track_id,
                history=TrackHistory(self.config.history_window_ms),
                state_since=now,
            )
            self.tracks[track_id] = context

        context.history.add(
            TrackSample(now, centroid, diagonal, class_name, confidence, zone_id, in_roi)
        )
        context.last_seen = now
        context.last_zone = zone_id
        context.last_class = class_name
        context.last_confidence = confidence
        if context.reported_lost:
            # Track came back; let the normal state rules take over again.
            context.reported_lost = False

        # Only sufficiently confident detections contribute evidence.
        if confidence >= self.config.evidence_confidence:
            if context.evidence_class != class_name:
                context.evidence_class = class_name
                context.evidence_class_since = now
        # A low-confidence detection keeps the track alive but changes no evidence.

    # -- evaluation ------------------------------------------------------- #

    def update(self, now: float) -> list[TrackEvidence]:
        """Recompute every track's state. Returns current evidence per track."""
        if not self.source_healthy:
            return [self._camera_unavailable()]

        results: list[TrackEvidence] = []
        for track_id in list(self.tracks):
            context = self.tracks[track_id]
            age_ms = (now - context.last_seen) * 1000.0

            if age_ms > self.config.track_expiry_ms:
                del self.tracks[track_id]
                continue

            if age_ms > self.config.track_lost_timeout_ms:
                results.append(self._track_lost(context, now))
                continue

            context.history.prune(now)
            results.append(self._evaluate(context, now))
        return results

    def _evaluate(self, context: TrackContext, now: float) -> TrackEvidence:
        config = self.config
        in_pool = context.last_zone is not None
        is_out_of_water = context.evidence_class == RawClass.out_of_water.value

        movement = context.history.normalized_movement(now, config.motion)
        # Unknown movement is never treated as low motion.
        is_low_motion = movement is not None and movement < config.motion.low_motion_ratio_per_sec

        # Elapsed-time guards compare against None explicitly: these are
        # monotonic timestamps and 0.0 is a valid value.
        if is_low_motion:
            if context.low_motion_since is None:
                context.low_motion_since = now
        else:
            context.low_motion_since = None
        low_motion_ms = (
            (now - context.low_motion_since) * 1000.0
            if context.low_motion_since is not None
            else 0.0
        )

        has_distress_evidence = (
            context.evidence_class == RawClass.distress_candidate.value and in_pool
        )
        if has_distress_evidence:
            if context.distress_since is None:
                context.distress_since = (
                    context.evidence_class_since
                    if context.evidence_class_since is not None
                    else now
                )
        else:
            context.distress_since = None
        distress_ms = (
            (now - context.distress_since) * 1000.0
            if context.distress_since is not None
            else 0.0
        )

        class_persistence_ms = (
            (now - context.evidence_class_since) * 1000.0
            if context.evidence_class_since is not None
            else 0.0
        )

        # Inactivity requires a valid in-pool track that is not on the deck.
        inactivity_eligible = in_pool and not is_out_of_water
        reasons: list[str] = []

        if inactivity_eligible and low_motion_ms >= config.state.inactivity_persistence_ms:
            target = VisualState.suspected_inactivity
            reasons.append("prolonged_low_normalized_movement")
            if has_distress_evidence:
                reasons.append("persistent_distress_appearance")
        elif has_distress_evidence and distress_ms >= config.state.distress_persistence_ms:
            target = VisualState.suspected_distress
            reasons.append("persistent_distress_appearance")
            if is_low_motion:
                reasons.append("limited_displacement")
        elif has_distress_evidence and distress_ms >= config.state.watch_min_ms:
            target = VisualState.watch
            reasons.append("recent_distress_appearance")
        else:
            target = VisualState.normal
            if is_out_of_water:
                reasons.append("out_of_water_appearance")
            elif not in_pool:
                reasons.append("outside_pool_roi")
            elif context.evidence_class == RawClass.normal_swimming.value:
                reasons.append("normal_swimming_appearance")
            else:
                reasons.append("no_confident_evidence")

        state = self._apply_hysteresis(context, target, now)

        # motionState reports the measurement itself, independent of the state.
        if movement is None:
            motion_state = MotionState.unknown
        elif is_low_motion:
            motion_state = MotionState.low
        else:
            motion_state = MotionState.normal
        if low_motion_ms >= config.motion.inactivity_ms:
            reasons.append("inactivity_level_motion")

        return TrackEvidence(
            track_id=context.track_id,
            zone_id=context.last_zone,
            raw_class=context.evidence_class or context.last_class,
            detection_confidence=context.last_confidence,
            motion_state=motion_state,
            normalized_movement=movement,
            low_motion_duration_ms=int(low_motion_ms),
            class_persistence_ms=int(class_persistence_ms),
            visibility=Visibility.clear,
            visual_state=state,
            evidence=reasons,
        )

    def _apply_hysteresis(
        self, context: TrackContext, target: VisualState, now: float
    ) -> VisualState:
        """Escalate immediately (gates already require persistence); de-escalate slowly."""
        if target is not VisualState.normal:
            context.normal_since = None
            if context.state is not target:
                context.state = target
                context.state_since = now
            return context.state

        # target is NORMAL
        if context.state is VisualState.normal:
            if context.normal_since is None:
                context.normal_since = now
            return context.state

        if context.normal_since is None:
            context.normal_since = now
        stable_normal_ms = (now - context.normal_since) * 1000.0
        if stable_normal_ms >= self.config.state.recovery_ms:
            context.state = VisualState.normal
            context.state_since = now
        return context.state

    def _track_lost(self, context: TrackContext, now: float) -> TrackEvidence:
        if context.state is not VisualState.track_lost:
            context.state = VisualState.track_lost
            context.state_since = now
        context.reported_lost = True
        return TrackEvidence(
            track_id=context.track_id,
            zone_id=context.last_zone,
            raw_class=context.evidence_class or context.last_class,
            detection_confidence=None,
            motion_state=MotionState.unknown,
            normalized_movement=None,
            low_motion_duration_ms=0,
            class_persistence_ms=0,
            visibility=Visibility.lost,
            visual_state=VisualState.track_lost,
            evidence=["track_not_matched_within_timeout"],
        )

    def _camera_unavailable(self) -> TrackEvidence:
        return TrackEvidence(
            track_id=None,
            zone_id=None,
            raw_class=None,
            detection_confidence=None,
            motion_state=MotionState.unknown,
            normalized_movement=None,
            low_motion_duration_ms=0,
            class_persistence_ms=0,
            visibility=Visibility.unavailable,
            visual_state=VisualState.camera_unavailable,
            evidence=["capture_source_unavailable"],
        )

    def set_source_healthy(self, healthy: bool) -> None:
        """A failed source must surface as CAMERA_UNAVAILABLE, never as NORMAL."""
        self.source_healthy = healthy
