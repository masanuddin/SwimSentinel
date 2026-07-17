import pytest

from app.config import Settings
from app.pipeline import event_intervals, mock_event_stream


def test_event_intervals_read_from_config():
    heartbeat_s, mock_event_s = event_intervals(Settings())
    # Matches config/thresholds.yaml: heartbeat_ms 3000, mock_event_ms 1000.
    assert heartbeat_s == pytest.approx(3.0)
    assert mock_event_s == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_mock_event_ms_faster_than_heartbeat_yields_extra_visual_events(monkeypatch):
    # heartbeat every 300ms, visual evidence every 100ms -> 3 visual per heartbeat.
    monkeypatch.setattr(
        "app.pipeline.event_intervals", lambda settings: (0.3, 0.1)
    )

    stream = mock_event_stream(Settings())
    frames = []
    for _ in range(6):
        frames.append(await anext(stream))
    await stream.aclose()

    # First two are the immediate heartbeat + visual burst.
    assert frames[0].startswith("event: heartbeat")
    assert frames[1].startswith("event: visual_evidence")

    heartbeats = sum(1 for f in frames if f.startswith("event: heartbeat"))
    visuals = sum(1 for f in frames if f.startswith("event: visual_evidence"))
    # Visual evidence must arrive more frequently than heartbeats.
    assert visuals > heartbeats
