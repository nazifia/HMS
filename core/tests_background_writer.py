"""The shared background writer.

Replaces per-request daemon threads, so the properties that matter are: work
still runs, one slow job cannot be lost silently, and a flood sheds load
instead of growing the queue without limit.
"""
import queue
import threading

from django.test import TestCase, override_settings

from core import background_writer


def _workers():
    return [t for t in threading.enumerate() if t.name == "activity-log-writer"]


class BackgroundWriterTest(TestCase):
    # No global reset between tests: the worker is process-wide by design, and
    # tearing it down here would orphan the running thread.

    @override_settings(ACTIVITY_LOG_ASYNC=False)
    def test_runs_inline_when_async_disabled(self):
        seen = []
        before = len(_workers())
        background_writer.submit(seen.append, "done")
        assert seen == ["done"]
        assert len(_workers()) == before, "inline mode must not start a worker"

    @override_settings(ACTIVITY_LOG_ASYNC=False)
    def test_inline_errors_do_not_propagate(self):
        def boom():
            raise ValueError("logging exploded")

        background_writer.submit(boom)  # must not raise

    @override_settings(ACTIVITY_LOG_ASYNC=True)
    def test_worker_runs_the_job(self):
        done = threading.Event()
        background_writer.submit(done.set)
        assert done.wait(timeout=5), "worker never ran the job"
        assert background_writer._worker.daemon

    @override_settings(ACTIVITY_LOG_ASYNC=True)
    def test_one_worker_serves_many_jobs(self):
        results = queue.Queue()
        for i in range(20):
            background_writer.submit(results.put, i)
        collected = [results.get(timeout=5) for _ in range(20)]
        assert sorted(collected) == list(range(20))
        # 20 jobs, one thread — that is the whole point of the change.
        assert len(_workers()) == 1, _workers()

    @override_settings(ACTIVITY_LOG_ASYNC=True)
    def test_worker_survives_a_failing_job(self):
        done = threading.Event()

        def boom():
            raise ValueError("logging exploded")

        background_writer.submit(boom)
        background_writer.submit(done.set)
        assert done.wait(timeout=5), "worker died on the failing job"

    @override_settings(ACTIVITY_LOG_ASYNC=True)
    def test_full_queue_drops_instead_of_blocking(self):
        release = threading.Event()
        background_writer._ensure_worker()
        background_writer.submit(release.wait)  # occupies the worker

        # Fill past capacity; submit must return immediately either way.
        for _ in range(background_writer._QUEUE_MAXSIZE + 50):
            background_writer.submit(lambda: None)

        assert background_writer._queue.qsize() <= background_writer._QUEUE_MAXSIZE
        release.set()
