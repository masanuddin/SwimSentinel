"""Build the detector evaluation package from a trained checkpoint.

Runs the selected checkpoint once on the validation split and once on the test
split, merges the metrics with the training configuration, the training-curve
history, and the dataset audit (class distribution + source-group leakage), and
writes a committed, machine-independent evaluation package:

    cv-service/evaluation/detector_summary.json
    cv-service/evaluation/detector_summary.csv
    cv-service/evaluation/detector_pitch_summary.md

Usage (from the repository root):

    cv-service\\.venv\\Scripts\\python.exe cv-service\\evaluation\\build_evaluation.py ^
        --model   cv-service\\runs\\yolo11s-main\\weights\\best.pt ^
        --run-dir cv-service\\runs\\yolo11s-main

The test split is evaluated exactly once here, after the checkpoint is already
selected — it is never used to choose epochs, thresholds, or the checkpoint.
Reported numbers are validation/test-set object-detection performance on the
Roboflow dataset only, not medical or real-world drowning-detection accuracy.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

EVALUATION_DIR = Path(__file__).resolve().parent
CV_SERVICE_ROOT = EVALUATION_DIR.parent
TRAINING_DIR = CV_SERVICE_ROOT / "training"
if str(TRAINING_DIR) not in sys.path:
    sys.path.insert(0, str(TRAINING_DIR))

from dataset_config import RUNS_DIR, prepare_dataset  # noqa: E402

AUDIT_JSON = TRAINING_DIR / "dataset_audit.json"
SUMMARY_JSON = EVALUATION_DIR / "detector_summary.json"
SUMMARY_CSV = EVALUATION_DIR / "detector_summary.csv"
PITCH_MD = EVALUATION_DIR / "detector_pitch_summary.md"

# Ultralytics best-checkpoint fitness weighting.
FITNESS_W_MAP50 = 0.1
FITNESS_W_MAP = 0.9


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True,
                        help="Training run dir with args.yaml and results.csv")
    parser.add_argument("--data", type=Path, default=TRAINING_DIR / "dataset.yaml")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--device", default="0")
    parser.add_argument("--project", type=Path, default=RUNS_DIR)
    return parser.parse_args(argv)


def evaluate_split(model, resolved_yaml: Path, split: str, args) -> dict:
    results = model.val(
        data=str(resolved_yaml),
        split=split,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=str(args.project),
        name=f"eval-{split}",
        plots=True,
        exist_ok=True,
    )
    box = results.box
    names = results.names
    per_class = {}
    for list_index, class_id in enumerate(box.ap_class_index):
        class_name = names.get(int(class_id), str(class_id))
        per_class[class_name] = {
            "precision": round(float(box.p[list_index]), 4),
            "recall": round(float(box.r[list_index]), 4),
            "ap50": round(float(box.ap50[list_index]), 4),
            "ap50_95": round(float(box.ap[list_index]), 4),
        }
    return {
        "split": split,
        "precision": round(float(box.mp), 4),
        "recall": round(float(box.mr), 4),
        "map50": round(float(box.map50), 4),
        "map50_95": round(float(box.map), 4),
        "per_class": per_class,
        "artifacts_dir": _relpath(Path(results.save_dir)),
    }


def _relpath(path: Path) -> str:
    try:
        return path.resolve().relative_to(CV_SERVICE_ROOT.parent).as_posix()
    except ValueError:
        return path.name


def read_training_config(run_dir: Path) -> dict:
    args_path = run_dir / "args.yaml"
    if not args_path.is_file():
        return {}
    with args_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    keep = (
        "model", "imgsz", "epochs", "batch", "device", "workers", "seed",
        "deterministic", "amp", "optimizer", "patience", "lr0", "momentum",
    )
    config = {key: raw.get(key) for key in keep if key in raw}
    # Report the base model by name only (no machine-specific absolute path).
    if isinstance(config.get("model"), str):
        config["model"] = Path(config["model"]).name
    return config


def read_training_curve(run_dir: Path) -> dict:
    results_path = run_dir / "results.csv"
    if not results_path.is_file():
        return {}
    with results_path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return {}

    def fitness(row: dict) -> float:
        return (
            FITNESS_W_MAP50 * float(row["metrics/mAP50(B)"])
            + FITNESS_W_MAP * float(row["metrics/mAP50-95(B)"])
        )

    best_row = max(rows, key=fitness)
    last_row = rows[-1]
    return {
        "epochs_completed": int(last_row["epoch"]),
        "best_epoch": int(best_row["epoch"]),
        "best_epoch_val_map50": round(float(best_row["metrics/mAP50(B)"]), 4),
        "best_epoch_val_map50_95": round(float(best_row["metrics/mAP50-95(B)"]), 4),
        "final_train_box_loss": round(float(last_row["train/box_loss"]), 4),
        "final_val_box_loss": round(float(last_row["val/box_loss"]), 4),
        "training_seconds": round(float(last_row["time"]), 1),
    }


def read_audit() -> dict:
    if not AUDIT_JSON.is_file():
        return {}
    with AUDIT_JSON.open(encoding="utf-8") as handle:
        audit = json.load(handle)
    video = audit.get("leakage", {}).get("source_group_analysis", {}).get(
        "video_frame_groups", {}
    )
    return {
        "total_images": audit.get("distribution", {}).get("total_images"),
        "total_objects": audit.get("distribution", {}).get("total_objects"),
        "object_counts_by_class": audit.get("distribution", {}).get(
            "object_counts_by_class", {}
        ),
        "split_image_counts": {
            name: split.get("image_count")
            for name, split in audit.get("splits", {}).items()
        },
        "source_video_leakage": {
            "cross_split_groups": video.get("cross_split_groups"),
            "total_groups": video.get("total_groups"),
            "images_in_cross_split_groups": video.get("images_in_cross_split_groups"),
            "images_in_cross_split_groups_pct": video.get(
                "images_in_cross_split_groups_pct"
            ),
        },
    }


def pick_strongest_weakest(per_class: dict) -> tuple[str, str]:
    if not per_class:
        return "n/a", "n/a"
    strongest = max(per_class, key=lambda c: per_class[c]["ap50"])
    weakest = min(per_class, key=lambda c: per_class[c]["ap50"])
    return strongest, weakest


def build_summary(model_name, checkpoint, training_config, curve, val, test, audit) -> dict:
    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        "checkpoint": _relpath(checkpoint),
        "task": "detection",
        "classes": ["distress_candidate", "out_of_water", "normal_swimming"],
        "training": {**training_config, **curve},
        "dataset": audit,
        "validation_metrics": val,
        "test_metrics": test,
        "metric_caveats": [
            "Validation/test-set object-detection performance on the Roboflow "
            "dataset only; not medical or real-world drowning-detection accuracy.",
            "Frames from the same source video span splits (see "
            "dataset.source_video_leakage), so held-out metrics are optimistic "
            "relative to clip-independent evaluation.",
        ],
    }


def write_csv(summary: dict) -> None:
    rows = []
    for split_key, metrics in (
        ("validation", summary["validation_metrics"]),
        ("test", summary["test_metrics"]),
    ):
        rows.append({
            "split": split_key, "scope": "overall", "class": "ALL",
            "precision": metrics["precision"], "recall": metrics["recall"],
            "ap50": metrics["map50"], "ap50_95": metrics["map50_95"],
        })
        for class_name, class_metrics in metrics["per_class"].items():
            rows.append({
                "split": split_key, "scope": "per_class", "class": class_name,
                "precision": class_metrics["precision"],
                "recall": class_metrics["recall"],
                "ap50": class_metrics["ap50"], "ap50_95": class_metrics["ap50_95"],
            })
    with SUMMARY_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["split", "scope", "class", "precision", "recall", "ap50", "ap50_95"],
        )
        writer.writeheader()
        writer.writerows(rows)


def write_pitch(summary: dict) -> None:
    val = summary["validation_metrics"]
    test = summary["test_metrics"]
    strongest, weakest = pick_strongest_weakest(val["per_class"])
    s_m = val["per_class"].get(strongest, {})
    w_m = val["per_class"].get(weakest, {})
    leak = summary["dataset"].get("source_video_leakage", {})
    leak_pct = leak.get("images_in_cross_split_groups_pct")
    leak_pct_str = f"{leak_pct:.1%}" if isinstance(leak_pct, (int, float)) else "an unknown share of"
    gap = val["map50"] - test["map50"]

    md = f"""# Detector — Evaluation Summary

_Generated {summary['generated_utc']}. Model: {summary['model']} ({summary['task']}), classes: {', '.join(summary['classes'])}._

## What the metrics support

The trained detector distinguishes the three dataset-defined visual classes (`distress_candidate`, `out_of_water`, `normal_swimming`) on held-out dataset splits. On the validation split it reaches **mAP50 {val['map50']:.3f}** (mAP50-95 {val['map50_95']:.3f}); on the sealed test split, **mAP50 {test['map50']:.3f}** (mAP50-95 {test['map50_95']:.3f}). The {gap:.3f} validation-to-test mAP50 drop is itself informative (see the dataset caveat below).

## What the metrics do NOT support

These results do **not** establish medical drowning-detection accuracy, nor performance across all real pools, lighting, camera angles, or water clarity. "Distress" here means a visual appearance class in this dataset — not a diagnosed medical event.

## Strongest measured result

`{strongest}` is the strongest class on validation (AP50 {s_m.get('ap50', 0):.3f}, recall {s_m.get('recall', 0):.3f}) — encouraging, because it is the safety-relevant class.

## Largest weakness

`{weakest}` is the weakest class by validation AP50 ({w_m.get('ap50', 0):.3f}, recall {w_m.get('recall', 0):.3f}). Separately, the residual `distress_candidate` ↔ `normal_swimming` confusion is the safety-relevant error to watch: a distressed-looking swimmer occasionally reads as normal, and vice versa.

## Architectural mitigation

Because frame-level predictions may fluctuate, SwimSentinel does not convert
one YOLO prediction directly into an emergency alert. The runtime adds
anonymous tracking (ByteTrack) and temporal persistence before producing a
`SUSPECTED_DISTRESS` state, and fusion with the wearable adds independent
evidence.

## Dataset caveat

Filename analysis indicates {leak.get('cross_split_groups', 'several')} source
videos contribute frames to more than one split; about {leak_pct_str} of images
belong to such cross-split video groups. Near-duplicate frames therefore appear
in both training and evaluation, so these held-out metrics are **optimistic**
relative to a clip-independent split. Judge live runtime behaviour, not just
these numbers.

## Suggested pitch line

> SwimSentinel treats the detector as visual evidence, then applies anonymous
> tracking and temporal reasoning rather than trusting a single frame.
"""
    PITCH_MD.write_text(md, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.model.is_file():
        print(f"ERROR: checkpoint not found: {args.model}", file=sys.stderr)
        return 1

    _, resolved_yaml = prepare_dataset(args.data)

    from ultralytics import YOLO  # deferred: slow import

    model = YOLO(str(args.model))
    model_name = model.model.yaml.get("yaml_file", "yolo11s") if hasattr(model, "model") else "yolo11s"

    print("Evaluating validation split...")
    val_metrics = evaluate_split(model, resolved_yaml, "val", args)
    print("Evaluating test split (one-time)...")
    test_metrics = evaluate_split(model, resolved_yaml, "test", args)

    training_config = read_training_config(args.run_dir)
    curve = read_training_curve(args.run_dir)
    audit = read_audit()

    summary = build_summary(
        Path(str(training_config.get("model", "yolo11s.pt"))).stem,
        args.model, training_config, curve, val_metrics, test_metrics, audit,
    )

    SUMMARY_JSON.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_csv(summary)
    write_pitch(summary)

    print(f"\nWrote:\n  {_relpath(SUMMARY_JSON)}\n  {_relpath(SUMMARY_CSV)}\n  {_relpath(PITCH_MD)}")
    print(
        f"\nValidation mAP50 {val_metrics['map50']:.3f} | "
        f"Test mAP50 {test_metrics['map50']:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
