"""DEBUG-only N+1 hunter.

Logs total + duplicate query counts per request so real N+1 offenders
surface as you click through the app. No dependency, no prod cost
(only wired in under DEBUG). Watch the runserver console for
``[N+1] /some/path 87 queries (72 dup)`` lines and fix the fattest.

ponytail: measurement tool, not a framework. Delete once the hot
pages are clean, or bump THRESHOLD to quiet the noise.
"""
from collections import Counter
from django.db import connection, reset_queries

THRESHOLD = 30  # only report requests heavier than this


class QueryCountMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        reset_queries()
        response = self.get_response(request)
        n = len(connection.queries)
        if n > THRESHOLD:
            # A repeated identical SQL string is the N+1 fingerprint.
            dup = sum(c - 1 for c in Counter(q["sql"] for q in connection.queries).values() if c > 1)
            print(f"[N+1] {request.path} {n} queries ({dup} dup)")
        return response
