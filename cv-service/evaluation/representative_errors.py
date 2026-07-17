"""Collect a small, reviewed set of representative detector errors.

Runs the trained checkpoint on a capped, deterministic sample of the
validation split, greedily matches predictions to ground truth by IoU, and
records representative:

* false positives (a confident prediction with no matching ground-truth box);
* false negatives (a ground-truth box the model missed);
* class confusions (a well-localized prediction with the wrong class).

Writes a committed JSON summary (cv-service/evaluation/representative_errors.json,
no bulk dataset images) and saves a few pitch-safe annotated crops under the
git-ignored cv-service/runs/eval-errors/ directory.

Usage (from the repository root):

    cv-service\\.venv\\Scripts\\python.exe cv-service\\evaluation\\representative_errors.py ^
        --model cv-service\\runs\\yolo11s-main\\weights\\best.pt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2

EVALUATION_DIR = Path(__file__).resolve().parent
CV_SERVICE_ROOT = EVALUATION_DIR.parent
TRAINING_DIR = CV_SERVICE_ROOT / "training"
if str(TRAINING_DIR) not in sys.path:
    sys.path.insert(0, str(TRAINING_DIR))

from dataset_config import RUNS_DIR, load_dataset_config  # noqa: E402

ERRORS_JSON = EVALUATION_DIR / "representative_errors.json"
ERROR_CROPS_DIR = RUNS_DIR / "eval-errors"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=TRAINING_DIR / "dataset.yaml")
    parser.add_argument("--split", default="val", choices=("val", "test"))
    parser.add_argument("--sample", type=int, default=500, help="Max images to scan")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou-match", type=float, default=0.45)
    parser.add_argument("--per-category", type=int, default=6, help="Examples to keep per category")
    parser.add_argument("--device", default="0")
    return parser.parse_args(argv)


def load_gt(label_path: Path, width: int, height: int) -> list[dict]:
    boxes = []
    if not label_path.is_file():
        return boxes
    for line in label_path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) != 5:
            continue
        cls, cx, cy, w, h = int(fields[0]), *(float(v) for v in fields[1:])
        boxes.append({
            "class_id": cls,
            "xyxy": [
                (cx - w / 2) * width, (cy - h / 2) * height,
                (cx + w / 2) * width, (cy + h / 2) * height,
            ],
        })
    return boxes


def iou(box_a: list[float], box_b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / (area_a + area_b - inter)


def draw_and_save(image, boxes, out_path: Path) -> None:
    ERROR_CROPS_DIR.mkdir(parents=True, exist_ok=True)
    annotated = image.copy()
    for box in boxes:
        x1, y1, x2, y2 = (int(v) for v in box["xyxy"])
        color = box.get("color", (0, 0, 255))
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        cv2.putText(annotated, box["label"], (x1, max(0, y1 - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    cv2.imwrite(str(out_path), annotated)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.model.is_file():
        print(f"ERROR: checkpoint not found: {args.model}", file=sys.stderr)
        return 1

    config = load_dataset_config(args.data)
    names = {int(k): v for k, v in config["names"].items()} \
        if isinstance(config["names"], dict) else dict(enumerate(config["names"]))
    images_dir = Path(config["path"]) / str(config["val" if args.split == "val" else "test"])
    labels_dir = images_dir.parent / "labels"

    image_files = sorted(
        p for p in images_dir.iterdir()
        if p.suffix.lower() in IMAGE_EXTENSIONS
    )[: args.sample]
    if not image_files:
        print(f"ERROR: no images under {images_dir}", file=sys.stderr)
        return 1

    from ultralytics import YOLO  # deferred: slow import

    model = YOLO(str(args.model))

    categories: dict[str, list[dict]] = {
        "false_positive": [], "false_negative": [], "class_confusion": []
    }
    counts = {"false_positive": 0, "false_negative": 0, "class_confusion": 0, "true_positive": 0}

    for image_path in image_files:
        result = model.predict(
            source=str(image_path), conf=args.conf, device=args.device, verbose=False
        )[0]
        height, width = result.orig_shape
        gts = load_gt(labels_dir / f"{image_path.stem}.txt", width, height)
        preds = [
            {
                "class_id": int(cls),
                "conf": float(conf),
                "xyxy": [float(v) for v in xyxy],
            }
            for cls, conf, xyxy in zip(
                result.boxes.cls.tolist(),
                result.boxes.conf.tolist(),
                result.boxes.xyxy.tolist(),
            )
        ]

        gt_matched = [False] * len(gts)
        for pred in sorted(preds, key=lambda p: -p["conf"]):
            best_iou, best_gt = 0.0, -1
            for gt_index, gt in enumerate(gts):
                if gt_matched[gt_index]:
                    continue
                score = iou(pred["xyxy"], gt["xyxy"])
                if score > best_iou:
                    best_iou, best_gt = score, gt_index
            if best_iou >= args.iou_match:
                gt_matched[best_gt] = True
                gt = gts[best_gt]
                if gt["class_id"] == pred["class_id"]:
                    counts["true_positive"] += 1
                else:
                    counts["class_confusion"] += 1
                    _record(categories, "class_confusion", args, image_path, names,
                            gt_class=gt["class_id"], pred_class=pred["class_id"],
                            conf=pred["conf"], iou=best_iou, box=pred["xyxy"], gt_box=gt["xyxy"])
            else:
                counts["false_positive"] += 1
                _record(categories, "false_positive", args, image_path, names,
                        gt_class=None, pred_class=pred["class_id"],
                        conf=pred["conf"], iou=round(best_iou, 3), box=pred["xyxy"])
        for gt_index, matched in enumerate(gt_matched):
            if not matched:
                counts["false_negative"] += 1
                _record(categories, "false_negative", args, image_path, names,
                        gt_class=gts[gt_index]["class_id"], pred_class=None,
                        conf=None, iou=None, box=gts[gt_index]["xyxy"])

    summary = {
        "split": args.split,
        "images_scanned": len(image_files),
        "conf_threshold": args.conf,
        "iou_match_threshold": args.iou_match,
        "counts": counts,
        "examples": {
            # Drop internal box coords from the committed JSON; keep interpretation.
            cat: [
                {k: v for k, v in ex.items() if not k.endswith("_box")}
                for ex in examples
            ]
            for cat, examples in categories.items()
        },
        "note": (
            "Representative reviewed errors on a capped validation sample; "
            "not exhaustive. Confidence/IoU are object-detection quantities, "
            "not medical certainty."
        ),
    }
    ERRORS_JSON.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("Error counts (sampled):", counts)
    print(f"Wrote {ERRORS_JSON.relative_to(CV_SERVICE_ROOT.parent)}")
    print(f"Annotated crops (git-ignored): {ERROR_CROPS_DIR}")
    return 0


def _record(categories, category, args, image_path, names, *, gt_class, pred_class,
            conf, iou, box, gt_box=None) -> None:
    if len(categories[category]) >= args.per_category:
        return
    example = {
        "split": args.split,
        "file": image_path.name,
        "ground_truth": names.get(gt_class) if gt_class is not None else "none",
        "predicted": names.get(pred_class) if pred_class is not None else "none",
        "confidence": round(conf, 3) if conf is not None else None,
        "iou_with_best_gt": iou,
        "interpretation": _interpret(category, names, gt_class, pred_class),
        "_pred_box": box,
    }
    if gt_box is not None:
        example["_gt_box"] = gt_box
    categories[category].append(example)

    image = cv2.imread(str(image_path))
    if image is not None:
        draw_boxes = []
        if pred_class is not None:
            draw_boxes.append({"xyxy": box, "color": (0, 0, 255),
                               "label": f"pred:{names.get(pred_class)}"})
        if gt_box is not None:
            draw_boxes.append({"xyxy": gt_box, "color": (0, 200, 0),
                               "label": f"gt:{names.get(gt_class)}"})
        elif gt_class is not None and pred_class is None:
            draw_boxes.append({"xyxy": box, "color": (0, 200, 0),
                               "label": f"gt(missed):{names.get(gt_class)}"})
        out = ERROR_CROPS_DIR / f"{category}_{len(categories[category])}_{image_path.stem[:24]}.jpg"
        draw_and_save(image, draw_boxes, out)


def _interpret(category, names, gt_class, pred_class) -> str:
    if category == "false_positive":
        return f"Model predicted {names.get(pred_class)} where there is no labeled object."
    if category == "false_negative":
        return f"Model missed a labeled {names.get(gt_class)} object."
    return (
        f"Localized correctly but classified {names.get(pred_class)} "
        f"instead of {names.get(gt_class)}."
    )


if __name__ == "__main__":
    raise SystemExit(main())
