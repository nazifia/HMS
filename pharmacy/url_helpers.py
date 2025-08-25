"""Small utility helpers for defensive URL reversing.

Functions:
- safe_reverse(view_name, namespace='pharmacy', fallback='/')
    Try namespaced reverse first, fall back to un-namespaced reverse, then a literal fallback path.

This helper is intentionally lightweight and logs failures instead of raising so callers
can use a stable URL even if a name changes during refactors.
"""
from typing import Optional

from django.urls import reverse, NoReverseMatch
import logging

logger = logging.getLogger(__name__)


def safe_reverse(view_name: str, namespace: Optional[str] = "pharmacy", fallback: str = "/") -> str:
    """Resolve a URL by trying several strategies and return a fallback if all fail.

    Order of attempts:
    1. namespaced: "{namespace}:{view_name}" (if namespace provided)
    2. plain view_name
    3. return the provided fallback

    This avoids raising NoReverseMatch in edge cases (stale code, in-progress refactors).
    The function logs failures at DEBUG and a final WARNING when falling back.

    Args:
        view_name: the view name (without namespace) to resolve.
        namespace: optional namespace to try first.
        fallback: literal URL path to return if reversing fails.

    Returns:
        A URL string.
    """
    candidates = []
    if namespace:
        candidates.append(f"{namespace}:{view_name}")
    candidates.append(view_name)

    for candidate in candidates:
        try:
            url = reverse(candidate)
            logger.debug("safe_reverse: resolved %s -> %s", candidate, url)
            return url
        except NoReverseMatch as exc:
            logger.debug("safe_reverse: failed to reverse %s: %s", candidate, exc)

    logger.warning(
        "safe_reverse: could not resolve %s (namespace=%s); returning fallback %s",
        view_name,
        namespace,
        fallback,
    )
    return fallback
