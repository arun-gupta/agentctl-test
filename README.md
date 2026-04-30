# agentctl-test

A simple Flask task-management API used to exercise [agentctl](https://github.com/arun-gupta/agentctl) — a CLI that spins up AI coding agents in isolated git worktrees to resolve GitHub issues.

## The app

A minimal REST API for managing tasks (in-memory, single process). Intentional bugs and missing features are tracked as GitHub issues so each one can be handed to `agentctl` for resolution.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tasks` | List all tasks, optionally filtered by `priority=low|medium|high`, sorted with `sort=created_at|priority|title` plus `order=asc|desc`, and paginated with `cursor` + `per_page` |
| POST | `/tasks` | Create a task (`priority` defaults to `medium`, optional ISO 8601 `due_date`) |
| GET | `/tasks/:id` | Get a task |
| PUT | `/tasks/:id` | Update a task |
| DELETE | `/tasks/:id` | Delete a task |
| GET | `/tasks/:id/toggle` | Toggle completion (buggy — see issue #4) |

### Response headers

Every response includes these headers regardless of status code:

| Header | Example value | Description |
|--------|---------------|-------------|
| `X-Request-ID` | `f47ac10b-58cc-4372-a567-0e02b2c3d479` | UUID v4 unique to this request. Use it to correlate client logs with server logs. |
| `X-Response-Time` | `12ms` | Server processing time in milliseconds, measured from the start of the request to the start of response serialisation. |

### Browser access

The API returns permissive CORS headers for browser-based clients:

| Header | Value |
|--------|-------|
| `Access-Control-Allow-Origin` | `*` |
| `Access-Control-Allow-Methods` | `GET, POST, PUT, PATCH, DELETE, OPTIONS` |
| `Access-Control-Allow-Headers` | `Content-Type` |

This allows cross-origin browser requests to the existing JSON and CSV endpoints, including preflighted requests that send `Content-Type: application/json`.

### Running locally

```bash
pip install -r requirements.txt
python app.py
# API available at http://localhost:5000

# Run tests
pytest tests/
```

---

## agentctl use cases

Each open GitHub issue maps to a specific `agentctl` invocation pattern. Work through them to exercise every major feature of the tool.

### Prerequisites

```bash
# Install agentctl
brew install arun-gupta/tap/agentctl   # or go install github.com/arun-gupta/agentctl@latest

# Set credentials
export ANTHROPIC_API_KEY=...
export OPENAI_API_KEY=...   # for --agent opencode / --agent codex
```

---

### 1  Basic interactive agent (default Claude)

```bash
agentctl start 1
```

Issue #1 — **Persist tasks to SQLite**: Replace the in-memory dict with SQLite so tasks survive server restarts. Good first task for the default `claude` agent with no extra flags.

---

### 2  Choose a different coding agent

```bash
agentctl start 2 --agent gemini
# or
agentctl start 2 --agent opencode
# or
agentctl start 2 --agent codex
```

Issue #2 — **Add task priority levels**: Add a `priority` field (`low` / `medium` / `high`, default `medium`) to the task model and surface it in all CRUD endpoints. Run the same issue against different agents to compare results.

---

### 3  Headless mode (no interactive terminal)

```bash
agentctl start 3 --headless
# Monitor progress
agentctl logs 3
# Mirror the session (read-only attach)
agentctl attach 3
```

Issue #3 — **Add input validation**: `POST /tasks` currently accepts a missing or blank `title` and stores `null`. The fix should return HTTP 400 with a clear error message. Good for headless because the change is small and self-contained.

---

### 4  Headless + spec review (`--sdd=plain`)

```bash
# Agent writes specs/spec.md and pauses
agentctl start 4 --headless --sdd=plain
# Review the spec, then unblock the agent
agentctl resume 4
# or with feedback
agentctl resume 4 "please also add an endpoint to bulk-toggle tasks"
```

Issue #4 — **Fix toggle endpoint**: The `/toggle` route uses `GET`, which is semantically wrong (GET must be idempotent and side-effect-free). Change it to `PATCH` and update the tests. `--sdd=plain` is a good fit because the spec checkpoint lets you verify the approach before implementation.

---

### 5  Interactive agent with structured spec (`--sdd=speckit`)

```bash
agentctl start 5 --sdd=speckit
```

Issue #5 — **Add due date support**: Tasks should have an optional `due_date` field (ISO 8601). The agent walks through speckit's multi-stage workflow (`/speckit.specify` → `/speckit.plan` → `/speckit.tasks` → `/speckit.implement`) before writing any code.

---

### 6  Headless + speckit (fully automated spec + implement)

```bash
agentctl start 6 --headless --sdd=speckit
agentctl logs 6 --lines 100
```

Issue #6 — **Add task tags/categories**: Tasks should support a list of string tags. Include filter-by-tag support on `GET /tasks`. Headless + speckit demonstrates the fully automated pipeline where you can review the spec file between stages without blocking.

---

### 7  Quiet headless batch run

```bash
agentctl start 7 --headless --quiet
agentctl status --verbose
```

Issue #7 — **Add pagination to `GET /tasks`**: Accept `?cursor=<opaque>&per_page=20` query parameters and return a paginated response with `total`, `per_page`, `next_cursor`, and `items` fields. `--quiet` suppresses output for CI/batch contexts.

---

### Cleanup after PRs merge

```bash
# Remove a single worktree
agentctl cleanup 1

# Remove all merged worktrees at once
agentctl cleanup --all

# Discard abandoned work (no PR)
agentctl discard 3
```

---

### Status overview

```bash
agentctl status
agentctl status --verbose
```
