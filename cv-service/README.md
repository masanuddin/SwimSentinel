# CV Service

Camera + computer-vision service. Emits visual-evidence events over SSE for the
lifeguard dashboard: YOLO11s detection, anonymous ByteTrack tracking, pool
ROI/zones, and temporal reasoning before any state is reported.

Track IDs are anonymous and temporary — a track ID is not a person, an
identity, or a wristband owner. Detection confidence is an object-detection
score, never a drowning probability.

Setup (venv, dependencies, model, dataset) is in the [root README](../README.md).

## Run

From the **repository root**, using the local venv interpreter:

```powershell
cv-service\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir cv-service --host 127.0.0.1 --port 8000
```

- **Expected working directory:** the repository root (the folder containing
  `cv-service/`). `--app-dir cv-service` puts `app` on the import path.
- **Path resolution:** configuration paths resolve from stable anchors derived
  from the source location, not the current working directory, so the service
  also works if launched from inside `cv-service/`. Relative defaults such as
  `cv-service/config` resolve against the repository root; paths not starting
  with `cv-service` resolve against the `cv-service/` root. Absolute paths in
  environment variables are honoured unchanged.
- **Environment:** `.env.local` at the repo root is the shared file — Vite
  reads it too, so one file configures both the frontend and this service.
  `.env` (loaded first) and `cv-service/.env` (loaded last) are also honoured,
  so a CV-only override never has to touch the shared file. All variables are
  documented in [`.env.example`](../.env.example).
- **Override the config directory:** set `CV_CONFIG_DIR` (relative to the repo
  root, or absolute). `thresholds.yaml` and `zones.example.json` are read from
  there.

## Endpoints

- `GET /status`
- `GET /events`

### Expected `/status` in mock mode

```json
{
  "service": "cv-service",
  "mode": "mock",
  "ready": true,
  "thresholdsLoaded": true
}
```

In video/camera mode `/status` also reports `modelLoaded`, `sourceAvailable`,
`device`, `fps`, `avgInferenceMs`, `activeTracks`, and `latestError`.

### Events and cadence

`GET /events` is a Server-Sent Events stream with two named events:

- `heartbeat` — cadence from `events.heartbeat_ms` (default 3000 ms).
- `visual_evidence` — one track's evidence at a point in time. In mock mode the
  cadence is `events.mock_event_ms` (default 1000 ms); in video/camera mode it
  is emitted on meaningful state change plus a bounded periodic refresh — never
  once per frame.

`trackId`, `zoneId`, `rawClass`, and `detectionConfidence` are **nullable**:
`camera_unavailable` has no track or zone, `track_lost` has no live confidence,
and a detection outside the pool ROI is a real track with `zoneId: null`.
Consumers must treat `zoneId: null` as "not in a pool zone" and never escalate
it as in-pool evidence.

## Runtime modes

`CV_MODE` selects the source. Mock mode never loads OpenCV, Torch,
Ultralytics, or a camera.

| Mode | Source | Notes |
|---|---|---|
| `mock` (default) | none | Deterministic mock evidence. No model, no capture. |
| `video` | `CV_CAMERA_SOURCE=<path>` | Prerecorded fallback. Played at the file's real frame rate. |
| `camera` | `CV_CAMERA_SOURCE=<index or URL>` | e.g. `0`, or an RTSP/HTTP URL. No index is assumed. |

```powershell
# Prerecorded fallback
$env:CV_MODE="video"; $env:CV_CAMERA_SOURCE="C:\footage\pool.mp4"
cv-service\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir cv-service --host 127.0.0.1 --port 8000
```

**Real-time pacing.** Temporal states are measured in wall-clock seconds, so a
prerecorded file is paced to its own frame rate. Without this, an 8-second clip
would decode in ~2s on a fast GPU and silently defeat every persistence gate.
Set `CV_VIDEO_REALTIME=0` only to benchmark raw throughput. A live camera is
never paced — it already delivers frames in real time.

## Runtime pipeline

```text
source -> YOLO11s -> ByteTrack -> pool ROI/zones -> per-track history
       -> smoothed normalized motion -> temporal visual state -> SSE
```

- `app/vision.py` — model, capture, inference, tracking, FPS, debug overlay.
- `app/zones.py` — ROI/zone polygons, validation, scaling, assignment.
- `app/state.py` — history, motion, persistence, hysteresis, state machine.
- `app/pipeline.py` — mode selection, orchestration, one shared producer.

A single shared producer serves all SSE clients, so connecting two browsers
never opens two cameras or loads two models. Slow clients have their oldest
events dropped rather than stalling the pipeline.

## Configuration

`config/thresholds.yaml` holds runtime engineering values — rehearsal/demo
numbers, **not** medical thresholds. Tune only from measured behaviour.

| Group | Controls |
|---|---|
| `detection` | input size, device, preprocessing, tracking vs evidence confidence |
| `tracking` | ByteTrack thresholds, time-based track loss and expiry |
| `history` / `motion` | history window, centroid smoothing, normalized-movement and inactivity thresholds |
| `state` | watch / distress / inactivity persistence, recovery (hysteresis) |
| `zones` | anchor used to map a detection to a pool zone |
| `events` | heartbeat, mock cadence, periodic refresh, minimum emit interval |

Two settings are easy to get wrong:

- **`detection.preprocess`** (`stretch`, default) — the dataset was exported
  with images stretched to 640×640, so inference must distort the same way.
  Letterboxing a 16:9 source measurably costs recall and skews uncertain
  detections toward `distress_candidate`. `letterbox` exists only as a rollback.
- **`detection.evidence_confidence`** — detections below it keep a track alive
  (continuity) but can never escalate a state.

`config/zones.example.json` defines the pool ROI and zone polygons against a
declared `frameSize`; polygons are scaled automatically to the real capture
resolution. Point `CV_ZONES_FILE` at your own file for a different camera.

## Dataset

- **Source:** Roboflow Universe — "Drowning Detection"
  (`object-detection-model/drowning-detection-wqiom`, version 1)
- **URL:** https://universe.roboflow.com/object-detection-model/drowning-detection-wqiom
- **License:** CC BY 4.0 (as declared in the export's `data.yaml` and
  `README.dataset.txt`; the dataset is "Provided by a Roboflow user" — verify
  provenance before any public/commercial distribution beyond the hackathon).
- **Attribution:** credit the Roboflow Universe project above wherever the
  dataset or a model trained on it is presented.

Download instructions are in the [root README](../README.md) (Tier 3). Expected
layout — the tooling auto-discovers the folder containing `data.yaml`, so the
export folder name does not matter:

```text
cv-service/data/raw/<export-folder>/
├── data.yaml
├── train/images + train/labels   (8051 images)
├── valid/images + valid/labels   (1178 images)
└── test/images  + test/labels    ( 755 images)
```

### Classes

Source class IDs are preserved; only display names change (see
[`training/dataset.yaml`](training/dataset.yaml)):

| ID | Source name         | Product-facing name  |
|---:|---------------------|----------------------|
| 0  | Drowning            | `distress_candidate` |
| 1  | Person out of water | `out_of_water`       |
| 2  | Swimming            | `normal_swimming`    |

`distress_candidate` is deliberate: a detection is visual appearance evidence,
not a medical drowning diagnosis.

### Policies and limitations

- **Raw data is immutable.** Never rename, move, relabel, rebalance, augment,
  or delete anything under `data/raw/`. Project-specific configuration lives in
  `training/`.
- **No dataset merging.** This is the only dataset — no synthetic data, no
  extra annotations, no second dataset.
- Images were resized to 640×640 by stretching, so aspect ratios are distorted
  relative to a live camera feed (see `detection.preprocess` above).
- Footage conditions (pools, camera angles, water clarity) differ from the demo
  pool — expect a domain gap.
- Run `training/audit_dataset.py` for measured class balance, duplicate, and
  integrity findings (`training/dataset_audit.json`).

## Training

All commands run from the **repository root**. Training needs a CUDA GPU — it
is not practical on CPU (~29 min on an RTX 5090).

```powershell
# 1. Audit the dataset (reads only; never modifies it)
cv-service\.venv\Scripts\python.exe cv-service\training\audit_dataset.py

# 2. Smoke training — verifies paths, class mapping, GPU, run output.
#    Smoke metrics are meaningless; do not read into them.
cv-service\.venv\Scripts\python.exe cv-service\training\train.py --epochs 1 --name smoke

# 3. Main training
cv-service\.venv\Scripts\python.exe cv-service\training\train.py --epochs 60 --batch 32 --name yolo11s-main

# 4. Validate a checkpoint
cv-service\.venv\Scripts\python.exe cv-service\training\validate.py --model cv-service\runs\yolo11s-main\weights\best.pt
```

Outputs land in `runs/<name>/` (git-ignored). Useful flags: `--model`,
`--data`, `--imgsz`, `--batch` (-1 = auto), `--device`, `--workers`, `--seed`,
`--patience`.

`validate.py` reports precision, recall, mAP50, mAP50-95, and per-class
metrics, and saves plots (confusion matrix included). These are validation-set
object-detection metrics on this dataset — not medical accuracy, and not
real-world drowning-detection accuracy.

**Fallback model.** YOLO11n is not trained by default. Train it
(`--model yolo11n.pt`) only if live-camera benchmarking shows YOLO11s cannot
hold ≥10–15 FPS.

## Models and weights

The service loads its detector from `models/best.pt` (configurable via
`CV_MODEL_PATH`). If the file is missing, mock mode still works — it never
loads a model — but video/camera modes cannot start; they report the missing
model clearly instead of crashing.

- **Base weights** (`yolo11s.pt`) are downloaded automatically by
  `training/train.py` into `models/` on first use.
- **Trained checkpoints** are written by Ultralytics to `runs/<name>/weights/`
  (git-ignored). After a run is reviewed and approved, copy the chosen
  checkpoint into place:

```powershell
Copy-Item cv-service\runs\yolo11s-main\weights\best.pt cv-service\models\best.pt
```

`*.pt` / `*.onnx` are git-ignored — model binaries are tens of MB and don't
belong in ordinary Git history (this repo does not use Git LFS). Share
`best.pt` via a GitHub release artifact (preferred — versioned and linkable),
the team's shared drive, or direct transfer. The receiver drops it at
`models/best.pt` — nothing else to configure.

## Evaluation

```powershell
# Detector metrics: validation + one-time sealed test evaluation
cv-service\.venv\Scripts\python.exe cv-service\evaluation\build_evaluation.py `
  --model   cv-service\runs\yolo11s-main\weights\best.pt `
  --run-dir cv-service\runs\yolo11s-main

# Representative FP / FN / confusion examples
cv-service\.venv\Scripts\python.exe cv-service\evaluation\representative_errors.py `
  --model cv-service\runs\yolo11s-main\weights\best.pt

# Runtime behaviour: pipeline, FPS, state transitions
cv-service\.venv\Scripts\python.exe cv-service\evaluation\run_runtime_eval.py
```

Committed artifacts in `evaluation/`:

| File | Contents |
|---|---|
| `detector_summary.json` | Training config, training-curve summary, dataset counts and class distribution, source-video leakage, validation/test metrics, per-class metrics, caveats. |
| `detector_summary.csv` | Flat per-split / per-class precision, recall, AP50, AP50-95. |
| `detector_pitch_summary.md` | Plain-language interpretation: what the metrics do and do not support, strongest result, largest weakness, dataset caveat. |
| `representative_errors.json` | A small reviewed set of representative false positives, false negatives, and class confusions. |
| `runtime_evaluation.json` | Per-scenario runtime behaviour, plus what was **not executed** and why. |

Larger run artifacts (confusion matrices, PR/F1 curves, `results.csv`,
annotated prediction batches, overlay videos) live under the git-ignored
`runs/` directory.

### Interpreting the numbers

- These are **object-detection metrics on one Roboflow dataset** — never label
  them "drowning accuracy".
- The test split is evaluated **once**, after the checkpoint is chosen. It is
  never used to select epochs, thresholds, or the checkpoint.
- Source-video frames span splits (see `detector_summary.json` →
  `dataset.source_video_leakage`), so held-out metrics are **optimistic**
  relative to a clip-independent split. This caveat travels with every metric.
- `run_runtime_eval.py` builds **constructed** clips from real test-split
  images with controlled synthetic motion. Detections, tracking, FPS, and
  latency are real; the temporal composition is not. It validates the
  *pipeline*, not detector generalization to a real pool. Scenarios needing
  continuous real footage or live hardware are reported as NOT EXECUTED, never
  faked.

## Tests

```powershell
cv-service\.venv\Scripts\python.exe -m pytest cv-service -q
```

Tests run from either the repository root or `cv-service/` — path resolution is
covered explicitly for both working directories.
