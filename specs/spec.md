# Spec: Add GET /tasks/stats endpoint

## Problem

There is no way to get aggregate information about tasks. Callers must fetch all tasks and compute counts themselves. Issue #15 asks for a `GET /tasks/stats` endpoint that returns total, completed, incomplete counts and a breakdown by priority level.

## Approach

Add a single new route `GET /tasks/stats` in `app.py` that runs two SQL queries against the existing `tasks` table:

1. A `COUNT(*)` grouped by `completed` to get total/completed/incomplete.
2. A `COUNT(*)` grouped by `priority` to build the `by_priority` map.

All three known priority levels (`low`, `medium`, `high`) are always present in the response, defaulting to `0` if no tasks of that priority exist.

The route is defined before `GET /tasks/<int:task_id>` — though not strictly necessary (Flask won't confuse the literal path `/tasks/stats` with the `<int:…>` converter), placing it first keeps the ordering logical.

## Changes

**`app.py`** — add one new route:

```python
@app.route("/tasks/stats", methods=["GET"])
def get_task_stats():
    db = get_db()
    rows = db.execute("SELECT completed, COUNT(*) as cnt FROM tasks GROUP BY completed").fetchall()
    completed = 0
    incomplete = 0
    for row in rows:
        if row["completed"]:
            completed = row["cnt"]
        else:
            incomplete = row["cnt"]
    total = completed + incomplete

    priority_rows = db.execute(
        "SELECT priority, COUNT(*) as cnt FROM tasks GROUP BY priority"
    ).fetchall()
    by_priority = {"low": 0, "medium": 0, "high": 0}
    for row in priority_rows:
        by_priority[row["priority"]] = row["cnt"]

    return jsonify({"total": total, "completed": completed, "incomplete": incomplete, "by_priority": by_priority})
```

**`tests/test_app.py`** — add two new test functions:

- `test_stats_empty` — calls `GET /tasks/stats` with no tasks; asserts all counts are zero.
- `test_stats_counts` — creates tasks with varied priorities and completion states; toggles some; asserts each field in the response matches expected values.

No new files, no schema changes, no dependency changes.

## Test Cases

- Empty database returns `{"total": 0, "completed": 0, "incomplete": 0, "by_priority": {"low": 0, "medium": 0, "high": 0}}`.
- After creating 1 low, 2 medium, 1 high task and completing 2 of them, the response shows `total=4`, `completed=2`, `incomplete=2`, `by_priority={"low":1,"medium":2,"high":1}`.
- `by_priority` always contains all three keys even when a priority level has no tasks.
- All tasks completed — create several tasks, toggle all to completed; assert `incomplete=0` and `completed=total`.

## Risks / Open Questions

- **Route ordering**: Flask distinguishes `/tasks/stats` (literal) from `/tasks/<int:task_id>` (integer converter) by type, so order should not matter — but placing the literal route first is safer and clearer.
- **Future priorities**: If new priority levels are added, `by_priority` will only include the three hardcoded keys unless the code is updated. This is acceptable for now since `PRIORITY_LEVELS` is also a fixed set.

## Out of Scope

- Filtering stats by date range, assignee, or any other dimension.
- Pagination or streaming for large datasets.
- Caching the stats result.
