"""Tests for the training dataset config and class mapping."""

import sys
from pathlib import Path

import pytest
import yaml

CV_SERVICE_ROOT = Path(__file__).resolve().parents[1]
TRAINING_DIR = CV_SERVICE_ROOT / "training"
if str(TRAINING_DIR) not in sys.path:
    sys.path.insert(0, str(TRAINING_DIR))

import dataset_config  # noqa: E402  (training/ is script-style, not a package)

# Locked conceptual mapping: source name -> product-facing name.
EXPECTED_MAPPING = {
    "Drowning": "distress_candidate",
    "Person out of water": "out_of_water",
    "Swimming": "normal_swimming",
}


def source_dataset_root() -> Path | None:
    raw_dir = CV_SERVICE_ROOT / "data" / "raw"
    if not raw_dir.is_dir():
        return None
    candidates = [d for d in sorted(raw_dir.iterdir()) if (d / "data.yaml").is_file()]
    return candidates[0] if len(candidates) == 1 else None


requires_dataset = pytest.mark.skipif(
    source_dataset_root() is None,
    reason="raw dataset not downloaded (see cv-service/README.md)",
)


def test_dataset_yaml_exists_and_parses():
    config = dataset_config.load_dataset_config()
    assert config["nc"] == 3
    assert config["names"] == {
        0: "distress_candidate",
        1: "out_of_water",
        2: "normal_swimming",
    }
    assert Path(config["path"]).is_absolute()


@requires_dataset
def test_class_mapping_preserves_source_ids():
    source_root = source_dataset_root()
    with (source_root / "data.yaml").open(encoding="utf-8") as handle:
        source = yaml.safe_load(handle)
    source_names = source["names"]
    if isinstance(source_names, dict):
        source_names = [source_names[key] for key in sorted(source_names)]

    training = dataset_config.load_dataset_config()
    assert len(source_names) == training["nc"]
    for class_id, source_name in enumerate(source_names):
        assert source_name in EXPECTED_MAPPING, f"unexpected source class: {source_name}"
        assert training["names"][class_id] == EXPECTED_MAPPING[source_name], (
            f"ID {class_id}: source '{source_name}' must map to "
            f"'{EXPECTED_MAPPING[source_name]}', got '{training['names'][class_id]}'"
        )


@requires_dataset
def test_split_paths_resolve():
    config = dataset_config.load_dataset_config()
    assert dataset_config.validate_dataset_config(config) == []
    assert Path(config["path"]) == source_dataset_root()


@requires_dataset
def test_no_unexpected_class_ids_in_labels():
    config = dataset_config.load_dataset_config()
    valid_ids = set(config["names"])
    seen: set[int] = set()
    for labels_dir in Path(config["path"]).glob("*/labels"):
        for label_file in labels_dir.iterdir():
            for line in label_file.read_text(encoding="utf-8").splitlines():
                fields = line.split()
                if fields:
                    seen.add(int(fields[0]))
    assert seen, "no label rows found at all"
    assert seen <= valid_ids, f"unexpected class IDs in labels: {seen - valid_ids}"


def test_missing_dataset_fails_validation(tmp_path):
    config = {
        "path": str(tmp_path / "nope"),
        "train": "train/images",
        "nc": 3,
        "names": {0: "a", 1: "b", 2: "c"},
    }
    problems = dataset_config.validate_dataset_config(config)
    assert problems and "dataset root not found" in problems[0]


def test_prepare_dataset_exits_on_missing_dataset(tmp_path):
    bad_yaml = tmp_path / "dataset.yaml"
    bad_yaml.write_text(
        "path: ./missing\ntrain: train/images\nnc: 1\nnames:\n  0: a\n",
        encoding="utf-8",
    )
    with pytest.raises(SystemExit):
        dataset_config.prepare_dataset(bad_yaml)


def test_nc_mismatch_detected(tmp_path):
    dataset_root = tmp_path / "ds"
    dataset_root.mkdir()
    config = {"path": str(dataset_root), "nc": 5, "names": {0: "a", 1: "b"}}
    problems = dataset_config.validate_dataset_config(config)
    assert any("nc=5" in problem for problem in problems)


def test_non_contiguous_class_ids_detected(tmp_path):
    dataset_root = tmp_path / "ds"
    dataset_root.mkdir()
    config = {"path": str(dataset_root), "nc": 2, "names": {0: "a", 2: "c"}}
    problems = dataset_config.validate_dataset_config(config)
    assert any("not contiguous" in problem for problem in problems)
