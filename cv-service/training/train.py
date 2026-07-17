"""Train YOLO11 on the drowning-detection dataset.

Usage (from the repository root):

    # Smoke run (1 epoch, verifies paths / GPU / class mapping):
    cv-service\\.venv\\Scripts\\python.exe cv-service\\training\\train.py --epochs 1 --name smoke

    # Main run:
    cv-service\\.venv\\Scripts\\python.exe cv-service\\training\\train.py --epochs 60 --name yolo11s-main

Outputs go to cv-service/runs/<name>/ (git-ignored). The raw dataset is never
modified. Base weights (e.g. yolo11s.pt) download into cv-service/models/.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dataset_config import (
    CV_SERVICE_ROOT,
    DEFAULT_DATASET_YAML,
    RUNS_DIR,
    prepare_dataset,
)

MODELS_DIR = CV_SERVICE_ROOT / "models"


def resolve_model_arg(model: str) -> str:
    """Anchor bare official weight names (yolo11s.pt) to cv-service/models/.

    A path that exists (or contains a directory component) is used as-is, so
    resuming from a runs/ checkpoint still works.
    """
    path = Path(model)
    if path.exists() or path.parent != Path("."):
        return str(path)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return str(MODELS_DIR / path.name)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", default="yolo11s.pt", help="Base weights (default: yolo11s.pt)")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATASET_YAML)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--batch", type=int, default=16, help="-1 enables auto-batch")
    parser.add_argument("--device", default=None, help="e.g. 0, cpu (default: auto-select)")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--name", default="yolo11s")
    parser.add_argument("--project", type=Path, default=RUNS_DIR)
    parser.add_argument("--patience", type=int, default=15, help="Early-stopping patience (epochs)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    config, resolved_yaml = prepare_dataset(args.data)
    model_path = resolve_model_arg(args.model)

    print(f"Dataset config : {args.data}")
    print(f"Dataset root   : {config['path']}")
    print(f"Classes        : {config['names']}")
    print(f"Resolved YAML  : {resolved_yaml}")
    print(f"Model weights  : {model_path}")
    print(f"Output project : {args.project}")

    from ultralytics import YOLO  # deferred: import is slow and needs the venv

    model = YOLO(model_path)
    results = model.train(
        data=str(resolved_yaml),
        imgsz=args.imgsz,
        epochs=args.epochs,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        seed=args.seed,
        deterministic=True,
        project=str(args.project),
        name=args.name,
        patience=args.patience,
        exist_ok=False,
    )

    save_dir = Path(results.save_dir) if results is not None else None
    if save_dir is not None:
        best = save_dir / "weights" / "best.pt"
        print(f"\nTraining finished. Run directory: {save_dir}")
        if best.is_file():
            print(f"Best checkpoint: {best}")
            print(
                "After validation approval, copy it to the runtime location:\n"
                f'  Copy-Item "{best}" "{MODELS_DIR / "best.pt"}"'
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
