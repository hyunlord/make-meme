"""Tests for make_meme.jobs: JobManager lifecycle, persistence across restarts, cancellation."""

from __future__ import annotations

import asyncio

from make_meme.jobs import JobManager


async def test_job_succeeds_and_persists_result(tmp_path):
    manager = JobManager(jobs_dir=tmp_path, max_concurrent=1)

    async def work(ctx):
        ctx.update(stage="working", progress=0.5)
        return {"answer": 42}

    job = manager.submit("demo", work)
    finished = await manager.wait(job.id)
    assert finished.status == "succeeded"
    assert finished.result == {"answer": 42}
    assert finished.progress == 1.0

    reloaded = JobManager(jobs_dir=tmp_path, max_concurrent=1)
    assert reloaded.get(job.id).status == "succeeded"


async def test_job_failure_is_captured_not_raised(tmp_path):
    manager = JobManager(jobs_dir=tmp_path, max_concurrent=1)

    async def work(ctx):
        raise RuntimeError("boom")

    job = manager.submit("demo", work)
    finished = await manager.wait(job.id)
    assert finished.status == "failed"
    assert "boom" in finished.error


async def test_job_can_be_cancelled_cooperatively(tmp_path):
    manager = JobManager(jobs_dir=tmp_path, max_concurrent=1)
    started = asyncio.Event()

    async def work(ctx):
        started.set()
        for _ in range(500):
            ctx.check_cancelled()
            await asyncio.sleep(0.01)
        return {}

    job = manager.submit("demo", work)
    await started.wait()
    assert manager.cancel(job.id) is True
    finished = await manager.wait(job.id)
    assert finished.status == "cancelled"


async def test_cancel_unknown_or_finished_job_returns_false(tmp_path):
    manager = JobManager(jobs_dir=tmp_path, max_concurrent=1)
    assert manager.cancel("does-not-exist") is False

    async def work(ctx):
        return {}

    job = manager.submit("demo", work)
    await manager.wait(job.id)
    assert manager.cancel(job.id) is False


async def test_restart_marks_running_jobs_as_failed(tmp_path):
    manager = JobManager(jobs_dir=tmp_path, max_concurrent=1)
    gate = asyncio.Event()

    async def work(ctx):
        await gate.wait()
        return {}

    job = manager.submit("demo", work)
    for _ in range(200):
        if manager.get(job.id).status == "running":
            break
        await asyncio.sleep(0.01)
    assert manager.get(job.id).status == "running"

    # Simulate a server restart: a fresh JobManager reads the same jobs_dir while the
    # "old" job file on disk still says status=running.
    restarted = JobManager(jobs_dir=tmp_path, max_concurrent=1)
    assert restarted.get(job.id).status == "failed"
    assert restarted.get(job.id).error == "server restarted"

    gate.set()
    await manager.wait(job.id)  # let the original task finish so it doesn't leak into other tests


async def test_queued_jobs_run_sequentially_with_max_concurrent_one(tmp_path):
    manager = JobManager(jobs_dir=tmp_path, max_concurrent=1)
    order: list[str] = []

    def make_work(name, delay):
        async def work(ctx):
            order.append(f"start:{name}")
            await asyncio.sleep(delay)
            order.append(f"end:{name}")
            return {}

        return work

    job1 = manager.submit("demo", make_work("a", 0.05))
    job2 = manager.submit("demo", make_work("b", 0.0))
    await manager.wait(job1.id)
    await manager.wait(job2.id)

    assert order == ["start:a", "end:a", "start:b", "end:b"]


async def test_unreadable_job_file_is_skipped_not_fatal(tmp_path):
    (tmp_path / "corrupt.json").write_text("{not valid json")
    manager = JobManager(jobs_dir=tmp_path, max_concurrent=1)
    assert manager.list() == []


async def test_real_asyncio_cancellation_resolves_job_not_stuck_running(tmp_path):
    """A genuine asyncio.CancelledError (BaseException) from the pipeline -- not just our
    own cooperative ctx.check_cancelled()/JobCancelled -- must still resolve the job,
    instead of leaving it "running" forever (CancelledError isn't caught by `except
    Exception`, so it used to escape _run entirely before the status/persist code ran)."""

    manager = JobManager(jobs_dir=tmp_path, max_concurrent=1)
    started = asyncio.Event()

    async def work(ctx):
        started.set()
        await asyncio.sleep(10)  # would hang the test if cancellation weren't handled
        return {}

    job = manager.submit("demo", work)
    await started.wait()

    task = manager._tasks[job.id]
    task.cancel()  # genuine asyncio cancellation, not ctx.cancelled.set()

    finished = await manager.wait(job.id)
    assert finished.status == "cancelled"


async def test_restart_marks_queued_jobs_as_failed_too(tmp_path):
    manager = JobManager(jobs_dir=tmp_path, max_concurrent=1)
    gate = asyncio.Event()

    async def blocking_first(ctx):
        await gate.wait()
        return {}

    async def noop(ctx):
        return {}

    first = manager.submit("demo", blocking_first)
    second = manager.submit("demo", noop)  # queues behind `first` (max_concurrent=1)

    for _ in range(200):
        if manager.get(second.id).status == "queued":
            break
        await asyncio.sleep(0.01)
    assert manager.get(second.id).status == "queued"

    restarted = JobManager(jobs_dir=tmp_path, max_concurrent=1)
    assert restarted.get(second.id).status == "failed"
    assert restarted.get(second.id).error == "server restarted"

    gate.set()
    await manager.wait(first.id)
    await manager.wait(second.id)


async def test_job_error_is_type_and_message_truncated(tmp_path):
    manager = JobManager(jobs_dir=tmp_path, max_concurrent=1)

    async def work(ctx):
        raise ValueError("x" * 1000)

    job = manager.submit("demo", work)
    finished = await manager.wait(job.id)
    assert finished.status == "failed"
    assert finished.error.startswith("ValueError: ")
    assert len(finished.error) <= 600
