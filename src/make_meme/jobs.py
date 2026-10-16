"""In-process async job manager with on-disk persistence.

Long-running work (AI generation) runs as a background job so MCP tool calls
return quickly; callers poll ``get_job``. At most one job runs at a time
(others queue), and job state is persisted to disk so it survives a server
restart (a job caught mid-``running`` is marked ``failed``).
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import get_settings

logger = logging.getLogger(__name__)

JobStatus = str  # "queued" | "running" | "succeeded" | "failed" | "cancelled"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class JobCancelled(Exception):
    """Raised inside a job coroutine (via JobContext.check_cancelled) when cancelled."""


@dataclass
class Job:
    id: str
    kind: str
    status: JobStatus
    stage: str = ""
    progress: float = 0.0
    message: str = ""
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Job:
        return cls(**data)


class JobContext:
    """Passed to a job's coroutine to report progress and check for cancellation."""

    def __init__(self, job: Job, manager: JobManager) -> None:
        self._job = job
        self._manager = manager
        self.cancelled = asyncio.Event()

    @property
    def job_id(self) -> str:
        return self._job.id

    def update(
        self,
        *,
        stage: str | None = None,
        progress: float | None = None,
        message: str | None = None,
    ) -> None:
        if stage is not None:
            self._job.stage = stage
        if progress is not None:
            self._job.progress = max(0.0, min(1.0, progress))
        if message is not None:
            self._job.message = message
        self._job.updated_at = _now_iso()
        self._manager._persist(self._job)

    def check_cancelled(self) -> None:
        if self.cancelled.is_set():
            raise JobCancelled("job was cancelled")


class JobManager:
    """Runs at most ``max_concurrent`` job coroutines at a time, persisting state to disk."""

    def __init__(self, jobs_dir: Path | None = None, max_concurrent: int = 1) -> None:
        settings = get_settings()
        self.jobs_dir = jobs_dir or settings.jobs_dir
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, Job] = {}
        self._contexts: dict[str, JobContext] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._load_existing()

    def _load_existing(self) -> None:
        for path in sorted(self.jobs_dir.glob("*.json")):
            try:
                job = Job.from_json(json.loads(path.read_text()))
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                logger.warning("skipping unreadable job file %s: %s", path, exc)
                continue
            if job.status == "running":
                job.status = "failed"
                job.error = "server restarted"
                job.updated_at = _now_iso()
                self._write(job)
            self._jobs[job.id] = job

    def _write(self, job: Job) -> None:
        (self.jobs_dir / f"{job.id}.json").write_text(json.dumps(job.to_json(), indent=2))

    def _persist(self, job: Job) -> None:
        self._write(job)

    def submit(self, kind: str, coro_factory: Callable[[JobContext], Awaitable[dict[str, Any]]]) -> Job:
        """Create a new job, persist it, and schedule its coroutine. Returns immediately."""

        now = _now_iso()
        job = Job(id=uuid.uuid4().hex, kind=kind, status="queued", created_at=now, updated_at=now)
        self._jobs[job.id] = job
        self._write(job)
        ctx = JobContext(job, self)
        self._contexts[job.id] = ctx
        task = asyncio.ensure_future(self._run(job, ctx, coro_factory))
        self._tasks[job.id] = task
        return job

    async def _run(
        self,
        job: Job,
        ctx: JobContext,
        coro_factory: Callable[[JobContext], Awaitable[dict[str, Any]]],
    ) -> None:
        async with self._semaphore:
            if ctx.cancelled.is_set():
                job.status = "cancelled"
                job.updated_at = _now_iso()
                self._write(job)
                return
            job.status = "running"
            job.updated_at = _now_iso()
            self._write(job)
            try:
                result = await coro_factory(ctx)
                job.result = result
                job.progress = 1.0
                job.status = "succeeded"
            except JobCancelled:
                job.status = "cancelled"
            except Exception as exc:  # any failure becomes a job failure, not a server crash
                logger.exception("job %s (%s) failed", job.id, job.kind)
                job.status = "failed"
                job.error = str(exc)
            job.updated_at = _now_iso()
            self._write(job)

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        return sorted(self._jobs.values(), key=lambda j: j.created_at)

    def cancel(self, job_id: str) -> bool:
        """Request cancellation of a queued/running job. Returns whether a job was found to cancel."""

        job = self._jobs.get(job_id)
        ctx = self._contexts.get(job_id)
        if job is None or job.status not in ("queued", "running"):
            return False
        if ctx is not None:
            ctx.cancelled.set()
        return True

    async def wait(self, job_id: str, timeout: float | None = None) -> Job:
        """Await a submitted job's task to finish and return its final :class:`Job`."""

        task = self._tasks.get(job_id)
        if task is not None:
            await asyncio.wait_for(task, timeout=timeout)
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        return job
