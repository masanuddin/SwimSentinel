"""Pool ROI and zone geometry.

Owns polygon validation, coordinate scaling from the configured frame size to
the actual capture size, point-in-polygon tests, and stable zone assignment.

Zone anchor: a detection is mapped to a zone by its bounding-box **centroid**
(configurable via `zones.anchor` in thresholds.yaml). The camera is a fixed
above-water side/diagonal view of swimmers in the water, so the centroid
of the visible body is the best available proxy for surface position.
`lower_center` is offered for a ground-plane view where feet mark position.

Detections outside the pool ROI are still reported (debug/visibility) but are
marked with `zone_id = None` and must never contribute to in-pool distress or
inactivity escalation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

Point = tuple[float, float]
Polygon = list[Point]


class ZoneConfigError(ValueError):
    """Raised when the zones configuration is missing or invalid."""


def validate_polygon(polygon: object, label: str) -> Polygon:
    """Validate a raw polygon and return it as a list of float pairs."""
    if not isinstance(polygon, (list, tuple)):
        raise ZoneConfigError(f"{label}: polygon must be a list of [x, y] points")
    if len(polygon) < 3:
        raise ZoneConfigError(f"{label}: polygon needs at least 3 points, got {len(polygon)}")
    points: Polygon = []
    for index, raw in enumerate(polygon):
        if not isinstance(raw, (list, tuple)) or len(raw) != 2:
            raise ZoneConfigError(f"{label}: point {index} must be [x, y]")
        try:
            points.append((float(raw[0]), float(raw[1])))
        except (TypeError, ValueError) as exc:
            raise ZoneConfigError(f"{label}: point {index} is not numeric") from exc
    if polygon_area(points) <= 0.0:
        raise ZoneConfigError(f"{label}: polygon is degenerate (zero area)")
    return points


def polygon_area(polygon: Polygon) -> float:
    """Absolute shoelace area."""
    total = 0.0
    count = len(polygon)
    for index in range(count):
        x1, y1 = polygon[index]
        x2, y2 = polygon[(index + 1) % count]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def point_in_polygon(x: float, y: float, polygon: Polygon) -> bool:
    """Ray-casting point-in-polygon test (points on an edge count as inside)."""
    inside = False
    count = len(polygon)
    for index in range(count):
        x1, y1 = polygon[index]
        x2, y2 = polygon[(index + 1) % count]
        if _on_segment(x, y, x1, y1, x2, y2):
            return True
        # Does the horizontal ray at y cross this edge?
        if (y1 > y) != (y2 > y):
            x_cross = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < x_cross:
                inside = not inside
    return inside


def _on_segment(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> bool:
    cross = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
    if abs(cross) > 1e-9:
        return False
    return min(x1, x2) - 1e-9 <= px <= max(x1, x2) + 1e-9 and \
        min(y1, y2) - 1e-9 <= py <= max(y1, y2) + 1e-9


def scale_polygon(polygon: Polygon, scale_x: float, scale_y: float) -> Polygon:
    return [(x * scale_x, y * scale_y) for x, y in polygon]


@dataclass(frozen=True)
class Zone:
    id: int
    label: str
    polygon: Polygon


@dataclass
class ZoneMap:
    """Pool ROI + zones, scaled to a concrete frame size."""

    camera_id: str
    frame_width: int
    frame_height: int
    roi: Polygon
    zones: list[Zone]

    @classmethod
    def from_file(cls, path: Path) -> "ZoneMap":
        if not path.is_file():
            raise ZoneConfigError(
                f"zones config not found: {path}\n"
                "Set CV_ZONES_FILE or add the file to cv-service/config/."
            )
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ZoneConfigError(f"{path} is not valid JSON: {exc}") from exc
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict) -> "ZoneMap":
        if not isinstance(raw, dict):
            raise ZoneConfigError("zones config must be a JSON object")
        frame = raw.get("frameSize") or {}
        try:
            width = int(frame["width"])
            height = int(frame["height"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ZoneConfigError("zones config needs frameSize.width and .height") from exc
        if width <= 0 or height <= 0:
            raise ZoneConfigError("frameSize must be positive")

        roi = validate_polygon(raw.get("roi"), "roi")
        raw_zones = raw.get("zones")
        if not isinstance(raw_zones, list) or not raw_zones:
            raise ZoneConfigError("zones config needs a non-empty 'zones' list")

        zones: list[Zone] = []
        seen_ids: set[int] = set()
        for entry in raw_zones:
            if not isinstance(entry, dict) or "id" not in entry:
                raise ZoneConfigError("each zone needs an 'id'")
            zone_id = int(entry["id"])
            if zone_id in seen_ids:
                raise ZoneConfigError(f"duplicate zone id: {zone_id}")
            seen_ids.add(zone_id)
            polygon = validate_polygon(entry.get("polygon"), f"zone {zone_id}")
            zones.append(Zone(zone_id, str(entry.get("label", f"Zone {zone_id}")), polygon))

        return cls(
            camera_id=str(raw.get("cameraId", "POOL-CAM-01")),
            frame_width=width,
            frame_height=height,
            roi=roi,
            zones=zones,
        )

    def scaled_to(self, width: int, height: int) -> "ZoneMap":
        """Return a copy scaled from the configured frame size to width×height."""
        if width <= 0 or height <= 0:
            raise ZoneConfigError("target frame size must be positive")
        scale_x = width / self.frame_width
        scale_y = height / self.frame_height
        if scale_x == 1.0 and scale_y == 1.0:
            return self
        return ZoneMap(
            camera_id=self.camera_id,
            frame_width=width,
            frame_height=height,
            roi=scale_polygon(self.roi, scale_x, scale_y),
            zones=[
                Zone(zone.id, zone.label, scale_polygon(zone.polygon, scale_x, scale_y))
                for zone in self.zones
            ],
        )

    def in_roi(self, x: float, y: float) -> bool:
        return point_in_polygon(x, y, self.roi)

    def zone_for_point(self, x: float, y: float) -> int | None:
        """Zone id for a point, or None when outside the ROI or all zones.

        Zones are checked in configured order, so a point in an overlap always
        resolves to the same zone (stable assignment, no flicker).
        """
        if not self.in_roi(x, y):
            return None
        for zone in self.zones:
            if point_in_polygon(x, y, zone.polygon):
                return zone.id
        return None

    @property
    def zone_ids(self) -> list[int]:
        return [zone.id for zone in self.zones]


def anchor_point(xyxy: tuple[float, float, float, float], anchor: str = "centroid") -> Point:
    """Anchor used for zone assignment. See module docstring for rationale."""
    x1, y1, x2, y2 = xyxy
    if anchor == "lower_center":
        return ((x1 + x2) / 2.0, y2)
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
