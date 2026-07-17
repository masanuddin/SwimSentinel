"""Tests for the dataset audit tool against a small temporary fixture dataset."""

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

CV_SERVICE_ROOT = Path(__file__).resolve().parents[1]
TRAINING_DIR = CV_SERVICE_ROOT / "training"
if str(TRAINING_DIR) not in sys.path:
    sys.path.insert(0, str(TRAINING_DIR))

import audit_dataset  # noqa: E402  (training/ is script-style, not a package)
import validate as validate_tool  # noqa: E402


def write_image(path: Path, seed: int) -> None:
    rng = np.random.default_rng(seed)
    image = rng.integers(0, 255, size=(32, 48, 3), dtype=np.uint8)
    assert cv2.imwrite(str(path), image)


@pytest.fixture
def fixture_dataset(tmp_path: Path) -> Path:
    """Tiny dataset with one known defect of each audited kind."""
    root = tmp_path / "mini-dataset"
    for split in ("train", "valid", "test"):
        (root / split / "images").mkdir(parents=True)
        (root / split / "labels").mkdir(parents=True)
    (root / "data.yaml").write_text(
        "train: ../train/images\nval: ../valid/images\ntest: ../test/images\n"
        "nc: 3\nnames: ['Drowning', 'Person out of water', 'Swimming']\n",
        encoding="utf-8",
    )

    train = root / "train"
    write_image(train / "images" / "ok.jpg", seed=1)
    (train / "labels" / "ok.txt").write_text(
        "0 0.5 0.5 0.2 0.3\n2 0.4 0.4 0.1 0.1\n", encoding="utf-8"
    )
    write_image(train / "images" / "bad_rows.jpg", seed=2)
    (train / "labels" / "bad_rows.txt").write_text(
        "0 0.5 0.5\n"  # malformed: wrong field count
        "7 0.5 0.5 0.2 0.2\n"  # out-of-range class id
        "1 1.5 0.5 0.2 0.2\n",  # invalid coordinate
        encoding="utf-8",
    )
    write_image(train / "images" / "empty_label.jpg", seed=3)
    (train / "labels" / "empty_label.txt").write_text("", encoding="utf-8")
    write_image(train / "images" / "no_label.jpg", seed=4)
    (train / "labels" / "orphan.txt").write_text("1 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    (train / "images" / "corrupt.jpg").write_bytes(b"this is not a jpeg")

    # Exact duplicate image shared between train and valid (leakage).
    write_image(train / "images" / "dup_a.jpg", seed=5)
    (train / "labels" / "dup_a.txt").write_text("2 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    (root / "valid" / "images" / "dup_b.jpg").write_bytes(
        (train / "images" / "dup_a.jpg").read_bytes()
    )
    (root / "valid" / "labels" / "dup_b.txt").write_text(
        "2 0.5 0.5 0.2 0.2\n", encoding="utf-8"
    )

    write_image(root / "test" / "images" / "t.jpg", seed=6)
    (root / "test" / "labels" / "t.txt").write_text("1 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    return root


def test_audit_reports_fixture_defects(fixture_dataset, tmp_path):
    report = audit_dataset.run_audit(
        fixture_dataset, report_path=tmp_path / "audit.json"
    )

    train = report["splits"]["train"]
    assert train["image_count"] == 6
    assert train["label_count"] == 5
    assert train["images_without_labels"] == ["corrupt.jpg", "no_label.jpg"]
    assert train["labels_without_images"] == ["orphan.txt"]
    assert train["empty_label_files"] == 1
    assert train["unreadable_images"] == ["corrupt.jpg"]
    assert train["malformed_rows"] == 1
    assert train["out_of_range_class_rows"] == 1
    assert train["invalid_coordinate_rows"] == 1
    assert train["unexpected_class_ids"] == [7]
    assert train["multi_class_images"] == 1
    assert train["object_counts_by_class"] == {
        "Drowning": 1,
        "Person out of water": 1,
        "Swimming": 2,
    }

    leakage = report["leakage"]
    assert leakage["cross_split_exact_duplicate_groups"] == 1
    assert leakage["cross_split_exact_duplicates"][0]["files"] == [
        "train/dup_a.jpg",
        "valid/dup_b.jpg",
    ]

    assert (tmp_path / "audit.json").is_file()
    assert "32" in next(iter(train["resolutions"]))  # 48x32 fixture images


def test_parse_source_group_video_vs_name():
    # Extracted video frame -> high-confidence clip group.
    group, confidence = audit_dataset.parse_source_group(
        "drowning1_mp4-37_jpg.rf.abc123.jpg"
    )
    assert group == "drowning1_mp4"
    assert confidence == "video"

    # Two frames of the same clip share the group id.
    group2, _ = audit_dataset.parse_source_group(
        "drowning1_mp4-38_jpg.rf.def456.jpg"
    )
    assert group2 == group

    # Standalone still -> ambiguous name group (its own original stem).
    group3, confidence3 = audit_dataset.parse_source_group("102_jpg.rf.999.jpg")
    assert group3 == "102_jpg"
    assert confidence3 == "name"


def test_source_group_analysis_detects_cross_split_video_group(tmp_path):
    root = tmp_path / "ds"
    for split in ("train", "valid", "test"):
        (root / split / "images").mkdir(parents=True)
    # Same clip 'clipA_mp4' appears in train AND valid -> cross-split leakage.
    write_image(root / "train" / "images" / "clipA_mp4-0_jpg.rf.a.jpg", seed=1)
    write_image(root / "train" / "images" / "clipA_mp4-1_jpg.rf.b.jpg", seed=2)
    write_image(root / "valid" / "images" / "clipA_mp4-2_jpg.rf.c.jpg", seed=3)
    # A different clip confined to test only.
    write_image(root / "test" / "images" / "clipB_mp4-0_jpg.rf.d.jpg", seed=4)

    analysis = audit_dataset.analyze_source_groups(root, total_images=4)
    video = analysis["video_frame_groups"]
    assert video["total_groups"] == 2
    assert video["cross_split_groups"] == 1
    assert video["images_in_cross_split_groups"] == 3
    assert video["examples"][0]["group"] == "clipA_mp4"
    assert sorted(video["examples"][0]["splits"]) == ["train", "valid"]


def test_audit_fails_without_dataset(tmp_path):
    empty_raw = tmp_path / "raw"
    empty_raw.mkdir()
    with pytest.raises(SystemExit):
        audit_dataset.find_dataset_root(empty_raw)


def test_validate_tool_fails_without_model(tmp_path):
    with pytest.raises(SystemExit):
        validate_tool.check_model_path(tmp_path / "missing.pt")
