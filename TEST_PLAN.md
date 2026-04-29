# agentctl Test Plan

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Tested — issue closed, feature verified |
| ⬜ | Needs testing — issue open, not yet run |
| ❌ | Blocked — cannot run without external dependency |

---

## Coverage summary

| Feature | Status | Section |
|---------|--------|---------|
| `start` interactive (claude) | ✅ | [start — basic interactive](#start--basic-interactive) |
| `start --headless` | ✅ | [start --headless](#start---headless) |
| `start --quiet` | ⬜ | [start --quiet](#start---quiet) |
| `start --agent claude` | ✅ | [start --agent](#start---agent-name) |
| `start --agent codex` | ✅ | [start --agent](#start---agent-name) |
| `start --agent copilot` | ⬜ | [start --agent](#start---agent-name) |
| `start --agent gemini` | ⬜ | [start --agent](#start---agent-name) |
| `start --agent opencode` | ⬜ | [start --agent](#start---agent-name) |
| `start --agent openhands` | ✅ | [start --agent](#start---agent-name) |
| `start --sdd=plain` | ⬜ | [start --sdd=plain](#start---sddplain) |
| `start --sdd=speckit` | ❌ | [start --sdd=speckit](#start---sddspeckit) |
| `start --notify` | ⬜ | [start --notify](#start---notify) |
| `start <url>` | ⬜ | [start \<url\>](#start-url--full-github-url) |
| `logs` | ✅ | [logs](#logs) |
| `logs --lines N` | ⬜ | [logs](#logs) |
| `logs --no-follow` | ⬜ | [logs](#logs) |
| `attach` | ✅ | [attach](#attach) |
| `resume` (approve) | ✅ | [resume](#resume) |
| `resume "feedback"` | ⬜ | [resume](#resume) |
| `resume --headless` | ⬜ | [resume](#resume) |
| `status` | ⬜ | [status](#status) |
| `status --verbose` | ⬜ | [status](#status) |
| `cleanup <issue>` | ✅ | [cleanup](#cleanup) |
| `cleanup --all` | ⬜ | [cleanup](#cleanup) |
| `discard <issue>` | ⬜ | [discard](#discard) |
| `discard --stale` | ⬜ | [discard](#discard) |

---

## `start` — basic interactive

Run the agent in the foreground; log streams to the terminal.

```bash
agentctl start <issue>
```

| Status | Issue | Title |
|--------|-------|-------|
| ✅ | [#1](https://github.com/arun-gupta/agentctl-test/issues/1) | Persist tasks to SQLite instead of in-memory dict |
| ✅ | [#11](https://github.com/arun-gupta/agentctl-test/issues/11) | Add GET /health endpoint |

---

## `start --headless`

Run the agent in the background; output written to `agent.log`.

```bash
agentctl start <issue> --headless
```

| Status | Issue | Title |
|--------|-------|-------|
| ✅ | [#3](https://github.com/arun-gupta/agentctl-test/issues/3) | Add input validation to POST /tasks |
| ⬜ | [#6](https://github.com/arun-gupta/agentctl-test/issues/6) | Add tags/categories to tasks with filter support |

---

## `start --quiet`

Suppress log output; show only spinner (TTY) or CI heartbeat lines.

```bash
agentctl start <issue> --headless --quiet
```

| Status | Issue | Title |
|--------|-------|-------|
| ⬜ | [#7](https://github.com/arun-gupta/agentctl-test/issues/7) | Add pagination to GET /tasks |

---

## `start --agent <name>`

Use a specific coding agent. Each agent is tested independently.

```bash
agentctl start <issue> --agent <name>
```

| Status | Agent | Issue | Title |
|--------|-------|-------|-------|
| ✅ | claude (default) | [#1](https://github.com/arun-gupta/agentctl-test/issues/1) | Persist tasks to SQLite instead of in-memory dict |
| ✅ | codex | [#4](https://github.com/arun-gupta/agentctl-test/issues/4) | Fix toggle endpoint: change GET to PATCH |
| ✅ | openhands | [#12](https://github.com/arun-gupta/agentctl-test/issues/12) | Return 400 for malformed JSON |
| ⬜ | copilot | [#31](https://github.com/arun-gupta/agentctl-test/issues/31) | Add sort order to GET /tasks |
| ⬜ | gemini | [#32](https://github.com/arun-gupta/agentctl-test/issues/32) | Add PATCH /tasks/:id for partial update |
| ⬜ | opencode | [#33](https://github.com/arun-gupta/agentctl-test/issues/33) | Add overdue filter to GET /tasks |

---

## `start --sdd=plain`

Lightweight spec-review checkpoint; no external tooling required. Produces a `spec.md` and pauses for `agentctl resume`.

```bash
agentctl start <issue> --sdd=plain
```

| Status | Issue | Title |
|--------|-------|-------|
| ⬜ | [#34](https://github.com/arun-gupta/agentctl-test/issues/34) | Add optional notes field to tasks |
| ⬜ | [#25](https://github.com/arun-gupta/agentctl-test/issues/25) | Add completed filter to GET /tasks |

---

## `start --sdd=speckit`

Full spec-then-implement pipeline via Spec Kit.

```bash
agentctl start <issue> --sdd=speckit
```

| Status | Issue | Title | Notes |
|--------|-------|-------|-------|
| ✅ | [#5](https://github.com/arun-gupta/agentctl-test/issues/5) | Add optional due_date field to tasks | Interactive speckit workflow |
| ❌ | [#6](https://github.com/arun-gupta/agentctl-test/issues/6) | Add tags/categories to tasks with filter support | Blocked: speckit not installed |

> speckit is not currently installed in this repo. Install it to unblock issue [#6](https://github.com/arun-gupta/agentctl-test/issues/6).

---

## `start --notify`

Send a native desktop notification when a headless agent finishes. Also set repo-wide via `notify: true` in `.agentctl.yml` (already configured in this repo).

```bash
agentctl start <issue> --headless --notify
```

| Status | Issue | Title |
|--------|-------|-------|
| ⬜ | [#35](https://github.com/arun-gupta/agentctl-test/issues/35) | Add GET /tasks/export endpoint (CSV) |
| ⬜ | [#26](https://github.com/arun-gupta/agentctl-test/issues/26) | Add created_at timestamp to tasks |

---

## `start <url>` — full GitHub URL

Start from any directory without `cd`-ing into the repo first.

```bash
agentctl start https://github.com/arun-gupta/agentctl-test/issues/<n>
```

| Status | Issue | Title |
|--------|-------|-------|
| ⬜ | [#33](https://github.com/arun-gupta/agentctl-test/issues/33) | Add overdue filter to GET /tasks |
| ⬜ | [#29](https://github.com/arun-gupta/agentctl-test/issues/29) | Return 404 with JSON body for unknown routes |

---

## `logs`

Stream `agent.log` for a running or finished headless agent.

```bash
agentctl logs <issue>               # follow (default)
agentctl logs <issue> --lines 100   # history depth
agentctl logs <issue> --no-follow   # print and exit
```

| Status | Flag | Issue | Title |
|--------|------|-------|-------|
| ✅ | (default) | [#3](https://github.com/arun-gupta/agentctl-test/issues/3) | Add input validation to POST /tasks |
| ⬜ | `--lines N` | [#6](https://github.com/arun-gupta/agentctl-test/issues/6) | Add tags/categories to tasks with filter support |
| ⬜ | `--no-follow` | [#35](https://github.com/arun-gupta/agentctl-test/issues/35) | Add GET /tasks/export endpoint (CSV) |

---

## `attach`

Attach to a running headless agent and exit automatically when it finishes.

```bash
agentctl attach <issue>
```

| Status | Issue | Title |
|--------|-------|-------|
| ✅ | [#3](https://github.com/arun-gupta/agentctl-test/issues/3) | Add input validation to POST /tasks |
| ⬜ | [#6](https://github.com/arun-gupta/agentctl-test/issues/6) | Add tags/categories to tasks with filter support |

---

## `resume`

Approve or revise the spec after an SDD checkpoint. Requires a paused worktree with `spec.md` present.

```bash
agentctl resume <issue>                         # approve, run in foreground
agentctl resume <issue> "revision feedback"     # request spec rewrite
agentctl resume --headless <issue>              # approve, run in background
```

| Status | Variant | Issue | Title |
|--------|---------|-------|-------|
| ✅ | approve | [#5](https://github.com/arun-gupta/agentctl-test/issues/5) | Add optional due_date field to tasks |
| ⬜ | `"feedback"` | [#34](https://github.com/arun-gupta/agentctl-test/issues/34) | Add optional notes field to tasks |
| ⬜ | `--headless` | [#34](https://github.com/arun-gupta/agentctl-test/issues/34) | Add optional notes field to tasks |

---

## `status`

Show all linked worktrees and their state.

```bash
agentctl status
agentctl status --verbose
```

| Status | Flag | Issue | Title |
|--------|------|-------|-------|
| ⬜ | (default) | [#33](https://github.com/arun-gupta/agentctl-test/issues/33) | Add overdue filter to GET /tasks |
| ⬜ | `--verbose` | [#7](https://github.com/arun-gupta/agentctl-test/issues/7) | Add pagination to GET /tasks |

---

## `cleanup`

Remove a worktree after its PR is merged.

```bash
agentctl cleanup <issue>    # single issue
agentctl cleanup --all      # sweep all merged PRs
```

| Status | Variant | Issue | Title |
|--------|---------|-------|-------|
| ✅ | single | [#1](https://github.com/arun-gupta/agentctl-test/issues/1) | Persist tasks to SQLite |
| ✅ | single | [#2](https://github.com/arun-gupta/agentctl-test/issues/2) | Add task priority levels |
| ✅ | single | [#3](https://github.com/arun-gupta/agentctl-test/issues/3) | Add input validation to POST /tasks |
| ✅ | single | [#4](https://github.com/arun-gupta/agentctl-test/issues/4) | Fix toggle endpoint |
| ✅ | single | [#5](https://github.com/arun-gupta/agentctl-test/issues/5) | Add optional due_date field to tasks |
| ⬜ | `--all` | [#25](https://github.com/arun-gupta/agentctl-test/issues/25) + [#28](https://github.com/arun-gupta/agentctl-test/issues/28) + [#29](https://github.com/arun-gupta/agentctl-test/issues/29) | Run after merging a batch of PRs |

---

## `discard`

Permanently delete a worktree and branches for abandoned or intentionally dropped work.

```bash
agentctl discard <issue>    # single
agentctl discard --stale    # all worktrees with no agent and no PR
```

| Status | Variant | Issue | Title | Notes |
|--------|---------|-------|-------|-------|
| ⬜ | single | [#26](https://github.com/arun-gupta/agentctl-test/issues/26) | Add created_at timestamp to tasks | Duplicate of closed #13 — safe to start and discard |
| ⬜ | single | [#27](https://github.com/arun-gupta/agentctl-test/issues/27) | Validate title max length | Duplicate of closed #14 — safe to start and discard |
| ⬜ | `--stale` | any above | — | After discarding one, leave another without a PR to test `--stale` |
