import asyncio
import logging
import shutil
import tempfile
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

import pandas as pd
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .agent.client import OllamaClient
from .agent.investigator import investigate
from .agent.schemas import InvestigationRequest
from .config import ROOT, settings
from .data.loader import DatasetError, load_dataset
from .data.profiler import profile_dataset
from .models import DatasetProfile
from .visualization.schemas import ChartSpec
from .visualization.validation import build_chart

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)


@dataclass
class Session:
    root: Path
    dataset_id: str = ""
    file_name: str = ""
    directory: Path | None = None
    snapshot: Path | None = None
    df: pd.DataFrame | None = None
    profile: DatasetProfile | None = None
    phase: str = "idle"
    loading: bool = False
    investigations: dict = field(default_factory=dict)
    active_id: str | None = None
    task: asyncio.Task | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


@asynccontextmanager
async def lifespan(app):
    with tempfile.TemporaryDirectory(prefix="dataset-investigator-") as directory:
        app.state.session = Session(root=Path(directory))
        log.info("Dataset Investigator started; local session only")
        yield
        task = app.state.session.task
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(title="Dataset Investigator", lifespan=lifespan)
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"]
)


@app.middleware("http")
async def local_request_guard(request: Request, call_next):
    # Stop cross-origin websites from invoking localhost uploads/model execution.
    origin = request.headers.get("origin")
    if origin:
        from urllib.parse import urlparse

        if urlparse(origin).hostname not in {"localhost", "127.0.0.1", "::1"}:
            return JSONResponse(
                {
                    "code": "ORIGIN_REJECTED",
                    "message": "Only local application requests are allowed.",
                    "details": None,
                },
                status_code=403,
            )
    length = request.headers.get("content-length", "0")
    try:
        if int(length) > settings.max_upload_mb * 1024 * 1024 + 1024 * 1024:
            return JSONResponse(
                {
                    "code": "FILE_TOO_LARGE",
                    "message": f"Files must be {settings.max_upload_mb} MB or smaller.",
                    "details": None,
                },
                status_code=413,
            )
    except ValueError:
        return JSONResponse(
            {"code": "INVALID_REQUEST", "message": "Invalid Content-Length.", "details": None},
            status_code=400,
        )
    return await call_next(request)


@app.exception_handler(DatasetError)
async def dataset_error(request, exc):
    status = (
        409
        if exc.code == "BUSY"
        else 404
        if exc.code == "NO_DATASET"
        else 413
        if exc.code == "FILE_TOO_LARGE"
        else 400
    )
    return JSONResponse(
        {"code": exc.code, "message": str(exc), "details": None}, status_code=status
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(
        {
            "code": "INVALID_REQUEST",
            "message": "Check the request fields and try again.",
            "details": [
                {"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()
            ],
        },
        status_code=422,
    )


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    log.exception("Request failed", exc_info=exc)
    return JSONResponse(
        {
            "code": "INTERNAL_ERROR",
            "message": "The operation could not be completed. Check the backend log for details.",
            "details": None,
        },
        status_code=500,
    )


def current(request: Request) -> Session:
    session = request.app.state.session
    if session.profile is None:
        raise DatasetError("NO_DATASET", "Upload a dataset to begin.")
    return session


def dataset_payload(session: Session):
    if session.profile is None:
        return None
    return {
        "dataset_id": session.dataset_id,
        "file_name": session.file_name,
        "rows": session.profile.row_count,
        "columns": session.profile.column_count,
        "profile": session.profile,
        "investigations": list(session.investigations.values()),
        "active_investigation_id": session.active_id,
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "max_upload_mb": settings.max_upload_mb,
        "agent_max_steps": settings.agent_max_steps,
    }


@app.get("/api/datasets/current")
async def get_current(request: Request):
    return dataset_payload(request.app.state.session)


@app.get("/api/datasets/profile")
async def get_profile(request: Request):
    return current(request).profile


@app.get("/api/datasets/progress")
async def progress(request: Request):
    session = request.app.state.session
    return {"phase": session.phase, "loading": session.loading}


def prepare_dataset(path, extension, name, session):
    session.phase = "Reading dataset"
    df = load_dataset(path, extension)
    session.phase = f"Profiling {len(df):,} rows · types, distributions and findings"
    profile = profile_dataset(df, name, settings)
    session.phase = "Creating read-only analysis snapshot"
    snapshot = path.parent / "snapshot.parquet"
    df.to_parquet(snapshot, index=False)
    snapshot.chmod(0o400)
    path.chmod(0o400)
    return df, profile, snapshot


async def ingest(file: UploadFile, request: Request):
    session = request.app.state.session
    async with session.lock:
        if session.loading or session.active_id:
            raise DatasetError(
                "BUSY", "An upload or investigation is in progress. Wait for it to finish."
            )
        session.loading = True
        session.phase = "Receiving upload"
    directory = session.root / str(uuid4())
    directory.mkdir(mode=0o700)
    try:
        name = Path((file.filename or "dataset").replace("\\", "/")).name
        extension = Path(name).suffix.lower()
        if extension not in {".csv", ".parquet"}:
            raise DatasetError("UNSUPPORTED_FILE", "Choose a CSV or Parquet file.")
        path = directory / ("source" + extension)
        total = 0
        with path.open("wb") as stream:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > settings.max_upload_mb * 1024 * 1024:
                    raise DatasetError(
                        "FILE_TOO_LARGE", f"Files must be {settings.max_upload_mb} MB or smaller."
                    )
                stream.write(chunk)
        log.info("Upload received: bytes=%d extension=%s", total, extension)
        df, profile, snapshot = await run_in_threadpool(
            prepare_dataset, path, extension, name, session
        )
        previous = session.directory
        session.dataset_id, session.file_name = directory.name, name
        session.df, session.profile, session.snapshot, session.directory = (
            df,
            profile,
            snapshot,
            directory,
        )
        session.investigations.clear()
        session.phase = "complete"
        if previous:
            shutil.rmtree(previous)
        return dataset_payload(session)
    except BaseException:
        shutil.rmtree(directory, ignore_errors=True)
        session.phase = "failed"
        raise
    finally:
        await file.close()
        session.loading = False


@app.post("/api/datasets")
async def upload(request: Request, file: UploadFile = File(...)):
    return await ingest(file, request)


@app.post("/api/datasets/demo")
async def demo(request: Request):
    with (ROOT / "examples" / "suspicious_customers.csv").open("rb") as stream:
        return await ingest(UploadFile(file=stream, filename="suspicious_customers.csv"), request)


@app.post("/api/datasets/chart")
async def chart(spec: ChartSpec, request: Request):
    session = current(request)
    try:
        return await run_in_threadpool(build_chart, spec, session.df, session.profile)
    except ValueError as exc:
        raise DatasetError("INVALID_CHART", str(exc)) from exc


@app.get("/api/ollama/status")
async def ollama_status():
    status = await OllamaClient(settings).status()
    log.debug("Ollama status: %s", status["code"])
    return status


@app.post("/api/investigations", status_code=202)
async def start_investigation(body: InvestigationRequest, request: Request):
    session = current(request)
    async with session.lock:
        if session.loading or session.active_id:
            raise DatasetError(
                "BUSY", "Investigation in progress. Wait for it to finish before starting another."
            )
        finding = None
        if body.finding_id:
            finding = next((f for f in session.profile.findings if f.id == body.finding_id), None)
            if finding is None:
                raise DatasetError(
                    "FINDING_NOT_FOUND", "This finding is not part of the current dataset."
                )
        client = OllamaClient(settings)
        status = await client.status()
        if not status["connected"] or not status["model_available"]:
            return JSONResponse(
                {"code": status["code"], "message": status["message"], "details": None},
                status_code=503,
            )
        investigation_id = str(uuid4())
        state = {
            "investigation_id": investigation_id,
            "question": body.question,
            "status": "running",
            "max_steps": settings.agent_max_steps,
            "steps_remaining": settings.agent_max_steps,
            "current_activity": "Preparing dataset context",
            "trace": [],
            "charts": [],
            "final_finding": None,
            "error": None,
        }
        session.investigations[investigation_id] = state
        session.active_id = investigation_id
        session.task = asyncio.create_task(investigate(state, session, client, settings, finding))
        return state


@app.get("/api/investigations/{investigation_id}")
async def get_investigation(investigation_id: str, request: Request):
    session = current(request)
    state = session.investigations.get(investigation_id)
    if state is None:
        return JSONResponse(
            {
                "code": "INVESTIGATION_NOT_FOUND",
                "message": "This investigation is not part of the current session.",
                "details": None,
            },
            status_code=404,
        )
    return state
