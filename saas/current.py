"""Per-request current tenant, stored in thread-local.

ponytail: thread-local, fine for sync WSGI/dev server. If you move to async
(ASGI) views, swap this for contextvars.ContextVar — same 3-function API.
"""
import threading

_state = threading.local()


def set_current_hospital(hospital):
    _state.hospital = hospital


def get_current_hospital():
    return getattr(_state, "hospital", None)


def clear_current_hospital():
    _state.hospital = None
