# Spec: Add response time header to API

## Problem

All API responses are missing an `X-Response-Time` header that indicates how long the server took to process the request. Issue #46 asks for this header to be included on every response, with the value expressed in milliseconds (e.g. `X-Response-Time: 12ms`).

## Approach

Use Flask's `before_request` / `after_request` hooks to bracket each request:

1. In a `before_request` handler, record `time.monotonic()` in `flask.g` (e.g. `g._request_start`).
2. In an `after_request` handler, compute elapsed milliseconds and attach the header to the outgoing response object.

This approach is transparent to every existing route handler — no route-level changes are needed.

## Changes

**`app.py`**

- Add `import time` at the top.
- Add two hook functions after `app = Flask(__name__)`:

```python
@app.before_request
def _record_start_time():
    g._request_start = time.monotonic()

@app.after_request
def _add_response_time_header(response):
    elapsed_ms = round((time.monotonic() - g._request_start) * 1000)
    response.headers["X-Response-Time"] = f"{elapsed_ms}ms"
    return response
```

No other files need modification for the core feature.

## Test Cases

- Every successful response (2xx) carries an `X-Response-Time` header.
- The header value matches the pattern `\d+ms` (a non-negative integer followed by "ms").
- Error responses (4xx) also carry the header (e.g. creating a task with a missing title returns 400 and still has the header).
- The elapsed time is non-negative (sanity check).
- Multiple sequential requests each carry their own independent header (header is not cached across requests).

Test file added/updated: `tests/test_app.py` — new test class or standalone test functions covering the cases above.

## Risks / Open Questions

- **Precision**: `time.monotonic()` provides sub-millisecond resolution but `round()` reduces it to integer ms. This is consistent with common practice (e.g. Express's `x-response-time` middleware) and satisfies the issue description of "processing time in milliseconds".
- **`g._request_start` availability**: If Flask ever invokes `after_request` without a preceding `before_request` (e.g. for certain 500 error flows), `g._request_start` would be missing. Using `g.get("_request_start", time.monotonic())` as a fallback makes the hook safe.

## Out of Scope

- Sub-millisecond precision (e.g. microseconds).
- Per-endpoint timing breakdown.
- Persisting or logging response times.
