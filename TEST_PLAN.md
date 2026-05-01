# agentctl Test Plan

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | agentctl command confirmed working |
| ⬜ | Not yet run |
| ❌ | Blocked — cannot run without external dependency |
| 🟢 | GitHub issue is open |
| 🔴 | GitHub issue is closed |

---

## Coverage summary

| Feature | Status | Section |
|---------|--------|---------|
| `start` interactive (claude) | ✅ | [start — basic interactive](#start--basic-interactive) |
| `start <issue> <slug>` | ✅ | [start — basic interactive](#start--basic-interactive) |
| `start --headless` | ✅ | [start --headless](#start---headless) |
| `start --quiet` | ✅ | [start --quiet](#start---quiet) |
| `start --quiet` + Ctrl+C (detach) | ✅ | [start --quiet](#start---quiet) |
| `start --agent claude` | ✅ | [start --agent](#start---agent-name) |
| `start --agent codex` | ✅ | [start --agent](#start---agent-name) |
| `start --agent copilot` | ✅ | [start --agent](#start---agent-name) |
| `start --agent gemini` | ⬜ | [start --agent](#start---agent-name) |
| `start --agent opencode` | ⬜ | [start --agent](#start---agent-name) |
| `start --agent openhands` | ✅ | [start --agent](#start---agent-name) |
| `start --sdd=plain` | ✅ | [start --sdd=plain](#start---sddplain) |
| `start --sdd=plain --headless` | ✅ | [start --sdd=plain](#start---sddplain) |
| `start --sdd=plain --agent codex` | ✅ | [start --sdd=plain](#start---sddplain) |
| `start --sdd=speckit` | ❌ | [start --sdd=speckit](#start---sddspeckit) |
| `start --notify` | ✅ | [start --notify](#start---notify) |
| `start <url>` | ✅ | [start \<url\>](#start-url--full-github-url) |
| `start <url> --agent copilot` | ✅ | [start \<url\>](#start-url--full-github-url) |
| `start <url> --sdd=plain` | ⬜ | [start \<url\>](#start-url--full-github-url) |
| `start <issue>,<issue>,...` (batch) | ⬜ | [start — batch](#start--batch) |
| `logs` | ✅ | [logs](#logs) |
| `logs --lines N` | ✅ | [logs](#logs) |
| `logs --no-follow` | ✅ | [logs](#logs) |
| `attach` | ✅ | [attach](#attach) |
| `attach` + Ctrl+C (detach without stopping agent) | ✅ | [attach](#attach) |
| `resume` (approve) | ✅ | [resume](#resume) |
| `resume "feedback"` | ✅ | [resume](#resume) |
| `resume --headless` | ⬜ | [resume](#resume) |
| `resume --notify` | ⬜ | [resume](#resume) |
| `resume --quiet` | ⬜ | [resume](#resume) |
| `status` | ✅ | [status](#status) |
| `status --verbose` | ✅ | [status](#status) |
| `list` (alias for status) | ✅ | [status](#status) |
| `cleanup <issue>` | ✅ | [cleanup](#cleanup) |
| `cleanup` (from inside worktree) | ⬜ | [cleanup](#cleanup) |
| `cleanup --all` | ✅ | [cleanup](#cleanup) |
| `cleanup <url>` | ✅ | [cleanup](#cleanup) |
| `discard <issue>` | ✅ | [discard](#discard) |
| `discard` (from inside worktree) | ⬜ | [discard](#discard) |
| `discard --stale` | ✅ | [discard](#discard) |
| `dev start` | ❌ | [dev](#dev) |
| `dev start --quiet` | ❌ | [dev](#dev) |
| `dev_server` in `.agentctl.yml` | ⬜ | [config](#agentctlyml-config) |
| user-level adapter | ⬜ | [config](#agentctlyml-config) |

---

## `start` — basic interactive

Run the agent in the foreground; log streams to the terminal. The optional `[slug]` overrides the auto-derived branch name.

| Variant | Issue | Status |
|---------|-------|--------|
| `agentctl start 1` | 🔴 [#1](https://github.com/arun-gupta/agentctl-test/issues/1) | ✅ |
| `agentctl start 28 add-bulk-delete` | 🔴 [#28](https://github.com/arun-gupta/agentctl-test/issues/28) | ✅ |

---

## `start --headless`

Run the agent in the background; output written to `agent.log`.

| Variant | Issue | Status |
|---------|-------|--------|
| `agentctl start 3 --headless` | 🔴 [#3](https://github.com/arun-gupta/agentctl-test/issues/3) | ✅ |

---

## `start --quiet`

Suppress log output in the foreground; show only spinner (TTY) or CI heartbeat lines. Has no effect with `--headless`.

Ctrl+C in quiet mode detaches without killing the agent — it keeps running in the background and prints reconnect instructions.

| Variant | Issue | Status |
|---------|-------|--------|
| `agentctl start 7 --quiet` | 🔴 [#7](https://github.com/arun-gupta/agentctl-test/issues/7) | ✅ |
| `agentctl start 37 --quiet` then Ctrl+C (verify agent detaches, not killed) | 🔴 [#37](https://github.com/arun-gupta/agentctl-test/issues/37) | ✅ |

---

## `start --agent <name>`

Use a specific coding agent. Each agent is tested independently.

| Variant | Issue | Status |
|---------|-------|--------|
| `agentctl start 1 --agent claude` | 🔴 [#1](https://github.com/arun-gupta/agentctl-test/issues/1) | ✅ |
| `agentctl start 4 --agent codex` | 🔴 [#4](https://github.com/arun-gupta/agentctl-test/issues/4) | ✅ |
| `agentctl start 31 --agent copilot` | 🔴 [#31](https://github.com/arun-gupta/agentctl-test/issues/31) | ✅ |
| `agentctl start 32 --agent gemini` | 🟢 [#32](https://github.com/arun-gupta/agentctl-test/issues/32) | ⬜ |
| `agentctl start 33 --agent opencode` | 🟢 [#33](https://github.com/arun-gupta/agentctl-test/issues/33) | ⬜ |
| `agentctl start 12 --agent openhands` | 🔴 [#12](https://github.com/arun-gupta/agentctl-test/issues/12) | ✅ |

---

## `start --sdd=plain`

Lightweight spec-review checkpoint; no external tooling required. Produces a `spec.md` and pauses for `agentctl resume`.

| Variant | Issue | Status |
|---------|-------|--------|
| `agentctl start 34 --sdd=plain` | 🔴 [#34](https://github.com/arun-gupta/agentctl-test/issues/34) | ✅ |
| `agentctl start 46 --sdd=plain --headless` | 🔴 [#46](https://github.com/arun-gupta/agentctl-test/issues/46) | ✅ |
| `agentctl start 51 --sdd=plain --headless` | 🔴 [#51](https://github.com/arun-gupta/agentctl-test/issues/51) | ✅ |
| `agentctl start 47 --sdd=plain --agent codex` | 🔴 [#47](https://github.com/arun-gupta/agentctl-test/issues/47) | ✅ |

---

## `start --sdd=speckit`

Full spec-then-implement pipeline via Spec Kit.

| Variant | Issue | Status |
|---------|-------|--------|
| `agentctl start 6 --sdd=speckit` | 🟢 [#6](https://github.com/arun-gupta/agentctl-test/issues/6) | ❌ |

> speckit is not currently installed in this repo. Install it to unblock these issues.

---

## `start --notify`

Send a native desktop notification when a headless agent finishes. Also set repo-wide via `notify: true` in `.agentctl.yml` (already configured in this repo).

| Variant | Issue | Status |
|---------|-------|--------|
| `agentctl start 35 --headless --notify` | 🔴 [#35](https://github.com/arun-gupta/agentctl-test/issues/35) | ✅ |

---

## `start <url>` — full GitHub URL

Start from any directory without `cd`-ing into the repo first.

| Variant | Issue | Status |
|---------|-------|--------|
| `agentctl start https://github.com/arun-gupta/agentctl-test/issues/65` | 🔴 [#65](https://github.com/arun-gupta/agentctl-test/issues/65) | ✅ |
| `agentctl start https://github.com/arun-gupta/agentctl-test/issues/54 --agent copilot` | 🔴 [#54](https://github.com/arun-gupta/agentctl-test/issues/54) | ✅ |
| `agentctl start https://github.com/arun-gupta/agentctl-test/issues/70 --sdd=plain` | 🔴 [#70](https://github.com/arun-gupta/agentctl-test/issues/70) | ⬜ |

---

## `start` — batch

Start multiple agents concurrently in headless mode using a comma-separated issue list. A `[slug]` argument is not allowed in batch mode.

| Variant | Issues | Status |
|---------|--------|--------|
| `agentctl start 55,56` | 🟢 [#55](https://github.com/arun-gupta/agentctl-test/issues/55) + 🟢 [#56](https://github.com/arun-gupta/agentctl-test/issues/56) | ⬜ |

---

## `logs`

Stream `agent.log` for a running or finished headless agent.

> **Prerequisite:** run `agentctl start 35 --headless` before testing the #35 rows below.

| Variant | Issue | Status |
|---------|-------|--------|
| `agentctl logs 3` | 🔴 [#3](https://github.com/arun-gupta/agentctl-test/issues/3) | ✅ |
| `agentctl logs 35 --lines 100` | 🔴 [#35](https://github.com/arun-gupta/agentctl-test/issues/35) | ✅ |
| `agentctl logs 35 --no-follow` | 🔴 [#35](https://github.com/arun-gupta/agentctl-test/issues/35) | ✅ |

---

## `attach`

Attach to a running headless agent and exit automatically when it finishes.

> **Prerequisite:** run `agentctl start <issue> --headless` before testing this — attach requires the agent to still be running.

| Variant | Issue | Status |
|---------|-------|--------|
| `agentctl attach 46` | 🔴 [#46](https://github.com/arun-gupta/agentctl-test/issues/46) | ✅ |
| `agentctl attach <issue>` then Ctrl+C (verify agent keeps running) | 🟢 [#66](https://github.com/arun-gupta/agentctl-test/issues/66) | ✅ |

---

## `resume`

Approve or revise the spec after an SDD checkpoint. Requires a paused worktree with `spec.md` present.

| Variant | Issue | Status |
|---------|-------|--------|
| `agentctl resume 5` | 🔴 [#5](https://github.com/arun-gupta/agentctl-test/issues/5) | ✅ |
| `agentctl resume 34 "revision feedback"` | 🔴 [#34](https://github.com/arun-gupta/agentctl-test/issues/34) | ✅ |
| `agentctl resume --headless 42` | 🟢 [#42](https://github.com/arun-gupta/agentctl-test/issues/42) | ⬜ |
| `agentctl resume --notify 43` | 🟢 [#43](https://github.com/arun-gupta/agentctl-test/issues/43) | ⬜ |
| `agentctl resume --quiet 25` | 🟢 [#25](https://github.com/arun-gupta/agentctl-test/issues/25) | ⬜ |

> **Prerequisite for ⬜ rows:** run `agentctl start <issue> --sdd=plain` first to create the paused worktree, then run the resume variant against the same issue.

---

## `status`

Show all linked worktrees and their state. `list` is an alias for `status`.

| Variant | Status |
|---------|--------|
| `agentctl status` | ✅ |
| `agentctl status --verbose` | ✅ |
| `agentctl list` | ✅ |

---

## `cleanup`

Remove a worktree after its PR is merged. Issue number is inferred from the current branch when run from inside a linked worktree.

| Variant | Issue | Status |
|---------|-------|--------|
| `agentctl cleanup <issue>` | 🔴 [#1](https://github.com/arun-gupta/agentctl-test/issues/1) + 🔴 [#2](https://github.com/arun-gupta/agentctl-test/issues/2) + 🔴 [#3](https://github.com/arun-gupta/agentctl-test/issues/3) + 🔴 [#4](https://github.com/arun-gupta/agentctl-test/issues/4) + 🔴 [#5](https://github.com/arun-gupta/agentctl-test/issues/5) | ✅ |
| `agentctl cleanup` (cd into worktree first) | 🟢 [#67](https://github.com/arun-gupta/agentctl-test/issues/67) | ⬜ |
| `agentctl cleanup --all` | 🟢 [#25](https://github.com/arun-gupta/agentctl-test/issues/25) + 🔴 [#28](https://github.com/arun-gupta/agentctl-test/issues/28) + 🟢 [#29](https://github.com/arun-gupta/agentctl-test/issues/29) | ✅ |
| `agentctl cleanup https://github.com/arun-gupta/agentctl-test/issues/54` | 🔴 [#54](https://github.com/arun-gupta/agentctl-test/issues/54) | ✅ |

---

## `discard`

Permanently delete a worktree and branches for abandoned or intentionally dropped work. Issue number is inferred from the current branch when run from inside a linked worktree.

| Variant | Issue | Status |
|---------|-------|--------|
| `agentctl discard 6` | 🟢 [#6](https://github.com/arun-gupta/agentctl-test/issues/6) | ✅ |
| `agentctl discard` (cd into worktree first) | 🟢 [#26](https://github.com/arun-gupta/agentctl-test/issues/26) or 🟢 [#27](https://github.com/arun-gupta/agentctl-test/issues/27) | ⬜ |
| `agentctl discard --stale` | 🟢 [#26](https://github.com/arun-gupta/agentctl-test/issues/26) or 🟢 [#27](https://github.com/arun-gupta/agentctl-test/issues/27) | ✅ |

---

## `dev`

Start the dev server inside a linked worktree using the `dev_server` command from `.agentctl.yml`.

> **Prerequisite:** `dev_server` must be configured in `.agentctl.yml`. Not yet set in this repo — blocked until configured.

| Variant | Issue | Status |
|---------|-------|--------|
| `agentctl dev start <issue>` | — | ❌ |
| `agentctl dev start <issue> --quiet` | — | ❌ |

---

## `.agentctl.yml` config

Per-repo configuration and adapter drop-in locations.

```yaml
notify: true              # already set in this repo
dev_server: "cmd {port}"  # not yet set in this repo
```

User-level adapter drop-in: `~/.config/agentctl/adapters/<name>.yml`

| Feature | Notes | Status |
|---------|-------|--------|
| `notify: true` | Set in `.agentctl.yml`; fires on every headless run | ✅ |
| project-level adapter | openhands via `.agentctl/adapters/openhands.yml` | ✅ |
| `dev_server` | Add a `dev_server` command to `.agentctl.yml` and verify port substitution on `start` | ⬜ |
| user-level adapter | Drop a custom adapter into `~/.config/agentctl/adapters/` and invoke it | ⬜ |
