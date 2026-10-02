import asyncio
import hashlib
import hmac
import json
import sys
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from . import db
from .config import config
from .models import CreateTasks, InspectRequest
from .security import validate_public_url


@asynccontextmanager
async def lifespan(app):
    db.initialize()
    yield


app = FastAPI(title="All-in-One Video Downloader", version="1.0.0", lifespan=lifespan)
inspect_slots = asyncio.Semaphore(2)


def session_signature() -> str:
    return hmac.new(config.access_token.encode(), b"aio-video-session-v1", hashlib.sha256).hexdigest()


def authenticated(request: Request) -> bool:
    if not config.access_token:
        return True
    return hmac.compare_digest(request.cookies.get("aio_session", ""), session_signature())


@app.middleware("http")
async def access_control(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin and urlsplit(origin).netloc != request.headers.get("host"):
        return JSONResponse({"detail": "只接受同源请求"}, status_code=403)
    length = request.headers.get("content-length", "0")
    if not length.isdigit() or int(length) > 1024 * 1024:
        return JSONResponse({"detail": "请求内容过大"}, status_code=413)
    if request.url.path.startswith("/api/") and request.url.path not in {"/api/health", "/api/session"}:
        if not authenticated(request):
            return JSONResponse({"detail": "请输入访问口令"}, status_code=401)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(ValueError)
async def bad_value(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=400)


class SessionRequest(BaseModel):
    token: str = Field(max_length=256)


@app.get("/api/session")
def session(request: Request):
    return {"required": bool(config.access_token), "authenticated": authenticated(request)}


@app.post("/api/session")
def login(data: SessionRequest, request: Request):
    if config.access_token and not hmac.compare_digest(data.token, config.access_token):
        raise HTTPException(401, "访问口令不正确")
    response = JSONResponse({"authenticated": True})
    secure = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    response.set_cookie("aio_session", session_signature(), httponly=True, secure=secure,
                        samesite="strict", max_age=604800, path="/api")
    return response


@app.delete("/api/session")
def logout():
    response = JSONResponse({"authenticated": False})
    response.delete_cookie("aio_session", path="/api")
    return response


@app.post("/api/inspect")
async def inspect_video(data: InspectRequest):
    if inspect_slots.locked():
        raise HTTPException(429, "解析任务较多，请稍后重试")
    async with inspect_slots:
        url = await run_in_threadpool(validate_public_url, data.url)
        process = await asyncio.create_subprocess_exec(sys.executable, "-m", "app.inspect", url,
                                                       stdout=asyncio.subprocess.PIPE,
                                                       stderr=asyncio.subprocess.PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=50)
        except (TimeoutError, asyncio.CancelledError):
            if process.returncode is None:
                process.kill()
            await process.communicate()
            raise HTTPException(504, "解析超时，平台可能需要登录或当前网络不可达")
        try:
            result = json.loads(stdout.decode())
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(502, "解析服务未返回有效结果，请稍后重试")
        if process.returncode or "error" in result:
            raise HTTPException(422, result.get("error", "此链接暂时无法解析"))
        return result


@app.get("/api/tasks")
def tasks():
    return db.list_tasks()


@app.post("/api/tasks", status_code=201)
def create_tasks(data: CreateTasks):
    urls = [validate_public_url(url) for url in data.urls]
    added, skipped = db.create_tasks(data, urls)
    return {"added": added, "skipped": skipped}


def require_task(task_id: str, raw: bool = False):
    task = db.get_task(task_id, raw)
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@app.get("/api/tasks/{task_id}")
def task_detail(task_id: str):
    return require_task(task_id)


@app.post("/api/tasks/{task_id}/actions/{action}")
def task_action(task_id: str, action: str):
    require_task(task_id)
    actions = {
        "pause": (("queued", "downloading", "processing"), "paused"),
        "resume": (("paused",), "queued"),
        "cancel": (("queued", "downloading", "processing", "paused"), "cancelled"),
        "retry": (("failed", "cancelled"), "queued"),
    }
    if action not in actions:
        raise HTTPException(404, "未知操作")
    allowed, target = actions[action]
    values = {"status": target, "speed": 0, "eta": 0, "error": ""}
    if action == "retry":
        values.update(progress=0, scheduled_at=None)
    if not db.update_task(task_id, values, allowed):
        raise HTTPException(409, "任务状态已变化，请刷新后再试")
    return require_task(task_id)


@app.get("/api/events")
async def events(request: Request):
    async def stream():
        previous = ""
        while not await request.is_disconnected():
            current = json.dumps(await run_in_threadpool(db.list_tasks), ensure_ascii=False)
            if current != previous:
                yield f"event: tasks\ndata: {current}\n\n"
                previous = current
            else:
                yield ": heartbeat\n\n"
            await asyncio.sleep(1.5)
    return StreamingResponse(stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"})


from .library import router as library_router  # noqa: E402

app.include_router(library_router)

from .learning import router as learning_router  # noqa: E402

app.include_router(learning_router)

from .status import router as status_router  # noqa: E402

app.include_router(status_router)
