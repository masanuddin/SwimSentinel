"""Make the `app` package importable regardless of the pytest working directory.

Tests import `from app.main import app`, which requires the `cv-service/` root on
sys.path. Running pytest from the repository root (without `--app-dir`) would
otherwise fail collection. Anchoring to this file's directory keeps tests
working from both the repository root and `cv-service/`.
"""

import sys
from pathlib import Path

CV_SERVICE_ROOT = Path(__file__).resolve().parent
if str(CV_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(CV_SERVICE_ROOT))
