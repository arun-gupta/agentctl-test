# Spec: Add CORS support to API

## Problem

Issue #47 asks the API to return appropriate CORS headers so browser-based clients can call it successfully. Right now the Flask app returns JSON and CSV responses without any `Access-Control-*` headers, which means browsers will block cross-origin calls and preflighted requests such as `POST`, `PUT`, `PATCH`, and `DELETE` with `application/json`.

## Approach

Add CORS behavior centrally at the Flask app level rather than in each route:

1. Extend the existing global `after_request` hook in `app.py` to attach a small, consistent CORS header set to every response, including error responses and Flask-generated `OPTIONS` responses.
2. Use permissive defaults suitable for this demo API:
   - `Access-Control-Allow-Origin: *`
   - `Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS`
   - `Access-Control-Allow-Headers: Content-Type`
3. Rely on Flask's built-in `OPTIONS` handling for routes, verifying via tests that preflight requests receive the expected headers and advertise the supported methods.
4. Document the new browser access behavior in `README.md`.

This keeps the change low-risk and avoids adding per-endpoint branching or a new dependency such as `flask-cors`.

## Changes

### `app.py`

- Update the existing `@app.after_request` hook so it also sets CORS headers on every response.
- Keep the implementation centralized instead of modifying individual route handlers.
- Expected header behavior:

```python
response.headers["Access-Control-Allow-Origin"] = "*"
response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
response.headers["Access-Control-Allow-Headers"] = "Content-Type"
```

- No new routes are expected; preflight support should come from Flask's automatic `OPTIONS` handling on existing endpoints such as:
  - `OPTIONS /tasks`
  - `OPTIONS /tasks/<id>`
  - `OPTIONS /tasks/<id>/toggle`
  - `OPTIONS /tasks/completed`

### `README.md`

- Add a short note documenting that the API supports cross-origin browser access with permissive CORS headers.
- If helpful, mention the allowed methods and that JSON requests may send `Content-Type`.

## Test Cases

- `GET /health` returns `Access-Control-Allow-Origin: *` on a normal success response.
- `GET /tasks` returns the CORS headers on a JSON list response.
- `POST /tasks` returns the CORS headers on a successful JSON create response.
- `PATCH /tasks/<id>/toggle` returns the CORS headers on a mutating success response.
- `GET /tasks/export` returns the CORS headers on the CSV export response.
- Validation failures such as `POST /tasks` with a missing title still include the CORS headers.
- Not-found responses such as `GET /tasks/999` still include the CORS headers.
- `OPTIONS /tasks` succeeds and includes the CORS headers needed for browser preflight.
- `OPTIONS /tasks/<id>/toggle` succeeds and advertises that `PATCH` is allowed for that endpoint.
- The advertised allowed methods header includes the API’s supported browser-relevant verbs: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, and `OPTIONS`.
- The allowed headers response includes `Content-Type` so browser JSON requests can pass preflight.

Test files added or updated: `tests/test_app.py`

## Risks / Open Questions

- The issue text does not specify whether CORS should be open to every origin or restricted to a configured allowlist. This spec assumes permissive `*` access because the app is a small demo API and there is no existing configuration mechanism for origin allowlists.
- `Access-Control-Allow-Headers` could be expanded later if browser clients need custom headers such as `Authorization` or `X-Request-ID`. This spec only includes `Content-Type`, which is the current minimum needed for JSON requests.
- If a future requirement adds credentialed browser requests, `Access-Control-Allow-Origin: *` will not be sufficient because wildcard origins cannot be combined with credentialed CORS.

## Out of Scope

- Adding authentication, cookies, or any credentialed cross-origin flow. The issue is limited to making the existing unauthenticated API callable from browsers.
- Introducing new application behavior beyond CORS support, such as changing task CRUD semantics or response payload shapes.
