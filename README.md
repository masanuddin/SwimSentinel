# SwimSentinel

Pool-safety decision support: wearable wristband + above-water camera + computer
vision + temporal reasoning + lifeguard dashboard. The camera service detects
persistent visual patterns consistent with suspected swimmer distress and
combines them with wearable evidence — the lifeguard stays the final
decision-maker.

Some assets are **deliberately not in Git** (dataset 416 MB, model weights,
virtualenv, training runs). This guide tells you which ones you actually need —
**most people need none of them.**

## Setup tiers — pick the lowest one that covers your work

| Tier | You want to... | Need model? | Need dataset? |
|---|---|---|---|
| **1. Frontend + mock CV** | UI work, fusion work, demo the flow | ❌ no | ❌ no |
| **2. Real CV pipeline** | Run YOLO on video/camera | ✅ `best.pt` | ❌ no |
| **3. Training / dataset audit** | Retrain or re-audit the dataset | ✅ | ✅ |

**Most teammates only need Tier 1.** Mock mode emits deterministic visual-evidence
events over the same SSE contract as the real pipeline — the frontend cannot tell
the difference, and it loads no model, no camera, no Torch.

---

## Tier 1 — Frontend + mock CV service

### Prerequisites
- **Node.js 18+**
- **Python 3.12** ← specifically 3.12. Python 3.13/3.14 do not have working
  PyTorch wheels yet. Check with `py -0p` (Windows) or `python3.12 --version`.

### 1. Clone and install the frontend
```powershell
git clone https://github.com/masanuddin/SwimSentinel.git
cd SwimSentinel
npm install
npm run dev          # http://localhost:5173
```

### 2. Create the Python venv
```powershell
py -3.12 -m venv cv-service/.venv
cv-service\.venv\Scripts\python.exe -m pip install --upgrade pip
```

### 3. Install dependencies

**If you have an NVIDIA GPU** (install CUDA Torch first, or you get a CPU-only build):
```powershell
cv-service\.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
cv-service\.venv\Scripts\python.exe -m pip install -r cv-service\requirements.txt
```

**If you have no NVIDIA GPU** (laptop, Mac, integrated graphics) — plain install is fine:
```powershell
cv-service\.venv\Scripts\python.exe -m pip install -r cv-service\requirements.txt
```
CPU works for mock mode and tests. Real inference on CPU will be slow (likely
below the 10 FPS floor) — fine for development, not for the demo.

> `cu128` matches the RTX 5090 (Blackwell/sm_120). On an older NVIDIA card use
> `cu121` instead. Verify with:
> `cv-service\.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available())"`

### 4. Run mock mode (no model, no dataset needed)
From the **repository root**:
```powershell
cv-service\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir cv-service --host 127.0.0.1 --port 8000
```
Check:
- http://127.0.0.1:8000/status → `"mode": "mock"`, `"ready": true`
- http://127.0.0.1:8000/events → SSE `heartbeat` + `visual_evidence`

The frontend reads `VITE_CV_SERVICE_URL` (default `http://127.0.0.1:8000`).
Copy `.env.example` → `.env.local` at the repo root only if you need to change
anything — the same file documents the Supabase and CV service variables, and
both the frontend and the CV service read `.env.local`.

### 5. Verify
```powershell
cv-service\.venv\Scripts\python.exe -m pytest cv-service -q   # expect: 100 passed
npm run build
```
✅ **Tier 1 done.** You can build the whole frontend and fusion against mock events.

---

## Tier 2 — Real CV pipeline (needs `best.pt`)

### Get the trained model
`cv-service/models/best.pt` is **not in Git** (18 MB binary). Get it from the
team and drop it at exactly that path (create the `models/` folder if missing):

```text
cv-service/models/best.pt
```

Sources, in order of preference:
1. **GitHub release artifact** on this repo (versioned + linkable);
2. team shared drive;
3. direct transfer from a teammate.

Verify it loaded correctly:
```powershell
cv-service\.venv\Scripts\python.exe -c "from ultralytics import YOLO; m=YOLO('cv-service/models/best.pt'); print(m.task, m.names)"
```
Expected: `detect {0: 'distress_candidate', 1: 'out_of_water', 2: 'normal_swimming'}`
Expected SHA-256: `9bb4b261ea7fc20b23dc738eca1a83623075553b5c97c793085255bc21803b38`

> If you don't have `best.pt`, **mock mode still works**. Only video/camera mode
> needs it, and it reports the missing model clearly instead of crashing.

### Run on a video file (prerecorded fallback)
```powershell
$env:CV_MODE="video"; $env:CV_CAMERA_SOURCE="C:\path\to\pool.mp4"
cv-service\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir cv-service --host 127.0.0.1 --port 8000
```

### Run on a camera
```powershell
$env:CV_MODE="camera"; $env:CV_CAMERA_SOURCE="0"    # index, or an RTSP/HTTP URL
```

`/status` should show `modelLoaded: true`, `sourceAvailable: true`, plus live
`fps` and `activeTracks`.

Other env vars: `CV_LOOP_VIDEO`, `CV_VIDEO_REALTIME` (leave on — see
`cv-service/README.md`), `CV_ZONES_FILE`. All documented in `.env.example`.

⚠️ **Never commit an env file** — it may hold Supabase keys or RTSP camera
credentials. `.env.local`, `.env`, and `cv-service/.env` are all git-ignored;
keep it that way.

---

## Tier 3 — Training / dataset audit (needs the dataset)

Only if you are retraining or re-auditing. The dataset is **not in Git** (416 MB).

1. Download manually from Roboflow (no SDK, no API key):
   https://universe.roboflow.com/object-detection-model/drowning-detection-wqiom
   → version 1 → **Download Dataset** → format **YOLOv11** (fallback: YOLOv8).
2. Extract into `cv-service/data/raw/` so you have:
   ```text
   cv-service/data/raw/<export-folder>/data.yaml
   cv-service/data/raw/<export-folder>/{train,valid,test}/{images,labels}/
   ```
   The tooling auto-discovers the folder containing `data.yaml`, so its exact
   name doesn't matter.
3. **The raw dataset is immutable** — never rename, move, relabel, rebalance, or
   delete anything under `data/raw/`. See `cv-service/README.md`.

Then:
```powershell
cv-service\.venv\Scripts\python.exe cv-service\training\audit_dataset.py
cv-service\.venv\Scripts\python.exe cv-service\training\train.py --epochs 60 --batch 32 --device 0 --name yolo11s-main
```
See the Training section in `cv-service/README.md`. Training needs a CUDA GPU —
it is not practical on CPU (~29 min on an RTX 5090).

---

## What is git-ignored and why

| Path | Size | Why ignored | How to restore |
|---|---|---|---|
| `cv-service/.venv/` | 4.8 GB | Machine-specific | `pip install` (Tier 1) |
| `cv-service/data/raw/` | 416 MB | Large, redistributable from source | Roboflow (Tier 3) |
| `cv-service/models/*.pt` | 18–19 MB | Binaries don't belong in Git history | Team share (Tier 2) |
| `cv-service/runs/` | 112 MB | Regenerated output | Re-run train/eval scripts |
| `.env.local`, `.env`, `cv-service/.env` | — | May contain Supabase keys or camera credentials | Copy from `.env.example` |

Base weights (`yolo11s.pt`) download automatically on first training run.

---

## Troubleshooting

**`torch.cuda.is_available()` is False on an NVIDIA machine**
You installed the CPU wheel. Reinstall from the CUDA index (step 3).

**`No module named app`**
Run from the **repository root** with `--app-dir cv-service`, not from inside
`cv-service/`. (Tests work from either directory.)

**Camera not found**
- Not available inside a Remote Desktop session — run locally.
- Check Windows Settings → Privacy & security → Camera.
- Try a different index (`0`, `1`, `2`).

**`model checkpoint not found`**
You're in Tier 2 without `best.pt`. Either add it, or use `CV_MODE=mock`.

**Python 3.13/3.14 errors installing torch**
Use Python 3.12: `py -3.12 -m venv cv-service/.venv`.
