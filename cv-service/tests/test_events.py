import pytest

from app.config import Settings
from app.pipeline import mock_event_stream


@pytest.mark.asyncio
async def test_mock_event_stream_emits_heartbeat_and_visual_evidence():
    settings = Settings()
    stream = mock_event_stream(settings)

    first = await anext(stream)
    second = await anext(stream)
    await stream.aclose()

    assert first.startswith("event: heartbeat")
    assert second.startswith("event: visual_evidence")
    assert '"cameraId":"POOL-CAM-01"' in second
    assert '"rawClass":"distress_candidate"' in second
