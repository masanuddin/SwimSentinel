from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import get_settings, load_thresholds
from app.pipeline import event_stream, get_producer, shutdown_producer
from app.schemas import StatusResponse

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Mock mode: no producer, no model, no capture.
    if settings.mode != "mock":
        await get_producer(settings).start()
    try:
        yield
    finally:
        if settings.mode != "mock":
            await shutdown_producer()


app = FastAPI(title="CV Service", version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/status", response_model=StatusResponse)
def status() -> StatusResponse:
    thresholds_loaded = True
    try:
        load_thresholds(settings)
    except Exception:
        thresholds_loaded = False

    runtime_status: dict = {}
    ready = settings.mode == "mock" and thresholds_loaded
    status_text = "mock mode ready" if settings.mode == "mock" else "configured"

    if settings.mode != "mock":
        runtime = get_producer(settings).runtime
        if runtime is not None:
            runtime_status = runtime.status()
            ready = bool(
                thresholds_loaded
                and runtime_status.get("modelLoaded")
                and runtime_status.get("sourceAvailable")
            )
            if ready:
                status_text = f"{settings.mode} mode running"
            elif runtime_status.get("latestError"):
                status_text = f"{settings.mode} mode unavailable: {runtime_status['latestError']}"
            else:
                status_text = f"{settings.mode} mode starting"
        else:
            status_text = f"{settings.mode} mode not started"

    return StatusResponse(
        mode=settings.mode,
        cameraId=settings.camera_id,
        ready=ready,
        status=status_text,
        modelPath=settings.model_path,
        configDir=settings.config_dir,
        thresholdsLoaded=thresholds_loaded,
        allowedOrigins=settings.origins,
        timestamp=datetime.now(timezone.utc),
        **runtime_status,
    )


@app.get("/events")
async def events() -> StreamingResponse:
    return StreamingResponse(
        event_stream(settings),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
