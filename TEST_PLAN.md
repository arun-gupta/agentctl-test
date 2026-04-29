# agentctl Test Plan

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | agentctl command confirmed working |
| ⬜ | Not yet run |
| ❌ | Blocked — cannot run without external dependency |

---

## Coverage summary

| Feature | Status | Section |
|---------|--------|---------|
| `start` interactive (claude) | ✅ | [start — basic interactive](#start--basic-interactive) |
| `start <issue> <slug>` | ⬜ | [start — basic interactive](#start--basic-interactive) |
| `start --headless` | ✅ | [start --headless](#start---headless) |
| `start --quiet` | ⬜ | [start --quiet](#start---quiet) |
| `start --agent claude` | ✅ | [start --agent](#start---agent-name) |
| `start --agent codex` | ✅ | [start --agent](#start---agent-name) |
| `start --agent copilot` | ✅ | [start --agent](#start---agent-name) |
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
| `attach` | ⬜ | [attach](#attach) |
| `resume` (approve) | ✅ | [resume](#resume) |
| `resume "feedback"` | ✅ | [resume](#resume) |
| `resume --headless` | ⬜ | [resume](#resume) |
| `resume --notify` | ⬜ | [resume](#resume) |
| `resume --quiet` | ⬜ | [resume](#resume) |
| `status` | ✅ | [status](#status) |
| `status --verbose` | ✅ | [status](#status) |
| `list` (alias for status) | ⬜ | [status](#status) |
| `cleanup <issue>` | ⬜ | [cleanup](#cleanup) |
| `cleanup` (from inside worktree) | ⬜ | [cleanup](#cleanup) |
| `cleanup --all` | ✅ | [cleanup](#cleanup) |
| `discard <issue>` | ✅ | [discard](#discard) |
| `discard` (from inside worktree) | ⬜ | [discard](#discard) |
| `discard --stale` | ✅ | [discard](#discard) |
| `dev_server` in `.agentctl.yml` | ⬜ | [config](#agentctlyml-config) |
| user-level adapter | ⬜ | [config](#agentctlyml-config) |

---

## `start` — basic interactive

Run the agent in the foreground; log streams to the terminal. The optional `[slug]` overrides the auto-derived branch name.

```bash
agentctl start <issue>
agentctl start <issue> <slug>
```

| Status | Variant | Issue |
|--------|---------|-------|
| ✅ | (default) | [#1](https://github.com/arun-gupta/agentctl-test/issues/1) |
| ⬜ | (default) | [#11](https://github.com/arun-gupta/agentctl-test/issues/11) |
| ⬜ | `<slug>` | [#28](https://github.com/arun-gupta/agentctl-test/issues/28) |

---

## `start --headless`

Run the agent in the background; output written to `agent.log`.

```bash
agentctl start <issue> --headless
```

| Status | Issue |
|--------|-------|
| ✅ | [#3](https://github.com/arun-gupta/agentctl-test/issues/3) |
| ⬜ | [#35](https://github.com/arun-gupta/agentctl-test/issues/35) |

---

## `start --quiet`

Suppress log output in the foreground; show only spinner (TTY) or CI heartbeat lines. Has no effect with `--headless`.

```bash
agentctl start <issue> --quiet
```

| Status | Issue |
|--------|-------|
| ⬜ | [#7](https://github.com/arun-gupta/agentctl-test/issues/7) |

---

## `start --agent <name>`

Use a specific coding agent. Each agent is tested independently.

```bash
agentctl start <issue> --agent <name>
```

| Status | Agent | Issue |
|--------|-------|-------|
| ✅ | claude (default) | [#1](https://github.com/arun-gupta/agentctl-test/issues/1) |
| ✅ | codex | [#4](https://github.com/arun-gupta/agentctl-test/issues/4) |
| ✅ | copilot | [#31](https://github.com/arun-gupta/agentctl-test/issues/31) |
| ⬜ | gemini | [#32](https://github.com/arun-gupta/agentctl-test/issues/32) |
| ⬜ | opencode | [#33](https://github.com/arun-gupta/agentctl-test/issues/33) |
| ✅ | openhands | [#12](https://github.com/arun-gupta/agentctl-test/issues/12) |

---

## `start --sdd=plain`

Lightweight spec-review checkpoint; no external tooling required. Produces a `spec.md` and pauses for `agentctl resume`.

```bash
agentctl start <issue> --sdd=plain
```

| Status | Issue |
|--------|-------|
| ⬜ | [#34](https://github.com/arun-gupta/agentctl-test/issues/34) |
| ⬜ | [#25](https://github.com/arun-gupta/agentctl-test/issues/25) |

---

## `start --sdd=speckit`

Full spec-then-implement pipeline via Spec Kit.

```bash
agentctl start <issue> --sdd=speckit
```

| Status | Issue |
|--------|-------|
| ❌ | [#5](https://github.com/arun-gupta/agentctl-test/issues/5) |
| ❌ | [#6](https://github.com/arun-gupta/agentctl-test/issues/6) |

> speckit is not currently installed in this repo. Install it to unblock these issues.

---

## `start --notify`

Send a native desktop notification when a headless agent finishes. Also set repo-wide via `notify: true` in `.agentctl.yml` (already configured in this repo).

```bash
agentctl start <issue> --headless --notify
```

| Status | Issue |
|--------|-------|
| ⬜ | [#35](https://github.com/arun-gupta/agentctl-test/issues/35) |
| ⬜ | [#26](https://github.com/arun-gupta/agentctl-test/issues/26) |

---

## `start <url>` — full GitHub URL

Start from any directory without `cd`-ing into the repo first.

```bash
agentctl start https://github.com/arun-gupta/agentctl-test/issues/<n>
```

| Status | Issue |
|--------|-------|
| ⬜ | [#33](https://github.com/arun-gupta/agentctl-test/issues/33) |
| ⬜ | [#29](https://github.com/arun-gupta/agentctl-test/issues/29) |

---

## `logs`

Stream `agent.log` for a running or finished headless agent.

```bash
agentctl logs <issue>               # follow (default)
agentctl logs <issue> --lines 100   # history depth
agentctl logs <issue> --no-follow   # print and exit
```

| Status | Variant | Issue |
|--------|---------|-------|
| ✅ | (default) | [#3](https://github.com/arun-gupta/agentctl-test/issues/3) |
| ⬜ | `--lines N` | [#35](https://github.com/arun-gupta/agentctl-test/issues/35) |
| ⬜ | `--no-follow` | [#35](https://github.com/arun-gupta/agentctl-test/issues/35) |

---

## `attach`

Attach to a running headless agent and exit automatically when it finishes.

```bash
agentctl attach <issue>
```

| Status | Issue |
|--------|-------|
| ⬜ | [#3](https://github.com/arun-gupta/agentctl-test/issues/3) |
| ⬜ | [#35](https://github.com/arun-gupta/agentctl-test/issues/35) |

---

## `resume`

Approve or revise the spec after an SDD checkpoint. Requires a paused worktree with `spec.md` present.

```bash
agentctl resume <issue>                         # approve, run in foreground
agentctl resume <issue> "revision feedback"     # request spec rewrite
agentctl resume --headless <issue>              # approve, run in background
agentctl resume --notify <issue>                # notify on finish
agentctl resume --quiet <issue>                 # suppress output, show spinner
```

| Status | Variant | Issue |
|--------|---------|-------|
| ✅ | approve | [#5](https://github.com/arun-gupta/agentctl-test/issues/5) |
| ✅ | `"feedback"` | [#34](https://github.com/arun-gupta/agentctl-test/issues/34) |
| ⬜ | `--headless` | [#34](https://github.com/arun-gupta/agentctl-test/issues/34) |
| ⬜ | `--notify` | [#34](https://github.com/arun-gupta/agentctl-test/issues/34) |
| ⬜ | `--quiet` | [#25](https://github.com/arun-gupta/agentctl-test/issues/25) |

---

## `status`

Show all linked worktrees and their state. `list` is an alias for `status`.

```bash
agentctl status
agentctl status --verbose
agentctl list
```

| Status | Variant | Issue |
|--------|---------|-------|
| ✅ | (default) | [#33](https://github.com/arun-gupta/agentctl-test/issues/33) |
| ✅ | `--verbose` | [#7](https://github.com/arun-gupta/agentctl-test/issues/7) |
| ⬜ | `list` | [#29](https://github.com/arun-gupta/agentctl-test/issues/29) |

---

## `cleanup`

Remove a worktree after its PR is merged. Issue number is inferred from the current branch when run from inside a linked worktree.

```bash
agentctl cleanup <issue>    # explicit issue number
agentctl cleanup            # inferred from current branch (inside worktree)
agentctl cleanup --all      # sweep all merged PRs
```

| Status | Variant | Issue |
|--------|---------|-------|
| ⬜ | single | [#1](https://github.com/arun-gupta/agentctl-test/issues/1) |
| ⬜ | single | [#2](https://github.com/arun-gupta/agentctl-test/issues/2) |
| ⬜ | single | [#3](https://github.com/arun-gupta/agentctl-test/issues/3) |
| ⬜ | single | [#4](https://github.com/arun-gupta/agentctl-test/issues/4) |
| ⬜ | single | [#5](https://github.com/arun-gupta/agentctl-test/issues/5) |
| ⬜ | inferred (from inside worktree) | any of the above |
| ✅ | `--all` | [#25](https://github.com/arun-gupta/agentctl-test/issues/25) + [#28](https://github.com/arun-gupta/agentctl-test/issues/28) + [#29](https://github.com/arun-gupta/agentctl-test/issues/29) |

---

## `discard`

Permanently delete a worktree and branches for abandoned or intentionally dropped work. Issue number is inferred from the current branch when run from inside a linked worktree.

```bash
agentctl discard <issue>    # explicit issue number
agentctl discard            # inferred from current branch (inside worktree)
agentctl discard --stale    # all worktrees with no agent and no PR
```

| Status | Variant | Issue |
|--------|---------|-------|
| ✅ | single | [#6](https://github.com/arun-gupta/agentctl-test/issues/6) |
| ⬜ | inferred (from inside worktree) | [#26](https://github.com/arun-gupta/agentctl-test/issues/26) or [#27](https://github.com/arun-gupta/agentctl-test/issues/27) |
| ✅ | `--stale` | [#26](https://github.com/arun-gupta/agentctl-test/issues/26) or [#27](https://github.com/arun-gupta/agentctl-test/issues/27) |

---

## `.agentctl.yml` config

Per-repo configuration and adapter drop-in locations.

```yaml
notify: true              # already set in this repo
dev_server: "cmd {port}"  # not yet set in this repo
```

User-level adapter drop-in: `~/.config/agentctl/adapters/<name>.yml`

| Status | Feature | Notes |
|--------|---------|-------|
| ✅ | `notify: true` | Set in `.agentctl.yml`; fires on every headless run |
| ✅ | project-level adapter | openhands via `.agentctl/adapters/openhands.yml` |
| ⬜ | `dev_server` | Add a `dev_server` command to `.agentctl.yml` and verify port substitution on `start` |
| ⬜ | user-level adapter | Drop a custom adapter into `~/.config/agentctl/adapters/` and invoke it |
