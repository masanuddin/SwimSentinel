import os
import subprocess
import sys
from pathlib import Path

from app.config import (
    CV_SERVICE_ROOT,
    REPO_ROOT,
    Settings,
    load_thresholds,
    resolve_repo_path,
)

CHECK_SCRIPT = (
    "from app.config import get_settings; "
    "s = get_settings(); "
    "print(s.thresholds_path.exists(), s.zones_path.exists())"
)


def test_default_config_paths_resolve_without_doubling():
    settings = Settings()
    assert settings.thresholds_path.exists()
    assert settings.zones_path.exists()
    # Guard against the cv-service/cv-service/config regression.
    assert "cv-service" + os.sep + "cv-service" not in str(settings.thresholds_path)


def test_load_thresholds_reads_events_section():
    thresholds = load_thresholds(Settings())
    assert thresholds["events"]["heartbeat_ms"] == 3000
    assert thresholds["events"]["mock_event_ms"] == 1000


def test_absolute_env_override_is_preserved():
    absolute = REPO_ROOT / "cv-service" / "config"
    assert resolve_repo_path(str(absolute)) == absolute
    # An arbitrary absolute path is returned unchanged.
    marker = Path("/tmp/some/absolute/path").resolve()
    assert resolve_repo_path(str(marker)).is_absolute()


def _run_check(cwd: Path) -> str:
    result = subprocess.run(
        [sys.executable, "-c", CHECK_SCRIPT],
        cwd=cwd,
        env={**os.environ, "PYTHONPATH": str(CV_SERVICE_ROOT)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_config_resolves_from_repo_root_cwd():
    assert _run_check(REPO_ROOT) == "True True"


def test_config_resolves_from_cv_service_cwd():
    assert _run_check(CV_SERVICE_ROOT) == "True True"


def test_env_files_cover_the_repo_root_convention_in_precedence_order():
    """.env.example tells the team to copy it to `.env.local` at the repo root.

    That file must therefore be read, or every CV_* variable would be ignored
    silently. cv-service/.env stays supported as an override, so it comes last.
    """
    env_files = [Path(p) for p in Settings.model_config["env_file"]]
    assert env_files == [
        REPO_ROOT / ".env",
        REPO_ROOT / ".env.local",
        CV_SERVICE_ROOT / ".env",
    ]
    assert all(path.is_absolute() for path in env_files)


def test_env_example_documents_every_cv_setting():
    """.env.example is shared with the frontend, so it can drift out from under us.

    Every CV_* setting must stay listed there — it is the one file a teammate
    copies to `.env.local`. A setting missing from it is invisible: the service
    silently keeps its default instead of reporting an unknown option.
    """
    env_example = REPO_ROOT / ".env.example"
    assert env_example.is_file(), (
        f"{env_example} is missing. It documents both the Supabase and CV "
        "settings, and README.md tells teammates to copy it to .env.local."
    )
    documented = env_example.read_text(encoding="utf-8")
    aliases = [
        field.alias
        for field in Settings.model_fields.values()
        if field.alias and field.alias.startswith("CV_")
    ]
    missing = [alias for alias in aliases if alias not in documented]
    assert not missing, (
        f"{sorted(missing)} not documented in .env.example.\n"
        "Add a line (commented out is fine) under its '--- CV service ---' "
        "section. If that whole section was dropped while editing the file, "
        "restore it: the frontend and the CV service share this one file."
    )
