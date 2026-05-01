# Spec: Add input sanitization to task fields

## Problem

Issue #70 asks for input sanitization on the `title` and `description` fields in both create (`POST /tasks`) and update (`PUT /tasks/:id`). Currently:

- `title` is validated as non-blank (using `title.strip()` for the check), but the *unstripped* value is inserted into the database. A title of `"  Hello  "` is stored verbatim.
- `description` has no sanitization at all — any string, including all-whitespace strings, is stored verbatim.

The fix must strip leading/trailing whitespace from both fields before storing and reject values that are blank after stripping.

## Approach

Apply sanitization centrally inside the two route handlers, keeping the same structural pattern already used for validation:

1. **`create_task`** (`POST /tasks`):
   - Strip `title` before the blank-check and before INSERT. Store the stripped value.
   - Validate and strip `description` if provided: reject if the original value was non-empty but strips to `""` (all whitespace). If not provided, default to `""` as today.

2. **`update_task`** (`PUT /tasks/:id`):
   - Strip `title_value` before the blank-check and before UPDATE. Store the stripped value.
   - Validate and strip `description` if provided: reject if the original value was non-empty but strips to `""`. If omitted, preserve the existing value.

No new helpers, routes, or dependencies are needed.

## Changes

### `app.py`

**`create_task` function** (around line 524):

```python
# After the existing title validation, add:
title = title.strip()

# Replace the raw description extraction:
description_raw = data.get("description", "")
if not isinstance(description_raw, str):
    return jsonify({"error": "description must be a string"}), 400
description = description_raw.strip()
if description_raw and not description:
    return jsonify({"error": "description must not be blank"}), 400
```

Then pass `description` (stripped) to the INSERT instead of `data.get("description", "")`.

**`update_task` function** (around line 567):

```python
# After existing title type-check, add:
title_value = title_value.strip()
if not title_value:
    return jsonify({"error": "title must not be blank"}), 400

# New description sanitization block (when "description" is in data):
if "description" in data:
    description_raw = data["description"]
    if not isinstance(description_raw, str):
        return jsonify({"error": "description must be a string"}), 400
    description_value = description_raw.strip()
    if description_raw and not description_value:
        return jsonify({"error": "description must not be blank"}), 400
else:
    description_value = task["description"]
```

Then pass `description_value` (stripped) to the UPDATE instead of `data.get("description", task["description"])`.

## Test Cases

### POST /tasks — title sanitization

- `POST /tasks` with `title: "  Buy milk  "` returns 201 and the stored title is `"Buy milk"` (leading and trailing spaces stripped).
- `POST /tasks` with `title: "\tBuy milk\t"` returns 201 and the stored title is `"Buy milk"` (tabs stripped).
- `POST /tasks` with `title: "\n  Buy milk  \n"` returns 201 and the stored title is `"Buy milk"` (newlines stripped).
- `POST /tasks` with `title: "  leading only"` returns 201 and the stored title is `"leading only"`.
- `POST /tasks` with `title: "trailing only  "` returns 201 and the stored title is `"trailing only"`.
- `POST /tasks` with `title: "  "` (spaces only) returns 400 with `"title must not be blank"`.
- `POST /tasks` with `title: "\t\n"` (tabs and newlines only) returns 400 with `"title must not be blank"`.
- `POST /tasks` with `title: "Buy  milk"` (internal double-space) returns 201 and the stored title is `"Buy  milk"` — internal whitespace is preserved, not collapsed.
- `POST /tasks` with a padded title: stripped value is returned in the response body, not the original.
- `POST /tasks` with a padded title: `GET /tasks/:id` on the created task returns the stripped title.

### POST /tasks — title length check after stripping

- `POST /tasks` with `title: "   " + "a"*200` (200 non-whitespace chars with leading spaces) returns 201 — length is checked against the stripped value, so 200 chars is accepted.
- `POST /tasks` with `title: "a"*201` returns 400 with `"title must not exceed 200 characters"` — stripped value is 201 chars.
- `POST /tasks` with `title: "  " + "a"*201 + "  "` returns 400 with `"title must not exceed 200 characters"` — stripping does not rescue an oversized core.

### POST /tasks — description sanitization

- `POST /tasks` with `description: "  Pick up 2%  "` returns 201 and the stored description is `"Pick up 2%"`.
- `POST /tasks` with `description: "\t notes \t"` returns 201 and the stored description is `"notes"` (tabs stripped).
- `POST /tasks` with `description: "   "` (spaces only) returns 400 with `"description must not be blank"`.
- `POST /tasks` with `description: "\t"` (tab only) returns 400 with `"description must not be blank"`.
- `POST /tasks` with `description: "\n"` (newline only) returns 400 with `"description must not be blank"`.
- `POST /tasks` with `description: ""` (empty string) returns 201 and the stored description is `""` — explicitly empty is accepted.
- `POST /tasks` without a `description` key returns 201 and the stored description is `""` — default is unchanged.
- `POST /tasks` with `description: "line1  line2"` (internal spaces) returns 201 and the stored description is `"line1  line2"` — internal whitespace is preserved.
- `POST /tasks` with a padded description: stripped value is returned in the response body.

### POST /tasks — description type validation

- `POST /tasks` with `description: 42` (integer) returns 400 with `"description must be a string"`.
- `POST /tasks` with `description: true` (boolean) returns 400 with `"description must be a string"`.
- `POST /tasks` with `description: ["a"]` (array) returns 400 with `"description must be a string"`.
- `POST /tasks` with `description: null` returns 400 with `"description must be a string"` — `null` is not a valid description value (unlike `notes`, which explicitly allows null).

### POST /tasks — both fields sanitized together

- `POST /tasks` with `title: "  Groceries  "` and `description: "  Needs milk  "` returns 201 with both stripped: title `"Groceries"`, description `"Needs milk"`.

### PUT /tasks/:id — title sanitization

- `PUT /tasks/:id` with `title: "  Updated  "` returns 200 and the stored title is `"Updated"`.
- `PUT /tasks/:id` with `title: "\tUpdated\t"` returns 200 and the stored title is `"Updated"` (tabs stripped).
- `PUT /tasks/:id` with `title: "  "` (spaces only) returns 400 with `"title must not be blank"`.
- `PUT /tasks/:id` with `title: "\t\n"` returns 400 with `"title must not be blank"`.
- `PUT /tasks/:id` omitting `title` preserves the existing title unchanged (no stripping applied to the persisted value).

### PUT /tasks/:id — title length check after stripping

- `PUT /tasks/:id` with `title: "   " + "a"*200` returns 200 — stripped value is 200 chars, within limit.
- `PUT /tasks/:id` with `title: "a"*201` returns 400 with `"title must not exceed 200 characters"`.

### PUT /tasks/:id — description sanitization

- `PUT /tasks/:id` with `description: "  New desc  "` returns 200 and the stored description is `"New desc"`.
- `PUT /tasks/:id` with `description: "\tnotes\n"` returns 200 and the stored description is `"notes"`.
- `PUT /tasks/:id` with `description: "   "` returns 400 with `"description must not be blank"`.
- `PUT /tasks/:id` with `description: ""` returns 200 and the stored description is `""` — explicitly clearing description to empty is accepted.
- `PUT /tasks/:id` omitting `description` preserves the existing description value unchanged.
- `PUT /tasks/:id` with `description: "inner  spaces"` returns 200 and stores `"inner  spaces"` — internal whitespace preserved.

### PUT /tasks/:id — description type validation

- `PUT /tasks/:id` with `description: 42` returns 400 with `"description must be a string"`.
- `PUT /tasks/:id` with `description: false` (boolean) returns 400 with `"description must be a string"`.
- `PUT /tasks/:id` with `description: null` returns 400 with `"description must be a string"`.

### PUT /tasks/:id — both fields sanitized together

- `PUT /tasks/:id` with `title: "  Renamed  "` and `description: "  New body  "` returns 200 with both stripped: title `"Renamed"`, description `"New body"`.

### Round-trip and list verification

- `POST /tasks` with padded title, then `GET /tasks` returns the task with the stripped title in the `items` array.
- `POST /tasks` with padded title, then `GET /tasks/:id` returns the stripped title in the response.
- `POST /tasks` with padded title and description, then `GET /tasks/export` returns stripped values in the CSV row.
- `POST /tasks` with padded title, then `PUT /tasks/:id` omitting title: subsequent `GET` still returns the stripped title from the original create (not re-padded).

Test files added or updated: `tests/test_app.py`

## Risks / Open Questions

- The existing `test_create_task` test sends `description: "2% please"` and does not assert a stored value, so it will remain unaffected. However, if any test sends a title with surrounding whitespace and asserts the exact unstripped value back, it would break — a review of the test file shows no such test exists.
- The description field currently has no type validation. Adding it could technically break a caller passing a non-string, but such a caller is already storing bad data.

## Out of Scope

- Sanitizing other fields (`notes`, `priority`, `due_date`). The issue text targets only `title` and `description`.
- Adding a maximum-length constraint to `description` (not mentioned in the issue).
- Normalizing internal whitespace (e.g., collapsing multiple spaces between words). Only leading/trailing stripping is asked for.
