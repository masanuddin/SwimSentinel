"""Load, validate, and resolve cv-service/training/dataset.yaml.

Shared by train.py, validate.py, and the tests. The committed dataset.yaml
keeps a machine-independent relative `path`; Ultralytics would resolve that
against its global datasets_dir, so before handing the config to YOLO we
resolve `path` against the YAML file's own location and write a temporary
fully-resolved copy under cv-service/runs/.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

TRAINING_DIR = Path(__file__).resolve().parent
CV_SERVICE_ROOT = TRAINING_DIR.parent
DEFAULT_DATASET_YAML = TRAINING_DIR / "dataset.yaml"
RUNS_DIR = CV_SERVICE_ROOT / "runs"

SPLIT_KEYS = ("train", "val", "test")


class DatasetConfigError(RuntimeError):
    """Raised when the training dataset config or dataset itself is unusable."""


def load_dataset_config(yaml_path: Path = DEFAULT_DATASET_YAML) -> dict:
    """Load dataset.yaml and resolve `path` against the YAML file location."""
    if not yaml_path.is_file():
        raise DatasetConfigError(f"dataset config not found: {yaml_path}")
    with yaml_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise DatasetConfigError(f"{yaml_path} did not parse to a mapping")

    dataset_path = Path(str(config.get("path", "")))
    if not dataset_path.is_absolute():
        dataset_path = (yaml_path.parent / dataset_path).resolve()
    config["path"] = str(dataset_path)
    return config


def validate_dataset_config(config: dict) -> list[str]:
    """Return a list of problems; empty list means the config is usable."""
    problems: list[str] = []
    dataset_root = Path(config["path"])
    if not dataset_root.is_dir():
        problems.append(
            f"dataset root not found: {dataset_root}\n"
            "  Download the dataset manually (YOLOv11 export) from\n"
            "  https://universe.roboflow.com/object-detection-model/drowning-detection-wqiom\n"
            "  and extract it under cv-service/data/raw/ (see cv-service/README.md)."
        )
        return problems

    for key in SPLIT_KEYS:
        if key not in config:
            continue
        split_dir = dataset_root / str(config[key])
        if not split_dir.is_dir():
            problems.append(f"split '{key}' directory missing: {split_dir}")
        elif not any(split_dir.iterdir()):
            problems.append(f"split '{key}' directory is empty: {split_dir}")

    names = config.get("names")
    if isinstance(names, dict):
        ids = sorted(names)
        if ids != list(range(len(ids))):
            problems.append(f"class IDs are not contiguous from 0: {ids}")
        class_count = len(names)
    elif isinstance(names, list):
        class_count = len(names)
    else:
        problems.append("dataset config has no usable 'names' entry")
        return problems

    if int(config.get("nc", class_count)) != class_count:
        problems.append(
            f"nc={config.get('nc')} does not match number of names ({class_count})"
        )
    return problems


def write_resolved_yaml(config: dict, out_path: Path | None = None) -> Path:
    """Write a fully-resolved copy for Ultralytics; returns its path."""
    if out_path is None:
        out_path = RUNS_DIR / "dataset.resolved.yaml"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, sort_keys=False, allow_unicode=True)
    return out_path


def prepare_dataset(yaml_path: Path = DEFAULT_DATASET_YAML) -> tuple[dict, Path]:
    """Load, validate, and materialize the resolved config. Exits on failure."""
    config = load_dataset_config(yaml_path)
    problems = validate_dataset_config(config)
    if problems:
        print("Dataset configuration problems:", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        raise SystemExit(1)
    resolved_path = write_resolved_yaml(config)
    return config, resolved_path
