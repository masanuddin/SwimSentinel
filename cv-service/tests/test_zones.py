"""Tests for ROI/zone geometry, validation, scaling, assignment."""

import json

import pytest

from app.zones import (
    ZoneConfigError,
    ZoneMap,
    anchor_point,
    point_in_polygon,
    polygon_area,
    scale_polygon,
    validate_polygon,
)

SQUARE = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]

RAW_CONFIG = {
    "cameraId": "POOL-CAM-01",
    "frameSize": {"width": 100, "height": 100},
    "roi": [[0, 0], [100, 0], [100, 100], [0, 100]],
    "zones": [
        {"id": 1, "label": "Zone 1", "polygon": [[0, 0], [50, 0], [50, 50], [0, 50]]},
        {"id": 2, "label": "Zone 2", "polygon": [[50, 0], [100, 0], [100, 50], [50, 50]]},
    ],
}


# -- point in polygon ----------------------------------------------------- #


def test_point_inside_and_outside():
    assert point_in_polygon(5, 5, SQUARE) is True
    assert point_in_polygon(15, 5, SQUARE) is False
    assert point_in_polygon(-1, 5, SQUARE) is False


def test_point_on_edge_and_vertex_counts_as_inside():
    assert point_in_polygon(0, 5, SQUARE) is True
    assert point_in_polygon(10, 10, SQUARE) is True


def test_concave_polygon_notch_is_outside():
    # A "C" shape: the notch on the right must not count as inside.
    concave = [(0, 0), (10, 0), (10, 4), (4, 4), (4, 6), (10, 6), (10, 10), (0, 10)]
    assert point_in_polygon(2, 5, concave) is True
    assert point_in_polygon(7, 5, concave) is False


def test_polygon_area():
    assert polygon_area(SQUARE) == pytest.approx(100.0)


# -- validation ------------------------------------------------------------ #


def test_validate_polygon_rejects_too_few_points():
    with pytest.raises(ZoneConfigError, match="at least 3"):
        validate_polygon([[0, 0], [1, 1]], "roi")


def test_validate_polygon_rejects_degenerate():
    with pytest.raises(ZoneConfigError, match="degenerate"):
        validate_polygon([[0, 0], [5, 5], [10, 10]], "roi")


def test_validate_polygon_rejects_bad_points():
    with pytest.raises(ZoneConfigError):
        validate_polygon([[0, 0], [1], [2, 2]], "roi")
    with pytest.raises(ZoneConfigError):
        validate_polygon([[0, 0], ["a", "b"], [2, 2]], "roi")


def test_zone_map_rejects_duplicate_ids():
    raw = json.loads(json.dumps(RAW_CONFIG))
    raw["zones"][1]["id"] = 1
    with pytest.raises(ZoneConfigError, match="duplicate zone id"):
        ZoneMap.from_dict(raw)


def test_zone_map_rejects_missing_frame_size():
    raw = json.loads(json.dumps(RAW_CONFIG))
    del raw["frameSize"]
    with pytest.raises(ZoneConfigError, match="frameSize"):
        ZoneMap.from_dict(raw)


def test_zone_map_missing_file(tmp_path):
    with pytest.raises(ZoneConfigError, match="not found"):
        ZoneMap.from_file(tmp_path / "nope.json")


def test_zone_map_invalid_json(tmp_path):
    path = tmp_path / "zones.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ZoneConfigError, match="not valid JSON"):
        ZoneMap.from_file(path)


def test_real_zones_example_loads():
    from app.config import Settings

    zone_map = ZoneMap.from_file(Settings().zones_path)
    assert zone_map.zone_ids == [1, 2, 3, 4]


# -- scaling --------------------------------------------------------------- #


def test_scale_polygon():
    assert scale_polygon(SQUARE, 2.0, 0.5)[2] == (20.0, 5.0)


def test_zone_map_scales_to_actual_frame_size():
    zone_map = ZoneMap.from_dict(RAW_CONFIG)
    # Config declares 100x100; the real capture is 200x50.
    scaled = zone_map.scaled_to(200, 50)
    assert scaled.frame_width == 200
    assert scaled.frame_height == 50
    # A point at 25%,25% of the frame stays in zone 1 after scaling.
    assert zone_map.zone_for_point(25, 25) == 1
    assert scaled.zone_for_point(50, 12.5) == 1
    # Right half is still zone 2.
    assert scaled.zone_for_point(150, 12.5) == 2


def test_scaled_to_same_size_returns_self():
    zone_map = ZoneMap.from_dict(RAW_CONFIG)
    assert zone_map.scaled_to(100, 100) is zone_map


def test_scaled_to_rejects_bad_size():
    with pytest.raises(ZoneConfigError):
        ZoneMap.from_dict(RAW_CONFIG).scaled_to(0, 10)


# -- assignment ------------------------------------------------------------ #


def test_zone_assignment_and_out_of_roi():
    zone_map = ZoneMap.from_dict(RAW_CONFIG)
    assert zone_map.zone_for_point(25, 25) == 1
    assert zone_map.zone_for_point(75, 25) == 2
    # Inside the ROI but in no zone (lower half is unzoned here).
    assert zone_map.zone_for_point(25, 75) is None
    # Fully outside the ROI.
    assert zone_map.in_roi(150, 150) is False
    assert zone_map.zone_for_point(150, 150) is None


def test_zone_assignment_is_stable_for_overlapping_zones():
    raw = json.loads(json.dumps(RAW_CONFIG))
    # Make zone 2 overlap zone 1 entirely.
    raw["zones"][1]["polygon"] = [[0, 0], [100, 0], [100, 50], [0, 50]]
    zone_map = ZoneMap.from_dict(raw)
    # Configured order wins, every time -> no flicker.
    assert {zone_map.zone_for_point(25, 25) for _ in range(20)} == {1}


# -- anchors --------------------------------------------------------------- #


def test_anchor_centroid_and_lower_center():
    box = (10.0, 20.0, 30.0, 60.0)
    assert anchor_point(box, "centroid") == (20.0, 40.0)
    assert anchor_point(box, "lower_center") == (20.0, 60.0)
    # Unknown anchor falls back to centroid.
    assert anchor_point(box, "bogus") == (20.0, 40.0)
