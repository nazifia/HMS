"""Off-request-thread writer for background work (activity logging).

Activity logging used to spawn a fresh daemon thread per request, each opening
its own database connection. Under load that is unbounded thread and connection
churn, and the concurrent writers fight each other for the database — on SQLite
that surfaces as "database table is locked", and the losing write is dropped.

One worker thread draining a bounded queue keeps the request fast, serialises
the writes so they no longer collide, and caps the damage when logging falls
behind: the queue drops instead of growing without limit.

Set ACTIVITY_LOG_ASYNC = False (the default under tests) to run the work inline
on the request thread instead — the behaviour is identical, just synchronous.
"""
import logging
import queue
import threading

from django.conf import settings
from django.db import connection

logger = logging.getLogger(__name__)

# Bounded: logging that cannot keep up must shed load, not consume memory.
_QUEUE_MAXSIZE = 1000

_queue = None
_worker = None
_lock = threading.Lock()


def _async_enabled():
    return getattr(settings, "ACTIVITY_LOG_ASYNC", True)


def _drain():
    while True:
        job = _queue.get()
        func, args, kwargs = job
        try:
            func(*args, **kwargs)
        except Exception as e:  # noqa: BLE001 - logging must never take the app down
            logger.error(f"Background activity logging error: {e}")
        finally:
            _queue.task_done()
            # Nothing else queued: hand the connection back rather than holding
            # it open (and holding locks) while idle.
            if _queue.empty():
                connection.close()


def _ensure_worker():
    """Start the single worker thread on first use."""
    global _queue, _worker
    if _worker is not None and _worker.is_alive():
        return True
    with _lock:
        if _worker is not None and _worker.is_alive():
            return True
        if _queue is None:
            _queue = queue.Queue(maxsize=_QUEUE_MAXSIZE)
        _worker = threading.Thread(
            target=_drain, name="activity-log-writer", daemon=True
        )
        _worker.start()
    return True


def submit(func, *args, **kwargs):
    """Run `func` off the request thread, or inline when async is disabled."""
    if not _async_enabled():
        try:
            func(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Activity logging error: {e}")
        return

    _ensure_worker()
    try:
        _queue.put_nowait((func, args, kwargs))
    except queue.Full:
        logger.warning("Activity log queue full; dropping one entry.")
