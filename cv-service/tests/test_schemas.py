from datetime import datetime, timezone

from app.schemas import VisualEvidenceEvent


def test_visual_evidence_schema_accepts_contract_event():
    event = VisualEvidenceEvent(
        timestamp=datetime.now(timezone.utc),
        cameraId="POOL-CAM-01",
        trackId=7,
        zoneId=3,
        rawClass="distress_candidate",
        detectionConfidence=0.84,
        motionState="low",
        lowMotionDurationMs=2800,
        classPersistenceMs=2200,
        visibility="clear",
        visualState="suspected_distress",
        evidence=["persistent_distress_appearance", "limited_displacement"],
    )

    assert event.rawClass == "distress_candidate"
    assert event.zoneId == 3
