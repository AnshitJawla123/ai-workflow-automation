"""In-process async job runner. Survives restarts by re-reading queued JobRun rows.
Zero external infra — pure asyncio + SQLite-backed queue.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime
from typing import Callable, Dict

from sqlalchemy.orm import Session

from ...core.config import settings
from ...db.session import SessionLocal
from ...models import JobRun, Document
from .ws_bus import emit

log = logging.getLogger("jobs.runner")


class JobRunner:
    """Singleton async worker pool that processes documents through the pipeline."""

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._workers: list = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._handler: Callable | None = None
        self._started = False

    def set_handler(self, handler: Callable):
        """Handler is `async def handler(document_id: int) -> None`."""
        self._handler = handler

    def start(self):
        if self._started:
            return
        self._started = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="job-runner")
        self._thread.start()
        log.info("job runner started with %d workers", settings.pipeline_max_workers)

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        for _ in range(settings.pipeline_max_workers):
            self._loop.create_task(self._worker())
        self._loop.create_task(self._requeue_pending())
        self._loop.run_forever()

    async def _worker(self):
        while True:
            doc_id = await self._queue.get()
            if self._handler is None:
                log.error("no handler set; dropping doc %s", doc_id)
                continue
            try:
                await self._handler(doc_id)
            except Exception as e:
                log.exception("worker failed on doc %s: %s", doc_id, e)
            finally:
                self._queue.task_done()

    async def _requeue_pending(self):
        """On startup, re-queue any documents stuck in non-terminal states."""
        await asyncio.sleep(2)
        db: Session = SessionLocal()
        try:
            pending = db.query(Document).filter(
                Document.status.in_(["uploaded", "preprocessing", "ocr", "extracting", "validating"])
            ).all()
            for d in pending:
                log.info("requeue stuck doc %s status=%s", d.id, d.status)
                self.submit(d.id)
        finally:
            db.close()

    def submit(self, document_id: int):
        """Thread-safe submission."""
        if not self._loop:
            log.error("runner not started")
            return
        async def _put():
            await self._queue.put(document_id)
        asyncio.run_coroutine_threadsafe(_put(), self._loop)


runner = JobRunner()


def record_job(db: Session, document_id: int, stage: str, status: str, error: str | None = None, result: dict | None = None) -> JobRun:
    job = JobRun(document_id=document_id, stage=stage, status=status, error=error, result=result,
                 started_at=datetime.utcnow(),
                 finished_at=datetime.utcnow() if status in ("success", "failed") else None)
    db.add(job)
    db.commit()
    db.refresh(job)
    emit("job.update", {"document_id": document_id, "stage": stage, "status": status, "error": error})
    return job
