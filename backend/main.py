"""FastAPI app: API + admin + static frontend (frontend/dist) in one process on port 8000."""
from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select

from . import ledger
from .config import DATA, ROOT, get_settings
from .db import Ticket, Unanswered, init_db, session
from .logging_utils import log, request_id_var, setup_logging
from .media import UploadError, check_audio, check_media, check_text
from .pipeline import HelpDesk, ensure_dirs
from .providers import registry

logger = logging.getLogger("app")
DIST = ROOT / "frontend" / "dist"
desk = HelpDesk()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    ensure_dirs()
    init_db()
    await desk.startup()
    log(logger, "startup complete", stores=list(desk.retriever.stores), guides=len(desk.retriever.guides))
    yield


app = FastAPI(title="RRR AI Help Desk", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().allowed_origins.split(",") if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
_hits: dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def request_context(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    request_id_var.set(rid)
    if request.url.path == "/api/ask":
        ip = request.client.host if request.client else "?"
        q, now = _hits[ip], time.time()
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= get_settings().rate_limit_per_min:
            return JSONResponse({"error": "Too many requests. Please wait a minute and try again."}, status_code=429)
        q.append(now)
    t0 = time.perf_counter()
    resp = await call_next(request)
    resp.headers["x-request-id"] = rid
    if request.url.path.startswith(("/api", "/admin")):
        log(logger, "request", path=request.url.path, status=resp.status_code, ms=int((time.perf_counter() - t0) * 1000))
    return resp


# ---------------- public API ----------------
@app.get("/health")
async def health():
    return {"status": "ok", "guides": len(desk.retriever.guides), "index": list(desk.retriever.stores)}


@app.get("/metrics")
async def metrics():
    m = dict(desk.metrics)
    n = max(1, m["answered"] + m["handoffs"])
    m["stage_ms_avg"] = {k: round(v / n) for k, v in m["stage_ms_total"].items()}
    return m


@app.post("/api/ask")
async def ask(
    request: Request,
    text: str = Form(""),
    language: str = Form("auto"),
    session_id: str = Form(""),
    audio: UploadFile | None = File(None),
    media: UploadFile | None = File(None),
):
    try:
        check_text(text)
        audio_bytes = await audio.read() if audio else None
        if audio_bytes:
            check_audio(audio_bytes)
        media_bytes, mime, name = None, "", ""
        if media:
            media_bytes = await media.read()
            mime, name = media.content_type or "", media.filename or ""
            if media_bytes:
                check_media(media_bytes, mime)
        if not (text.strip() or audio_bytes or media_bytes):
            raise UploadError("Please speak, type a question, or upload a photo or video.")
    except UploadError as e:
        return JSONResponse({"error": str(e)}, status_code=413 if "larger" in str(e) or "longer" in str(e) else 400)
    try:
        result = await desk.ask(text=text, language=language, session_id=session_id[:64], audio=audio_bytes or None,
                                media=media_bytes or None, media_mime=mime, media_name=name)
    except Exception as e:  # noqa: BLE001
        desk.metrics["errors"] += 1
        logger.exception("ask failed")
        return JSONResponse({"error": "Something went wrong while preparing the answer. Please try again.", "detail": type(e).__name__},
                            status_code=500)
    result["request_id"] = request_id_var.get()
    return result


class FeedbackIn(BaseModel):
    session_id: str
    solved: bool
    request_id: str = ""


@app.post("/api/feedback")
async def feedback(body: FeedbackIn):
    from .db import Feedback

    with session() as db:
        db.add(Feedback(session_id=body.session_id[:64], request_id=body.request_id[:64], solved=int(body.solved)))
        db.commit()
    return await desk.feedback(body.session_id[:64], body.solved)


@app.get("/api/products")
async def products():
    return json.loads((DATA / "products.json").read_text(encoding="utf-8"))


@app.get("/api/demo-questions")
async def demo_questions():
    return desk.demo_questions


@app.get("/api/config")
async def public_config():
    s = get_settings()
    return {"limits": {"audio_seconds": s.max_audio_seconds, "audio_mb": s.max_audio_mb, "image_mb": s.max_image_mb,
                       "video_mb": s.max_video_mb, "video_seconds": s.max_video_seconds, "text_chars": s.max_text_chars}}


# ---------------- admin ----------------
def _auth(token: str | None) -> None:
    if not token or token != get_settings().admin_token:
        raise HTTPException(status_code=401, detail="Admin token required")


@app.get("/admin")
async def admin_page():
    return RedirectResponse("/#/admin")


@app.get("/admin/tickets")
async def admin_tickets(x_admin_token: str | None = Header(None)):
    _auth(x_admin_token)
    with session() as db:
        rows = db.scalars(select(Ticket).order_by(Ticket.id.desc()).limit(200)).all()
    return [{"id": t.id, "created_at": t.created_at.isoformat(), "reason": t.reason, "question": t.question, "language": t.language,
             "fault_id": t.fault_id, "confidence": t.confidence, "summary": t.summary, "media": t.media_evidence, "status": t.status}
            for t in rows]


@app.get("/admin/unanswered")
async def admin_unanswered(x_admin_token: str | None = Header(None)):
    _auth(x_admin_token)
    with session() as db:
        rows = db.scalars(select(Unanswered).order_by(Unanswered.id.desc()).limit(200)).all()
    return [{"id": u.id, "created_at": u.created_at.isoformat(), "question": u.question, "language": u.language,
             "best_fault": u.best_fault, "confidence": u.confidence} for u in rows]


@app.get("/admin/usage")
async def admin_usage(x_admin_token: str | None = Header(None)):
    _auth(x_admin_token)
    return ledger.summary()


@app.get("/admin/providers")
async def admin_providers(x_admin_token: str | None = Header(None)):
    _auth(x_admin_token)
    return {"providers": registry.status(), "index": list(desk.retriever.stores), "metrics": await metrics()}


# ---------------- static ----------------
if (DATA / "videos").exists():
    app.mount("/media/videos", StaticFiles(directory=DATA / "videos"), name="videos")
if (DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
async def spa(path: str):
    f = DIST / path
    if path and f.is_file() and DIST in f.resolve().parents:
        return FileResponse(f)
    index = DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse({"message": "Frontend not built. API is running; see README."})
