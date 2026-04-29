# agentctl Test Plan

Maps agentctl features to issues in this repo. Issues marked **tested** are closed; **open** issues are available for future test runs.

---

## `agentctl start` — basic interactive

Run the agent in the foreground; log streams to terminal.

```bash
agentctl start <issue>
```

| Issue | Title | Status |
|-------|-------|--------|
| #1 | Persist tasks to SQLite instead of in-memory dict | tested (closed) |
| #11 | Add GET /health endpoint | tested (closed) |

---

## `agentctl start --headless`

Run the agent in the background; output written to `agent.log`.

```bash
agentctl start <issue> --headless
```

| Issue | Title | Status |
|-------|-------|--------|
| #3 | Add input validation to POST /tasks | tested (closed) |
| #6 | Add tags/categories to tasks with filter support | open |

---

## `agentctl start --quiet`

Suppress log output; show only spinner or CI heartbeat lines.

```bash
agentctl start <issue> --headless --quiet
```

| Issue | Title | Status |
|-------|-------|--------|
| #7 | Add pagination to GET /tasks | open |

---

## `agentctl start --agent <name>`

Use a non-default coding agent (codex, gemini, opencode, copilot, openhands).

```bash
agentctl start <issue> --agent <name>
```

| Issue | Title | Status | Notes |
|-------|-------|--------|-------|
| #2 | Add task priority levels (low / medium / high) | tested (closed) | `--agent gemini/opencode/codex/copilot` |
| #4 | Fix toggle endpoint: change GET to PATCH | tested (closed) | `--agent codex` |
| #12 | Return 400 for malformed JSON | tested (closed) | adapter: openhands (see `.agentctl/adapters/openhands.yml`) |

---

## `agentctl start --sdd=plain`

Lightweight spec-review checkpoint; no external tooling required.

```bash
agentctl start <issue> --sdd=plain
```

| Issue | Title | Status | Notes |
|-------|-------|--------|-------|
| #25 | Add completed filter to GET /tasks | open | good fit — small focused feature |
| #28 | Add DELETE /tasks/completed | open | good fit — new endpoint |
| #29 | Return 404 with JSON body for unknown routes | open | good fit — simple change, clear spec |

---

## `agentctl start --sdd=speckit`

Full spec-then-implement pipeline via Spec Kit. **Requires speckit to be installed.**

```bash
agentctl start <issue> --sdd=speckit
```

| Issue | Title | Status | Notes |
|-------|-------|--------|-------|
| #5 | Add optional due_date field to tasks | tested (closed) | interactive speckit workflow |
| #6 | Add tags/categories to tasks with filter support | open | headless + speckit; speckit not currently installed |

> **Note:** speckit is not installed in this repo. `--sdd=speckit` cannot be exercised until it is set up. All other `start` flags on these issues remain testable.

---

## `agentctl start --notify`

Send a native desktop notification when a headless agent finishes.

```bash
agentctl start <issue> --headless --notify
```

Also configurable repo-wide via `.agentctl.yml`:

```yaml
notify: true
```

| Issue | Title | Status | Notes |
|-------|-------|--------|-------|
| `.agentctl.yml` | `notify: true` already set | configured | fires for any headless run |
| #26 | Add created_at timestamp to tasks | open | good candidate for `--notify` test |
| #27 | Validate title max length on create and update | open | good candidate for `--notify` test |

---

## `agentctl start <url>` — full GitHub URL

Start from any directory by passing a full issue URL; agentctl locates the repo automatically.

```bash
agentctl start https://github.com/arun-gupta/agentctl-test/issues/<n>
```

| Issue | Title | Status | Notes |
|-------|-------|--------|-------|
| #25 | Add completed filter to GET /tasks | open | any open issue works |
| #28 | Add DELETE /tasks/completed | open | |

---

## `agentctl logs`

Stream `agent.log` for a running or finished headless agent.

```bash
agentctl logs <issue>
agentctl logs <issue> --lines 100
agentctl logs <issue> --no-follow
```

| Issue | Title | Status | Notes |
|-------|-------|--------|-------|
| #3 | Add input validation to POST /tasks | tested (closed) | basic `agentctl logs 3` |
| #6 | Add tags/categories to tasks with filter support | open | `agentctl logs 6 --lines 100` explicitly called out |
| #7 | Add pagination to GET /tasks | open | `--no-follow` not yet exercised |

---

## `agentctl attach`

Attach to a running headless agent; exits automatically when the agent finishes.

```bash
agentctl attach <issue>
```

| Issue | Title | Status | Notes |
|-------|-------|--------|-------|
| #3 | Add input validation to POST /tasks | tested (closed) | |
| #6 | Add tags/categories to tasks with filter support | open | |

---

## `agentctl resume`

Approve or revise the spec after an SDD checkpoint. Requires a paused worktree with `spec.md` present.

```bash
agentctl resume <issue>                        # approve
agentctl resume <issue> "revision feedback"   # request rewrite
agentctl resume --headless <issue>            # approve and run in background
```

| Issue | Title | Status | Notes |
|-------|-------|--------|-------|
| #5 | Add optional due_date field to tasks | tested (closed) | `--sdd=speckit` produces checkpoint |
| #6 | Add tags/categories to tasks with filter support | open | blocked on speckit install |
| Any `--sdd=plain` issue | — | open | `--sdd=plain` produces checkpoint without speckit |

---

## `agentctl status`

Show all linked worktrees and their state.

```bash
agentctl status
agentctl status --verbose
```

| Issue | Title | Status | Notes |
|-------|-------|--------|-------|
| #7 | Add pagination to GET /tasks | open | `--verbose` explicitly called out |
| Any running headless issue | — | — | `status` is useful alongside any headless run |

---

## `agentctl cleanup`

Remove a worktree after its PR is merged.

```bash
agentctl cleanup <issue>
agentctl cleanup --all
```

| Issue | Title | Status | Notes |
|-------|-------|--------|-------|
| All closed issues | #1–#5, #11–#15 | tested (closed) | each closed issue exercised single-issue cleanup |
| #26, #27, #28, #29 | multiple open issues | open | good batch for `--all` after merging PRs |

---

## `agentctl discard`

Permanently delete a worktree and its branches for abandoned work.

```bash
agentctl discard <issue>
agentctl discard --stale
```

| Issue | Title | Status | Notes |
|-------|-------|--------|-------|
| #26 | Add created_at timestamp (duplicate scope of #13) | open | safe to discard if #13 already covers it |
| #27 | Validate title max length (duplicate scope of #14) | open | safe to discard if #14 already covers it |
| — | `--stale` | untested | needs a worktree with no agent running and no PR |

---

## Adapter: openhands

The repo ships `.agentctl/adapters/openhands.yml`. Tests the pluggable adapter system.

```bash
agentctl start <issue> --agent openhands
```

| Issue | Title | Status | Notes |
|-------|-------|--------|-------|
| #12 | Return 400 for malformed JSON | tested (closed) | confirmed via openhands adapter |
| #25 | Add completed filter to GET /tasks | open | good next candidate |

---

## Coverage summary

| Feature | Tested | Open / untested |
|---------|--------|-----------------|
| `start` interactive | #1, #11 | — |
| `start --headless` | #3 | #6 |
| `start --quiet` | — | #7 |
| `start --agent` | #2, #4, #12 | — |
| `start --sdd=plain` | — | #25, #28, #29 |
| `start --sdd=speckit` | #5 | #6 (blocked: speckit not installed) |
| `start --notify` | `.agentctl.yml` set | #26, #27 |
| `start <url>` | — | #25, #28 |
| `logs` | #3 | #6 (`--lines`), #7 (`--no-follow`) |
| `attach` | #3 | #6 |
| `resume` (approve) | #5 | any `--sdd` issue |
| `resume` (feedback) | — | any `--sdd` issue |
| `resume --headless` | — | any `--sdd` issue |
| `status` | — | #7 (`--verbose`) |
| `cleanup` single | all closed | — |
| `cleanup --all` | — | #26–#29 batch |
| `discard` single | — | #26, #27 |
| `discard --stale` | — | needs stale worktree |
| openhands adapter | #12 | #25 |
