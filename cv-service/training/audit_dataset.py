"""Audit the raw drowning-detection dataset before training.

Reads the manually downloaded Roboflow export under ``cv-service/data/raw/``
and reports configuration, per-split integrity, class distribution, exact
duplicate images across splits, and image-size statistics. The raw dataset is
treated as immutable: this tool only reads, it never renames, moves, or
rewrites source files.

Usage (from the repository root):

    cv-service\\.venv\\Scripts\\python.exe cv-service\\training\\audit_dataset.py

Outputs a human-readable terminal summary and a machine-readable JSON report
(default: cv-service/training/dataset_audit.json).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import yaml

TRAINING_DIR = Path(__file__).resolve().parent
CV_SERVICE_ROOT = TRAINING_DIR.parent
DEFAULT_RAW_DIR = CV_SERVICE_ROOT / "data" / "raw"
DEFAULT_REPORT_PATH = TRAINING_DIR / "dataset_audit.json"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SPLIT_NAMES = ("train", "valid", "test")

# Roboflow export names look like "<original-stem>.rf.<hex-hash>.<ext>".
ROBOFLOW_SUFFIX = re.compile(r"^(?P<orig>.+)\.rf\.[0-9a-f]+\.[^.]+$")
# Extracted video frames look like "<clip>_<videoext>-<frame>[_<suffix>]",
# e.g. "drowning1_mp4-37_jpg" -> source clip "drowning1_mp4".
VIDEO_FRAME = re.compile(
    r"^(?P<group>.+_(?:mp4|mov|avi|mkv|webm|m4v))-\d+(?:_[a-z0-9]+)?$",
    re.IGNORECASE,
)


def fail(message: str) -> "SystemExit":
    print(f"ERROR: {message}", file=sys.stderr)
    return SystemExit(1)


def find_dataset_root(raw_dir: Path) -> Path:
    """Locate the dataset folder (the one containing data.yaml) under raw_dir."""
    if (raw_dir / "data.yaml").is_file():
        return raw_dir
    if not raw_dir.is_dir():
        raise fail(
            f"raw data directory not found: {raw_dir}\n"
            "Download the dataset manually from "
            "https://universe.roboflow.com/object-detection-model/drowning-detection-wqiom "
            "(YOLOv11 export) and extract it under cv-service/data/raw/."
        )
    candidates = [d for d in sorted(raw_dir.iterdir()) if (d / "data.yaml").is_file()]
    if not candidates:
        raise fail(
            f"no dataset with a data.yaml found under {raw_dir}\n"
            "Expected an extracted Roboflow YOLOv11 export, e.g. "
            "cv-service/data/raw/<export-folder>/data.yaml"
        )
    if len(candidates) > 1:
        names = ", ".join(d.name for d in candidates)
        raise fail(
            f"multiple candidate datasets found under {raw_dir}: {names}\n"
            "Pass the intended one explicitly with --dataset."
        )
    return candidates[0]


def load_dataset_config(dataset_root: Path) -> dict:
    config_path = dataset_root / "data.yaml"
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise fail(f"{config_path} did not parse to a mapping")
    names = config.get("names")
    if isinstance(names, dict):
        names = [names[key] for key in sorted(names)]
    if not isinstance(names, list) or not names:
        raise fail(f"{config_path} has no usable 'names' entry")
    config["names"] = [str(name) for name in names]
    config["nc"] = int(config.get("nc", len(names)))
    return config


def parse_label_file(path: Path, num_classes: int) -> dict:
    """Parse one YOLO label file; returns row stats and per-class counts."""
    result = {
        "rows": 0,
        "malformed_rows": 0,
        "out_of_range_class_rows": 0,
        "invalid_coordinate_rows": 0,
        "class_counts": Counter(),
        "class_ids_seen": set(),
    }
    text = path.read_text(encoding="utf-8", errors="replace")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        result["rows"] += 1
        fields = line.split()
        if len(fields) != 5:
            result["malformed_rows"] += 1
            continue
        try:
            class_id = int(fields[0])
            cx, cy, w, h = (float(value) for value in fields[1:])
        except ValueError:
            result["malformed_rows"] += 1
            continue
        result["class_ids_seen"].add(class_id)
        if not 0 <= class_id < num_classes:
            result["out_of_range_class_rows"] += 1
            continue
        coords_normalized = all(0.0 <= value <= 1.0 for value in (cx, cy, w, h))
        if not coords_normalized or w <= 0.0 or h <= 0.0:
            result["invalid_coordinate_rows"] += 1
            continue
        result["class_counts"][class_id] += 1
    return result


@dataclass
class SplitAudit:
    name: str
    image_count: int = 0
    label_count: int = 0
    images_without_labels: list[str] = field(default_factory=list)
    labels_without_images: list[str] = field(default_factory=list)
    empty_label_files: int = 0
    unreadable_images: list[str] = field(default_factory=list)
    malformed_rows: int = 0
    out_of_range_class_rows: int = 0
    invalid_coordinate_rows: int = 0
    class_object_counts: Counter = field(default_factory=Counter)
    class_image_counts: Counter = field(default_factory=Counter)
    multi_class_images: int = 0
    unexpected_class_ids: set = field(default_factory=set)
    resolutions: Counter = field(default_factory=Counter)


def audit_split(
    split_dir: Path,
    num_classes: int,
    hash_index: dict[str, list[tuple[str, str]]],
    decode_images: bool = True,
) -> SplitAudit:
    audit = SplitAudit(name=split_dir.name)
    images_dir = split_dir / "images"
    labels_dir = split_dir / "labels"

    image_files = (
        sorted(
            p for p in images_dir.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        )
        if images_dir.is_dir()
        else []
    )
    label_files = (
        sorted(p for p in labels_dir.iterdir() if p.is_file() and p.suffix == ".txt")
        if labels_dir.is_dir()
        else []
    )
    audit.image_count = len(image_files)
    audit.label_count = len(label_files)

    label_stems = {p.stem for p in label_files}
    image_stems = {p.stem for p in image_files}
    audit.images_without_labels = sorted(
        p.name for p in image_files if p.stem not in label_stems
    )
    audit.labels_without_images = sorted(
        p.name for p in label_files if p.stem not in image_stems
    )

    for label_path in label_files:
        parsed = parse_label_file(label_path, num_classes)
        if parsed["rows"] == 0:
            audit.empty_label_files += 1
        audit.malformed_rows += parsed["malformed_rows"]
        audit.out_of_range_class_rows += parsed["out_of_range_class_rows"]
        audit.invalid_coordinate_rows += parsed["invalid_coordinate_rows"]
        audit.class_object_counts.update(parsed["class_counts"])
        for class_id in parsed["class_counts"]:
            audit.class_image_counts[class_id] += 1
        if len(parsed["class_counts"]) > 1:
            audit.multi_class_images += 1
        audit.unexpected_class_ids.update(
            class_id for class_id in parsed["class_ids_seen"]
            if not 0 <= class_id < num_classes
        )

    for image_path in image_files:
        data = image_path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        hash_index.setdefault(digest, []).append((split_dir.name, image_path.name))
        if decode_images:
            image = cv2.imread(str(image_path))
            if image is None:
                audit.unreadable_images.append(image_path.name)
            else:
                height, width = image.shape[:2]
                audit.resolutions[f"{width}x{height}"] += 1

    return audit


def cross_split_duplicates(hash_index: dict[str, list[tuple[str, str]]]) -> list[dict]:
    duplicates = []
    for digest, entries in hash_index.items():
        splits = {split for split, _ in entries}
        if len(splits) > 1:
            duplicates.append(
                {
                    "sha256": digest,
                    "files": [f"{split}/{name}" for split, name in sorted(entries)],
                }
            )
    return sorted(duplicates, key=lambda item: item["files"][0])


def duplicate_filenames_across_splits(splits: dict[str, SplitAudit], dataset_root: Path) -> list[str]:
    stem_to_splits: dict[str, set[str]] = {}
    for split_name in splits:
        images_dir = dataset_root / split_name / "images"
        if not images_dir.is_dir():
            continue
        for path in images_dir.iterdir():
            if path.suffix.lower() in IMAGE_EXTENSIONS:
                stem_to_splits.setdefault(path.name, set()).add(split_name)
    return sorted(name for name, in_splits in stem_to_splits.items() if len(in_splits) > 1)


def parse_source_group(filename: str) -> tuple[str, str]:
    """Infer a source-group id from a Roboflow filename.

    Returns ``(group_id, confidence)`` where confidence is:
    - ``"video"``  — high: the stem matches an extracted-video-frame pattern,
      so the group is the source clip name (frames are near-duplicates).
    - ``"name"``   — low/ambiguous: no video pattern, so the group is just the
      shared pre-``.rf.`` original stem. Equal stems may be re-exports of one
      image OR coincidental name collisions across merged sub-datasets.
    """
    match = ROBOFLOW_SUFFIX.match(filename)
    original = match.group("orig") if match else filename
    video = VIDEO_FRAME.match(original)
    if video:
        return video.group("group"), "video"
    return original, "name"


def _summarize_group_tier(
    group_splits: dict[str, set[str]],
    group_counts: dict[str, int],
    total_images: int,
) -> dict:
    cross = sorted(
        (g for g in group_splits if len(group_splits[g]) > 1),
        key=lambda g: -group_counts[g],
    )
    single = [g for g in group_splits if len(group_splits[g]) == 1]
    images_in_cross = sum(group_counts[g] for g in cross)
    examples = [
        {
            "group": g,
            "images": group_counts[g],
            "splits": sorted(group_splits[g]),
        }
        for g in cross[:8]
    ]
    return {
        "total_groups": len(group_splits),
        "single_split_groups": len(single),
        "cross_split_groups": len(cross),
        "images_in_cross_split_groups": images_in_cross,
        "images_in_cross_split_groups_pct": round(images_in_cross / total_images, 4)
        if total_images
        else 0,
        "examples": examples,
    }


def analyze_source_groups(dataset_root: Path, total_images: int) -> dict:
    """Estimate whether frames from the same source video/clip span splits.

    This is a heuristic over filenames only: no image content is compared and
    nothing is moved or rewritten. Two tiers are reported with explicit
    confidence so inflated metrics can be flagged without overclaiming.
    """
    video_splits: dict[str, set[str]] = defaultdict(set)
    video_counts: dict[str, int] = defaultdict(int)
    name_splits: dict[str, set[str]] = defaultdict(set)
    name_counts: dict[str, int] = defaultdict(int)

    for split_name in SPLIT_NAMES:
        images_dir = dataset_root / split_name / "images"
        if not images_dir.is_dir():
            continue
        for path in images_dir.iterdir():
            if path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            group_id, confidence = parse_source_group(path.name)
            if confidence == "video":
                video_splits[group_id].add(split_name)
                video_counts[group_id] += 1
            else:
                name_splits[group_id].add(split_name)
                name_counts[group_id] += 1

    video_images = sum(video_counts.values())
    return {
        "parsing_rule": (
            "Strip the Roboflow suffix '<stem>.rf.<hash>.<ext>'. If the stem "
            "matches '<clip>_<videoext>-<frame>' (videoext in mp4/mov/avi/mkv/"
            "webm/m4v) treat the clip as a high-confidence source group; "
            "otherwise fall back to the shared original stem (low confidence)."
        ),
        "video_frame_groups": {
            "confidence": "high",
            "images_matched": video_images,
            "coverage_pct": round(video_images / total_images, 4) if total_images else 0,
            **_summarize_group_tier(video_splits, video_counts, total_images),
        },
        "shared_original_name_groups": {
            "confidence": "low_ambiguous",
            "note": (
                "Identical pre-.rf. stems; may be re-exports of one image or "
                "coincidental numeric-name collisions across merged sources. "
                "Not proof of same-source frames on its own."
            ),
            **_summarize_group_tier(name_splits, name_counts, total_images),
        },
    }


def build_report(
    dataset_root: Path,
    config: dict,
    splits: dict[str, SplitAudit],
    duplicates: list[dict],
    duplicate_names: list[str],
    source_groups: dict,
) -> dict:
    class_names = config["names"]
    try:
        dataset_display = str(dataset_root.relative_to(CV_SERVICE_ROOT.parent))
    except ValueError:
        dataset_display = dataset_root.name

    def class_counter_to_names(counter: Counter) -> dict[str, int]:
        return {
            class_names[class_id] if 0 <= class_id < len(class_names) else f"id_{class_id}": count
            for class_id, count in sorted(counter.items())
        }

    total_images = sum(split.image_count for split in splits.values())
    report = {
        "dataset_root": dataset_display,
        "config": {
            "nc": config["nc"],
            "names": class_names,
            "declared_splits": {
                key: config.get(key) for key in ("train", "val", "test") if key in config
            },
            "roboflow": config.get("roboflow", {}),
        },
        "splits": {},
        "distribution": {},
        "leakage": {
            "cross_split_exact_duplicate_groups": len(duplicates),
            "cross_split_exact_duplicates": duplicates,
            "duplicate_filenames_across_splits": duplicate_names,
            "source_group_analysis": source_groups,
        },
    }
    for split in splits.values():
        report["splits"][split.name] = {
            "image_count": split.image_count,
            "label_count": split.label_count,
            "split_share": round(split.image_count / total_images, 4) if total_images else 0,
            "images_without_labels": split.images_without_labels,
            "labels_without_images": split.labels_without_images,
            "empty_label_files": split.empty_label_files,
            "unreadable_images": split.unreadable_images,
            "malformed_rows": split.malformed_rows,
            "out_of_range_class_rows": split.out_of_range_class_rows,
            "invalid_coordinate_rows": split.invalid_coordinate_rows,
            "unexpected_class_ids": sorted(split.unexpected_class_ids),
            "object_counts_by_class": class_counter_to_names(split.class_object_counts),
            "image_counts_by_class": class_counter_to_names(split.class_image_counts),
            "multi_class_images": split.multi_class_images,
            "resolutions": dict(split.resolutions.most_common()),
        }

    combined_objects = Counter()
    combined_images = Counter()
    for split in splits.values():
        combined_objects.update(split.class_object_counts)
        combined_images.update(split.class_image_counts)
    total_objects = sum(combined_objects.values())
    report["distribution"] = {
        "total_images": total_images,
        "total_objects": total_objects,
        "object_counts_by_class": class_counter_to_names(combined_objects),
        "object_share_by_class": {
            name: round(count / total_objects, 4)
            for name, count in class_counter_to_names(combined_objects).items()
        }
        if total_objects
        else {},
        "image_counts_by_class": class_counter_to_names(combined_images),
    }
    return report


def print_summary(report: dict) -> None:
    print(f"\nDataset: {report['dataset_root']}")
    print(f"Classes ({report['config']['nc']}): {report['config']['names']}")

    print("\n-- Splits --")
    for name, split in report["splits"].items():
        print(
            f"{name:>6}: {split['image_count']} images, {split['label_count']} labels "
            f"({split['split_share']:.1%} of images)"
        )
        issues = []
        if split["images_without_labels"]:
            issues.append(f"{len(split['images_without_labels'])} images without labels")
        if split["labels_without_images"]:
            issues.append(f"{len(split['labels_without_images'])} labels without images")
        if split["empty_label_files"]:
            issues.append(f"{split['empty_label_files']} empty label files")
        if split["unreadable_images"]:
            issues.append(f"{len(split['unreadable_images'])} unreadable images")
        if split["malformed_rows"]:
            issues.append(f"{split['malformed_rows']} malformed rows")
        if split["out_of_range_class_rows"]:
            issues.append(f"{split['out_of_range_class_rows']} out-of-range class rows")
        if split["invalid_coordinate_rows"]:
            issues.append(f"{split['invalid_coordinate_rows']} invalid coordinate rows")
        if split["unexpected_class_ids"]:
            issues.append(f"unexpected class ids {split['unexpected_class_ids']}")
        print(f"        issues: {', '.join(issues) if issues else 'none'}")

    print("\n-- Class distribution (objects, all splits) --")
    for name, count in report["distribution"]["object_counts_by_class"].items():
        share = report["distribution"]["object_share_by_class"].get(name, 0)
        print(f"  {name:>20}: {count} ({share:.1%})")

    leakage = report["leakage"]
    print("\n-- Leakage --")
    print(
        f"  exact duplicate image groups across splits: "
        f"{leakage['cross_split_exact_duplicate_groups']}"
    )
    print(
        f"  duplicate filenames across splits: "
        f"{len(leakage['duplicate_filenames_across_splits'])}"
    )
    video = leakage["source_group_analysis"]["video_frame_groups"]
    print(
        f"  source-video groups (high confidence): {video['total_groups']} groups, "
        f"{video['cross_split_groups']} span >=2 splits"
    )
    print(
        f"    -> {video['images_in_cross_split_groups']} images "
        f"({video['images_in_cross_split_groups_pct']:.1%}) are in cross-split video groups"
    )
    if video["examples"]:
        top = video["examples"][0]
        print(
            f"    -> largest: {top['group']!r} = {top['images']} frames in {top['splits']}"
        )
    name_tier = leakage["source_group_analysis"]["shared_original_name_groups"]
    print(
        f"  shared-name groups (ambiguous): {name_tier['cross_split_groups']} span >=2 splits, "
        f"{name_tier['images_in_cross_split_groups']} images "
        f"({name_tier['images_in_cross_split_groups_pct']:.1%})"
    )

    print("\n-- Image sizes --")
    for name, split in report["splits"].items():
        resolutions = split["resolutions"]
        if resolutions:
            top = ", ".join(f"{res} ({count})" for res, count in list(resolutions.items())[:3])
            print(f"  {name:>6}: {top}")
    print()


def run_audit(
    dataset_root: Path,
    report_path: Path | None = DEFAULT_REPORT_PATH,
    decode_images: bool = True,
) -> dict:
    config = load_dataset_config(dataset_root)
    hash_index: dict[str, list[tuple[str, str]]] = {}
    splits: dict[str, SplitAudit] = {}
    for split_name in SPLIT_NAMES:
        split_dir = dataset_root / split_name
        if split_dir.is_dir():
            splits[split_name] = audit_split(
                split_dir, config["nc"], hash_index, decode_images=decode_images
            )
    if not splits:
        raise fail(f"no train/valid/test split directories found under {dataset_root}")

    duplicates = cross_split_duplicates(hash_index)
    duplicate_names = duplicate_filenames_across_splits(splits, dataset_root)
    total_images = sum(split.image_count for split in splits.values())
    source_groups = analyze_source_groups(dataset_root, total_images)
    report = build_report(
        dataset_root, config, splits, duplicates, duplicate_names, source_groups
    )

    if report_path is not None:
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"JSON report written to {report_path}")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Dataset root containing data.yaml (default: auto-discover under cv-service/data/raw/)",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Where to write the JSON report",
    )
    parser.add_argument(
        "--skip-image-decode",
        action="store_true",
        help="Skip decoding every image (faster; disables unreadable-image and size checks)",
    )
    args = parser.parse_args(argv)

    dataset_root = args.dataset if args.dataset else find_dataset_root(DEFAULT_RAW_DIR)
    if not (dataset_root / "data.yaml").is_file():
        raise fail(f"data.yaml not found in {dataset_root}")

    print(f"Auditing dataset at: {dataset_root}")
    report = run_audit(
        dataset_root, report_path=args.report, decode_images=not args.skip_image_decode
    )
    print_summary(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
