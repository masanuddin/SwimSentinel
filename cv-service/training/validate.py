"""Report validation-set object-detection performance for a trained checkpoint.

Usage (from the repository root):

    cv-service\\.venv\\Scripts\\python.exe cv-service\\training\\validate.py ^
        --model cv-service\\runs\\yolo11s-main\\weights\\best.pt

Reports precision, recall, mAP50, mAP50-95, and per-class metrics on the
chosen split, and saves plots (including the confusion matrix) under
cv-service/runs/. These numbers describe validation-set object-detection
performance on the Roboflow dataset only — they are not medical accuracy and
not real-world drowning-detection accuracy.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dataset_config import DEFAULT_DATASET_YAML, RUNS_DIR, prepare_dataset


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--model",
        type=Path,
        required=True,
        help="Checkpoint to validate, e.g. cv-service/runs/<name>/weights/best.pt",
    )
    parser.add_argument("--data", type=Path, default=DEFAULT_DATASET_YAML)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default=None, help="e.g. 0, cpu (default: auto-select)")
    parser.add_argument("--split", choices=("val", "test"), default="val")
    parser.add_argument("--name", default="validate")
    parser.add_argument("--project", type=Path, default=RUNS_DIR)
    return parser.parse_args(argv)


def check_model_path(model_path: Path) -> None:
    if not model_path.is_file():
        print(
            f"ERROR: model checkpoint not found: {model_path}\n"
            "Train first (cv-service/training/train.py) or point --model at an\n"
            "existing checkpoint such as cv-service/runs/<name>/weights/best.pt.",
            file=sys.stderr,
        )
        raise SystemExit(1)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    check_model_path(args.model)
    config, resolved_yaml = prepare_dataset(args.data)

    print(f"Checkpoint     : {args.model}")
    print(f"Dataset root   : {config['path']}")
    print(f"Split          : {args.split}")

    from ultralytics import YOLO  # deferred: import is slow and needs the venv

    model = YOLO(str(args.model))
    results = model.val(
        data=str(resolved_yaml),
        split=args.split,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=str(args.project),
        name=args.name,
        plots=True,
    )

    box = results.box
    print(f"\n-- {args.split}-set object-detection performance --")
    print(f"precision : {box.mp:.4f}")
    print(f"recall    : {box.mr:.4f}")
    print(f"mAP50     : {box.map50:.4f}")
    print(f"mAP50-95  : {box.map:.4f}")

    names = results.names
    print("\n-- Per-class AP --")
    for list_index, class_id in enumerate(box.ap_class_index):
        class_name = names.get(int(class_id), str(class_id))
        print(
            f"  {class_name:>20}: AP50 {box.ap50[list_index]:.4f}  "
            f"AP50-95 {box.ap[list_index]:.4f}"
        )

    print(f"\nPlots (incl. confusion matrix) saved to: {results.save_dir}")
    print(
        "Note: these are validation-set object-detection metrics on the Roboflow\n"
        "dataset, not medical or real-world drowning-detection accuracy."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
