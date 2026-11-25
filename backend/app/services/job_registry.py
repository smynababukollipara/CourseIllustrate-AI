"""In-process guards for duplicate runs and cancellation."""
from threading import Lock

_lock = Lock()
_running_keys = set()
_cancelled_ids = set()


def try_begin(key: str) -> bool:
    with _lock:
        if key in _running_keys:
            return False
        _running_keys.add(key)
        return True


def finish(key: str) -> None:
    with _lock:
        _running_keys.discard(key)


def request_cancel(generation_id: str) -> None:
    with _lock:
        _cancelled_ids.add(generation_id)


def is_cancelled(generation_id: str | None) -> bool:  # noqa: syntax kept for 3.10+
    if not generation_id:
        return False
    with _lock:
        return generation_id in _cancelled_ids


def clear_cancel(generation_id: str) -> None:
    with _lock:
        _cancelled_ids.discard(generation_id)
