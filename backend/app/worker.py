import os
import shutil
import signal
import subprocess
import sys
import time

from . import db
from .config import config

stopping = False


def stop(*_):
    global stopping
    stopping = True


def storage_bytes() -> int:
    total = 0
    for path in config.media_dir.rglob("*"):
        try:
            if path.is_file():
                total += path.stat().st_size
        except FileNotFoundError:
            pass
    return total


def terminate(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
    else:
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        if os.name != "nt":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait()


def main():
    db.initialize()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while not stopping:
        db.set_settings({"worker_heartbeat": db.now()})
        db.recover_expired_tasks()
        task = db.claim_task()
        if not task:
            time.sleep(1)
            continue
        task_id = task["id"]
        limit = db.get_settings()["storage_limit_gb"] * 1024**3
        if storage_bytes() >= limit or shutil.disk_usage(config.data_dir).free < 100 * 1024**2:
            db.update_task(
                task_id, {"status": "failed", "error": "存储空间不足，请清理媒体或调整存储限额"}, ("downloading",)
            )
            continue
        process = subprocess.Popen([sys.executable, "-m", "app.download", task_id], start_new_session=os.name != "nt")
        started = time.monotonic()
        try:
            while process.poll() is None:
                db.set_settings({"worker_heartbeat": db.now()})
                live = db.get_task(task_id, raw=True)
                if stopping or not live or live["status"] not in {"downloading", "processing"}:
                    terminate(process)
                    break
                db.update_task(task_id, {"lease_at": db.now()}, ("downloading", "processing"))
                limit = db.get_settings()["storage_limit_gb"] * 1024**3
                if storage_bytes() > limit or shutil.disk_usage(config.data_dir).free < 50 * 1024**2:
                    terminate(process)
                    db.update_task(
                        task_id,
                        {"status": "failed", "error": "已达到存储限额，下载已停止", "speed": 0},
                        ("downloading", "processing"),
                    )
                    break
                if time.monotonic() - started > 5400:
                    terminate(process)
                    db.update_task(
                        task_id,
                        {"status": "failed", "error": "任务超过 90 分钟，请重试或缩短下载内容", "speed": 0},
                        ("downloading", "processing"),
                    )
                    break
                time.sleep(1)
        finally:
            terminate(process)
            if stopping:
                db.update_task(
                    task_id, {"status": "queued", "speed": 0, "lease_at": None}, ("downloading", "processing")
                )
            else:
                db.update_task(
                    task_id,
                    {"status": "failed", "speed": 0, "error": "下载进程意外退出，请重试"},
                    ("downloading", "processing"),
                )
            db.update_task(task_id, {"lease_at": None})
    db.set_settings({"worker_heartbeat": None})


if __name__ == "__main__":
    main()
