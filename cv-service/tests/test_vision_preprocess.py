"""Inference preprocessing must mirror the training-time stretch.

The dataset was exported with every image stretched to 640x640 (aspect ratio
not preserved). These tests lock in two guarantees:

1. Frames are stretched (not letterboxed) before inference.
2. Box coordinates are mapped back to the original frame's pixel space, so
   zone assignment and normalized motion never see stretched coordinates.
"""

import numpy as np
import pytest

from app.vision import Detector, VisionError, scale_xyxy, stretch_to_square


def make_frame(width: int, height: int):
    return np.zeros((height, width, 3), dtype=np.uint8)


# -- stretch_to_square ------------------------------------------------------ #


def test_stretch_landscape_frame_to_square():
    stretched, scale_x, scale_y = stretch_to_square(make_frame(1280, 720), 640)
    assert stretched.shape == (640, 640, 3)
    assert scale_x == pytest.approx(1280 / 640)
    assert scale_y == pytest.approx(720 / 640)


def test_stretch_portrait_frame_to_square():
    stretched, scale_x, scale_y = stretch_to_square(make_frame(720, 1280), 640)
    assert stretched.shape == (640, 640, 3)
    assert scale_x == pytest.approx(720 / 640)
    assert scale_y == pytest.approx(1280 / 640)


def test_square_frame_is_a_no_op():
    frame = make_frame(640, 640)
    stretched, scale_x, scale_y = stretch_to_square(frame, 640)
    assert stretched is frame  # dataset images / harness clips are untouched
    assert scale_x == 1.0
    assert scale_y == 1.0


# -- scale_xyxy ------------------------------------------------------------- #


def test_full_stretched_box_maps_to_full_original_frame():
    _, scale_x, scale_y = stretch_to_square(make_frame(1280, 720), 640)
    assert scale_xyxy((0.0, 0.0, 640.0, 640.0), scale_x, scale_y) == (
        0.0,
        0.0,
        1280.0,
        720.0,
    )


def test_scaled_box_centroid_stays_proportional():
    """The zone anchor is the centroid; remapping must not move it."""
    _, scale_x, scale_y = stretch_to_square(make_frame(1280, 720), 640)
    x1, y1, x2, y2 = scale_xyxy((300.0, 300.0, 340.0, 340.0), scale_x, scale_y)
    # Centre of the stretched box is (320, 320) = frame centre; the remapped
    # centroid must land on the original frame's centre.
    assert (x1 + x2) / 2 == pytest.approx(640.0)
    assert (y1 + y2) / 2 == pytest.approx(360.0)


def test_identity_scale_leaves_box_unchanged():
    box = (10.5, 20.25, 100.0, 200.0)
    assert scale_xyxy(box, 1.0, 1.0) == box


# -- Detector configuration ------------------------------------------------- #


def test_detector_rejects_unknown_preprocess_before_loading_model(tmp_path):
    with pytest.raises(VisionError, match="preprocess"):
        Detector(
            model_path=tmp_path / "missing.pt",
            tracker_config=tmp_path / "tracker.yaml",
            preprocess="crop",
        )
