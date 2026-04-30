# Spec: Add request ID header to API responses

## Problem

Issue #51 asks that every API response include an `X-Request-ID` header whose value is a unique UUID (version 4) generated per request. This is useful for distributed tracing and debugging — callers can log or forward the ID to correlate server-side logs with a specific request.

The README currently documents the endpoint table but has no mention of response headers. This PR is also an opportunity to document both `X-Request-ID` and the already-shipped `X-Response-Time` header in one place.

## Approach

Mirror the `X-Response-Time` implementation already in `app.py`:

1. In a `before_request` handler, generate a UUID4 string and store it in `flask.g` (e.g. `g._request_id`).
2. In the existing `_add_response_time_header` `after_request` handler, also attach the `X-Request-ID` header from `g._request_id`.

Using `before_request` / `after_request` hooks keeps all route handlers unchanged.

## Changes

### `app.py`

- Add `import uuid` at the top.
- Add a new `before_request` hook that generates and stores the request ID:

```python
@app.before_request
def _record_request_id():
    g._request_id = str(uuid.uuid4())
```

- In `_add_response_time_header` (the existing `after_request` hook), add one line to attach the header:

```python
response.headers["X-Request-ID"] = g.get("_request_id", "")
```

### `README.md`

Add a **Response headers** subsection under "The app" documenting all standard headers present on every response:

| Header | Example value | Description |
|--------|---------------|-------------|
| `X-Request-ID` | `f47ac10b-58cc-4372-a567-0e02b2c3d479` | UUID v4 unique to this request. Use it to correlate client logs with server logs. |
| `X-Response-Time` | `12ms` | Server processing time in milliseconds, measured from the start of the request to the start of response serialisation. |

## Test Cases

**Format validation**
- Header value matches the UUID v4 regex: `[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}` (lowercase hex, correct version bit `4`, correct variant bits `8`, `9`, `a`, or `b`).
- Header value is parseable by `uuid.UUID(..., version=4)` without raising an exception.
- Header value is a non-empty string (sanity guard against the fallback path returning `""`).

**Coverage across all endpoints and HTTP methods**
- `GET /health` (200) carries the header.
- `GET /tasks` (200) carries the header.
- `POST /tasks` with valid body (201) carries the header.
- `GET /tasks/<id>` for an existing task (200) carries the header.
- `PUT /tasks/<id>` update (200) carries the header.
- `DELETE /tasks/<id>` (200) carries the header.
- `PATCH /tasks/<id>/toggle` (200) carries the header.
- `GET /tasks/stats` (200) carries the header.
- `GET /tasks/export` CSV response (200) carries the header.
- `DELETE /tasks/completed` (200) carries the header.

**Error and edge-case responses**
- `POST /tasks` with missing title (400) carries the header.
- `POST /tasks` with invalid priority (400) carries the header.
- `GET /tasks/<id>` for a non-existent task (404) carries the header.
- `GET /tasks/<id>/toggle` using wrong HTTP method `GET` (405 Method Not Allowed) carries the header.
- `GET /tasks?priority=invalid` (400) carries the header.
- `GET /tasks?sort=invalid` (400) carries the header.
- `GET /tasks?page=-1` (400) carries the header.

**Uniqueness and independence**
- Two sequential requests to the same endpoint produce different `X-Request-ID` values.
- Ten sequential requests all produce distinct `X-Request-ID` values (no collisions in a small sample).
- Two requests in the same test produce different IDs (values are not shared across request contexts).

Test file added/updated: `tests/test_app.py` — new test functions grouped under a `# --- X-Request-ID header tests ---` comment block, following the existing style used for `X-Response-Time` tests.

## Risks / Open Questions

- **`g._request_id` availability in `after_request`**: If Flask ever invokes `after_request` without a preceding `before_request` (e.g. certain 500 error flows), `g._request_id` would be absent. `g.get("_request_id", "")` provides a safe fallback; the 405 test validates that the hook still fires for Flask's own error responses.
- **UUID version**: UUID v4 (random) is the standard choice for per-request correlation IDs. Ordered alternatives (v1 timestamp, v7 Unix-time) are out of scope.
- **405 hook firing**: Flask's built-in 405 handler runs `after_request`, so the hook should fire. Tested explicitly because it is a Flask internal path, not a user route.
- **README `X-Response-Time` note**: The `X-Response-Time` header has been in production since PR #46 but was never documented. This PR adds it to the README alongside `X-Request-ID` to avoid a second documentation gap.

## Out of Scope

- Accepting a caller-supplied `X-Request-ID` header and echoing it back (correlation via header propagation).
- Logging or persisting the request ID server-side.
- Sub-millisecond or structured timing data.
