# Spec: Add optional notes field to tasks

## Problem

Tasks only have a short `description` field. Users need a freeform `notes` field for longer context, links, or checklists that should not pollute the description. Issue #34 asks for an optional `notes` field (string, default `null`) on tasks, surfaced in all CRUD endpoints.

## Approach

1. Add a `notes TEXT` column to the SQLite `tasks` table (with migration guard using `PRAGMA table_info`).
2. Include `notes` in the `_row()` helper so every response serializes it.
3. Accept `notes` in `POST /tasks` and `PUT /tasks/:id`; allow `null` to clear it. Validate that `notes`, when provided, is either a string or `null` (reject any other type with 400).
4. `GET /tasks` (list) and `GET /tasks/:id` both return `notes`.
5. No length restriction on `notes` strings.

## Changes

**`app.py`**

- `get_db()`: add `notes TEXT` to the `CREATE TABLE` statement and a migration guard:
  ```python
  if "notes" not in columns:
      db.execute("ALTER TABLE tasks ADD COLUMN notes TEXT")
  ```

- `_row()`: add `"notes": row["notes"]` to the returned dict.

- `create_task()`: read and validate `notes`, then pass it to `INSERT`.
  ```python
  notes = data.get("notes")
  if notes is not None and not isinstance(notes, str):
      return jsonify({"error": "notes must be a string or null"}), 400

  cur = db.execute(
      "INSERT INTO tasks (title, description, completed, priority, due_date, notes, created_at) "
      "VALUES (?, ?, 0, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%S', 'now'))",
      (title, data.get("description", ""), priority, due_date, notes),
  )
  ```

- `update_task()`: read and validate `notes`; preserve existing value when key absent; allow `null` to clear.
  ```python
  if "notes" in data:
      notes = data["notes"]
      if notes is not None and not isinstance(notes, str):
          return jsonify({"error": "notes must be a string or null"}), 400
  else:
      notes = task["notes"]
  ```
  Add `notes` to the `UPDATE` SQL and its parameter tuple.

**`tests/test_app.py`**

- Update `test_list_tasks_can_filter_by_priority`: add `"notes": None` to the expected item dict (exact equality check will otherwise fail once `notes` is included in list responses).
- Add all new test functions listed under Test Cases below.

## Test Cases

### Create (POST /tasks)

- Creating a task with `notes` set to a string stores and returns the value (status 201).
- Creating a task without a `notes` key returns `notes: null`.
- Creating a task with explicit `notes: null` returns `notes: null`.
- Creating a task with `notes` set to a long multiline string (e.g. 5000+ characters with newlines) stores and returns the full value unchanged — no length restriction.
- Creating a task with `notes` containing unicode characters (e.g. emoji, CJK) stores and returns them correctly.
- Creating a task with `notes` set to an integer returns 400 with `"notes must be a string or null"`.
- Creating a task with `notes` set to a list returns 400 with `"notes must be a string or null"`.

### Read (GET /tasks and GET /tasks/:id)

- `GET /tasks/:id` response includes the `notes` field with its stored value.
- `GET /tasks/:id` returns `notes: null` when none was set.
- `GET /tasks` list response includes `notes` on every item.
- `GET /tasks?priority=high` filtered list includes `notes` in each returned item.
- Paginated `GET /tasks?page=1&per_page=2` includes `notes` in items.

### Update (PUT /tasks/:id)

- Updating `notes` to a new string value stores and returns the new value.
- Updating `notes` to `null` clears the field (response has `notes: null`).
- Sending a PUT body without a `notes` key preserves the existing `notes` value.
- Updating other fields (e.g. `title`, `priority`) while omitting `notes` leaves `notes` unchanged.
- Setting `notes` on a task that was created without one (notes was null) correctly stores the new value.
- Sending `notes` as an integer in a PUT body returns 400 with `"notes must be a string or null"`.

### Toggle (PATCH /tasks/:id/toggle)

- Toggling a task that has `notes` set preserves the `notes` value in the response.

Test file updated: `tests/test_app.py`.

## Risks / Open Questions

- **Existing test with exact dict comparison**: `test_list_tasks_can_filter_by_priority` asserts full dict equality on list items. Adding `notes` to `_row()` will break it; the fix is to add `"notes": None` to the expected dict. This is the only existing test that does exact dict matching on a task response.
- **Empty string for notes**: The spec treats `""` as a valid string (distinct from `null`). If the intent is that an empty string should be coerced to `null`, validation logic would need adjustment — not done here since the issue does not mention it.
- **List vs detail payload size**: The acceptance criteria specifies `notes` in both list and detail responses. If payload size becomes a concern, `notes` could be stripped from list responses in a future change.

## Out of Scope

- Length restriction on `notes`.
- Filtering or sorting by `notes`.
- Migrating existing `description` data into `notes`.
