import base64
import csv
import io
import json
import sqlite3
import threading
import time
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, g, Response

app = Flask(__name__)

_start_time = time.monotonic()
_rate_limit_store: dict[str, list[float]] = {}
_rate_limit_lock = threading.Lock()

RATE_LIMIT_DEFAULT_REQUESTS = 100
RATE_LIMIT_DEFAULT_WINDOW = 60
LIST_PAGE_SIZE_DEFAULT = 20
LIST_PAGE_SIZE_MAX = 100


@app.before_request
def _record_request_id():
    g._request_id = str(uuid.uuid4())


@app.before_request
def _record_start_time():
    g._request_start = time.monotonic()


@app.before_request
def _enforce_rate_limit():
    if not app.config.get("RATE_LIMIT_ENABLED", True):
        return

    limit = app.config.get("RATE_LIMIT_REQUESTS", RATE_LIMIT_DEFAULT_REQUESTS)
    window = app.config.get("RATE_LIMIT_WINDOW", RATE_LIMIT_DEFAULT_WINDOW)
    client_key = request.remote_addr or "unknown"
    now = time.time()
    window_start = now - window

    with _rate_limit_lock:
        timestamps = _rate_limit_store.get(client_key, [])
        timestamps = [t for t in timestamps if t > window_start]

        if len(timestamps) >= limit:
            reset_at = int(timestamps[0] + window)
            retry_after = max(1, reset_at - int(now))
            g._rl_limit = limit
            g._rl_remaining = 0
            g._rl_reset = reset_at
            resp = jsonify({"error": "rate limit exceeded"})
            resp.status_code = 429
            resp.headers["Retry-After"] = str(retry_after)
            return resp

        timestamps.append(now)
        _rate_limit_store[client_key] = timestamps
        g._rl_limit = limit
        g._rl_remaining = limit - len(timestamps)
        g._rl_reset = int(timestamps[0] + window)


@app.after_request
def _add_response_time_header(response):
    start = g.get("_request_start", time.monotonic())
    elapsed_ms = round((time.monotonic() - start) * 1000)
    response.headers["X-Response-Time"] = f"{elapsed_ms}ms"
    response.headers["X-Request-ID"] = g.get("_request_id", "")
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    if hasattr(g, "_rl_limit"):
        response.headers["X-RateLimit-Limit"] = str(g._rl_limit)
        response.headers["X-RateLimit-Remaining"] = str(g._rl_remaining)
        response.headers["X-RateLimit-Reset"] = str(g._rl_reset)
    return response
app.config["DATABASE"] = "tasks.db"
app.config["LIST_PAGE_SIZE_DEFAULT"] = LIST_PAGE_SIZE_DEFAULT
app.config["LIST_PAGE_SIZE_MAX"] = LIST_PAGE_SIZE_MAX

PRIORITY_LEVELS = {"low", "medium", "high"}
SORT_FIELDS = {"created_at", "priority", "title"}
SORT_ORDERS = {"asc", "desc"}
ALLOWED_TASK_COLLECTION_PARAMS = frozenset({"priority", "sort", "order", "cursor", "page_size", "urgent", "color", "assignee"})
PRIORITY_SORT_SQL = (
    "CASE priority "
    "WHEN 'low' THEN 1 "
    "WHEN 'medium' THEN 2 "
    "WHEN 'high' THEN 3 "
    "END"
)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        db = g.db
        db.execute(
            "CREATE TABLE IF NOT EXISTS tasks ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "title TEXT, "
            "description TEXT NOT NULL DEFAULT '', "
            "completed INTEGER NOT NULL DEFAULT 0, "
            "priority TEXT NOT NULL DEFAULT 'medium', "
            "due_date TEXT, "
            "notes TEXT, "
            "created_at TEXT NOT NULL DEFAULT '', "
            "urgent INTEGER NOT NULL DEFAULT 0, "
            "color TEXT)"
        )
        columns = {row["name"] for row in db.execute("PRAGMA table_info(tasks)")}
        if "due_date" not in columns:
            db.execute("ALTER TABLE tasks ADD COLUMN due_date TEXT")
        if "notes" not in columns:
            db.execute("ALTER TABLE tasks ADD COLUMN notes TEXT")
        if "created_at" not in columns:
            db.execute("ALTER TABLE tasks ADD COLUMN created_at TEXT NOT NULL DEFAULT ''")
            db.execute(
                "UPDATE tasks SET created_at = strftime('%Y-%m-%dT%H:%M:%S', 'now') "
                "WHERE created_at = ''"
            )
        if "urgent" not in columns:
            db.execute("ALTER TABLE tasks ADD COLUMN urgent INTEGER NOT NULL DEFAULT 0")
        if "color" not in columns:
            db.execute("ALTER TABLE tasks ADD COLUMN color TEXT")
        if "assignee" not in columns:
            db.execute("ALTER TABLE tasks ADD COLUMN assignee TEXT")
        db.commit()
    return g.db


@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _row(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "completed": bool(row["completed"]),
        "priority": row["priority"],
        "due_date": row["due_date"],
        "notes": row["notes"],
        "created_at": row["created_at"],
        "urgent": bool(row["urgent"]),
        # Always include color for consistent API shape
        "color": row["color"],
        "assignee": row["assignee"],
    }


def _validate_priority(priority):
    if priority not in PRIORITY_LEVELS:
        return jsonify({"error": "Priority must be one of: low, medium, high"}), 400
    return None


def _validate_sort(sort):
    if sort not in SORT_FIELDS:
        return jsonify({"error": "sort must be one of: created_at, priority, title"}), 400
    return None


def _validate_order(order):
    if order not in SORT_ORDERS:
        return jsonify({"error": "order must be one of: asc, desc"}), 400
    return None


def _validate_query_params(allowed):
    unknown = [k for k in request.args if k not in allowed]
    if unknown:
        return jsonify({"error": f"unsupported query parameter: {unknown[0]}"}), 400
    return None


def _validate_color(color):
    if color is None:
        return None
    if not isinstance(color, str):
        return jsonify({"error": "color must be a hex string like #RRGGBB"}), 400
    if len(color) != 7 or not color.startswith("#"):
        return jsonify({"error": "color must be a hex string like #RRGGBB"}), 400
    try:
        int(color[1:], 16)
    except ValueError:
        return jsonify({"error": "color must be a hex string like #RRGGBB"}), 400
    return None


def _tasks_order_by(sort, order):
    direction = order.upper()
    if sort == "priority":
        return f"urgent DESC, {PRIORITY_SORT_SQL} {direction}, id ASC"
    if sort == "title":
        return f"urgent DESC, LOWER(COALESCE(title, '')) {direction}, id ASC"
    return f"urgent DESC, created_at {direction}, id {direction}"


def _priority_rank(priority):
    return {"low": 1, "medium": 2, "high": 3}[priority]


def _cursor_error(message="cursor is invalid"):
    return jsonify({"error": message}), 400


def _collection_page_size_limit():
    return int(app.config.get("LIST_PAGE_SIZE_MAX", LIST_PAGE_SIZE_MAX))


def _collection_default_page_size():
    default = int(app.config.get("LIST_PAGE_SIZE_DEFAULT", LIST_PAGE_SIZE_DEFAULT))
    max_page_size = _collection_page_size_limit()
    return min(default, max_page_size)


def _parse_page_size():
    page_size_str = request.args.get("page_size")
    if page_size_str is None:
        return None, _collection_default_page_size()

    try:
        page_size = int(page_size_str)
    except (TypeError, ValueError):
        return _cursor_error("page_size must be a positive integer"), None

    if page_size < 1:
        return _cursor_error("page_size must be a positive integer"), None

    max_page_size = _collection_page_size_limit()
    if page_size > max_page_size:
        return _cursor_error(f"page_size must not exceed {max_page_size}"), None

    return None, page_size


def _cursor_payload(sort, order, priority, urgent_filter, assignee, row):
    if sort == "priority":
        last_value = _priority_rank(row["priority"])
    elif sort == "title":
        last_value = (row["title"] or "").lower()
    else:
        last_value = row["created_at"]

    return {
        "sort": sort,
        "order": order,
        "priority": priority,
        "urgent_filter": urgent_filter,
        "assignee": assignee,
        "last_urgent": int(bool(row["urgent"])),
        "last_value": last_value,
        "last_id": row["id"],
    }


def _encode_cursor(payload):
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(raw_cursor):
    if raw_cursor is None:
        return None, None

    padding = "=" * (-len(raw_cursor) % 4)
    try:
        decoded = base64.urlsafe_b64decode(f"{raw_cursor}{padding}")
        payload = json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        return _cursor_error(), None

    required_keys = {"sort", "order", "priority", "urgent_filter", "assignee", "last_urgent", "last_value", "last_id"}
    if not isinstance(payload, dict) or set(payload) != required_keys:
        return _cursor_error(), None

    if payload["sort"] not in SORT_FIELDS or payload["order"] not in SORT_ORDERS:
        return _cursor_error(), None

    if payload["priority"] is not None and payload["priority"] not in PRIORITY_LEVELS:
        return _cursor_error(), None

    if payload["urgent_filter"] is not None and not isinstance(payload["urgent_filter"], bool):
        return _cursor_error(), None

    if payload["assignee"] is not None and not isinstance(payload["assignee"], str):
        return _cursor_error(), None

    if not isinstance(payload["last_urgent"], int) or payload["last_urgent"] not in (0, 1):
        return _cursor_error(), None

    if not isinstance(payload["last_id"], int) or payload["last_id"] < 1:
        return _cursor_error(), None

    expected_type = int if payload["sort"] == "priority" else str
    if not isinstance(payload["last_value"], expected_type):
        return _cursor_error(), None

    return None, payload


def _cursor_clause(sort, order, cursor_payload):
    if cursor_payload is None:
        return "", []

    last_urgent = cursor_payload["last_urgent"]

    if sort == "priority":
        sort_sql = PRIORITY_SORT_SQL
        id_comparator = ">"
    elif sort == "title":
        sort_sql = "LOWER(COALESCE(title, ''))"
        id_comparator = ">"
    else:
        sort_sql = "created_at"
        id_comparator = ">" if order == "asc" else "<"

    value_comparator = ">" if order == "asc" else "<"
    secondary = (
        f"({sort_sql} {value_comparator} ? OR ({sort_sql} = ? AND id {id_comparator} ?))"
    )
    secondary_params = [
        cursor_payload["last_value"],
        cursor_payload["last_value"],
        cursor_payload["last_id"],
    ]
    # urgent is always DESC, so rows "after" last_urgent are: urgent < last_urgent
    # OR same urgency and passes the secondary sort condition
    return (
        f"(urgent < ? OR (urgent = ? AND {secondary}))",
        [last_urgent, last_urgent, *secondary_params],
    )


def _fetch_task_collection(priority, urgent_filter, color, assignee, sort, order, page_size, raw_cursor):
    cursor_error, cursor_payload = _decode_cursor(raw_cursor)
    if cursor_error:
        return cursor_error, None

    if cursor_payload is not None:
        if (
            cursor_payload["sort"] != sort
            or cursor_payload["order"] != order
            or cursor_payload["priority"] != priority
            or cursor_payload["urgent_filter"] != urgent_filter
            or cursor_payload["assignee"] != assignee
        ):
            return _cursor_error("cursor does not match the current query"), None

    db = get_db()
    where_parts = []
    where_params = []

    if priority is not None:
        where_parts.append("priority = ?")
        where_params.append(priority)

    if urgent_filter is not None:
        where_parts.append("urgent = ?")
        where_params.append(int(urgent_filter))
    if color is not None:
        where_parts.append("color = ?")
        where_params.append(color)
    if assignee is not None:
        where_parts.append("assignee = ?")
        where_params.append(assignee)

    count_where = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
    total = db.execute(
        f"SELECT COUNT(*) FROM tasks{count_where}",
        where_params,
    ).fetchone()[0]

    cursor_clause, cursor_params = _cursor_clause(sort, order, cursor_payload)
    if cursor_clause:
        where_parts.append(cursor_clause)

    query_where = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
    rows = db.execute(
        f"SELECT * FROM tasks{query_where} ORDER BY {_tasks_order_by(sort, order)} LIMIT ?",
        [*where_params, *cursor_params, page_size + 1],
    ).fetchall()

    has_more = len(rows) > page_size
    items = rows[:page_size]
    next_cursor = _encode_cursor(_cursor_payload(sort, order, priority, urgent_filter, assignee, items[-1])) if has_more else None

    return None, {
        "items": items,
        "total": total,
        "page_size": page_size,
        "next_cursor": next_cursor,
    }


def _due_date_error():
    return jsonify({"error": "due_date must be an ISO 8601 string"}), 400


def _parse_due_date(raw):
    if raw is None:
        return None, None
    if not isinstance(raw, str):
        return _due_date_error(), None
    value = raw.strip()
    if not value:
        return _due_date_error(), None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return _due_date_error(), None
    return None, value


@app.route("/health", methods=["GET"])
def health_check():
    error = _validate_query_params(frozenset())
    if error:
        return error
    return jsonify({"status": "ok", "uptime_seconds": int(time.monotonic() - _start_time)})


@app.route("/tasks", methods=["GET"])
def list_tasks():
    error = _validate_query_params(ALLOWED_TASK_COLLECTION_PARAMS)
    if error:
        return error
    priority = request.args.get("priority")
    sort = request.args.get("sort", "created_at")
    order = request.args.get("order", "asc")
    raw_cursor = request.args.get("cursor")
    color = request.args.get("color")
    assignee = request.args.get("assignee")

    urgent_filter = None
    if "urgent" in request.args:
        urgent_str = request.args.get("urgent")
        if urgent_str == "true":
            urgent_filter = True
        elif urgent_str == "false":
            urgent_filter = False
        else:
            return jsonify({"error": "urgent must be true or false"}), 400

    error, page_size = _parse_page_size()
    if error:
        return error

    error = _validate_sort(sort)
    if error:
        return error

    error = _validate_order(order)
    if error:
        return error

    if priority is not None:
        error = _validate_priority(priority)
        if error:
            return error

    error, page = _fetch_task_collection(priority, urgent_filter, color, assignee, sort, order, page_size, raw_cursor)
    if error:
        return error

    return jsonify({
        "items": [_row(r) for r in page["items"]],
        "total": page["total"],
        "page_size": page["page_size"],
        "next_cursor": page["next_cursor"],
    })


@app.route("/tasks/stats", methods=["GET"])
def get_task_stats():
    error = _validate_query_params(frozenset())
    if error:
        return error
    db = get_db()
    rows = db.execute("SELECT completed, COUNT(*) as cnt FROM tasks GROUP BY completed").fetchall()
    completed = 0
    incomplete = 0
    for row in rows:
        if row["completed"]:
            completed = row["cnt"]
        else:
            incomplete = row["cnt"]

    priority_rows = db.execute(
        "SELECT priority, COUNT(*) as cnt FROM tasks GROUP BY priority"
    ).fetchall()
    by_priority = {"low": 0, "medium": 0, "high": 0}
    for row in priority_rows:
        by_priority[row["priority"]] = row["cnt"]

    return jsonify({
        "total": completed + incomplete,
        "completed": completed,
        "incomplete": incomplete,
        "by_priority": by_priority,
    })


@app.route("/tasks/export", methods=["GET"])
def export_tasks():
    error = _validate_query_params(ALLOWED_TASK_COLLECTION_PARAMS)
    if error:
        return error
    priority = request.args.get("priority")
    sort = request.args.get("sort", "created_at")
    order = request.args.get("order", "asc")
    raw_cursor = request.args.get("cursor")
    color = request.args.get("color")
    assignee = request.args.get("assignee")

    urgent_filter = None
    if "urgent" in request.args:
        urgent_str = request.args.get("urgent")
        if urgent_str == "true":
            urgent_filter = True
        elif urgent_str == "false":
            urgent_filter = False
        else:
            return jsonify({"error": "urgent must be true or false"}), 400

    error, page_size = _parse_page_size()
    if error:
        return error

    error = _validate_sort(sort)
    if error:
        return error

    error = _validate_order(order)
    if error:
        return error

    if priority is not None:
        error = _validate_priority(priority)
        if error:
            return error

    error, page = _fetch_task_collection(priority, urgent_filter, color, assignee, sort, order, page_size, raw_cursor)
    if error:
        return error

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "title", "description", "completed", "priority", "due_date", "notes", "created_at", "urgent", "assignee"])
    for row in page["items"]:
        writer.writerow([
            row["id"],
            row["title"],
            row["description"],
            str(bool(row["completed"])).lower(),
            row["priority"],
            row["due_date"] if row["due_date"] is not None else "",
            row["notes"] if row["notes"] is not None else "",
            row["created_at"],
            str(bool(row["urgent"])).lower(),
            row["assignee"] if row["assignee"] is not None else "",
        ])
    return Response(
        buf.getvalue(),
        status=200,
        mimetype="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="tasks.csv"',
            "X-Page-Size": str(page["page_size"]),
            "X-Total-Count": str(page["total"]),
            "X-Next-Cursor": page["next_cursor"] or "",
        },
    )


@app.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    error = _validate_query_params(frozenset())
    if error:
        return error
    row = get_db().execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(_row(row))


@app.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json(silent=True)
    if data is None and request.is_json and request.get_data():
        return jsonify({"error": "request body must be valid JSON"}), 400
    data = data or {}
    priority = data.get("priority", "medium")
    error = _validate_priority(priority)
    if error:
        return error

    title = data.get("title")
    if title is None:
        return jsonify({"error": "title is required"}), 400
    if not isinstance(title, str) or not title.strip():
        return jsonify({"error": "title must not be blank"}), 400
    title = title.strip()
    if len(title) > 200:
        return jsonify({"error": "title must not exceed 200 characters"}), 400

    description_raw = data.get("description", "")
    if not isinstance(description_raw, str):
        return jsonify({"error": "description must be a string"}), 400
    description = description_raw.strip()
    if description_raw and not description:
        return jsonify({"error": "description must not be blank"}), 400

    error, due_date = _parse_due_date(data.get("due_date"))
    if error:
        return error

    notes = data.get("notes")
    if notes is not None and not isinstance(notes, str):
        return jsonify({"error": "notes must be a string or null"}), 400

    urgent = data.get("urgent", False)
    if not isinstance(urgent, bool):
        return jsonify({"error": "urgent must be a boolean"}), 400

    color = data.get("color")
    err = _validate_color(color)
    if err:
        return err

    assignee = data.get("assignee")
    if assignee is not None and not isinstance(assignee, str):
        return jsonify({"error": "assignee must be a string or null"}), 400

    db = get_db()
    cur = db.execute(
        "INSERT INTO tasks (title, description, completed, priority, due_date, notes, created_at, urgent, color, assignee) "
        "VALUES (?, ?, 0, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%S', 'now'), ?, ?, ?)",
        (title, description, priority, due_date, notes, int(urgent), color, assignee),
    )
    db.commit()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(_row(row)), 201


@app.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    db = get_db()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        return jsonify({"error": "Task not found"}), 404
    data = request.get_json(silent=True)
    if data is None and request.is_json and request.get_data():
        return jsonify({"error": "request body must be valid JSON"}), 400
    data = data or {}

    if "priority" in data:
        error = _validate_priority(data["priority"])
        if error:
            return error

    if "title" in data:
        title_value = data["title"]
        if not isinstance(title_value, str) or not title_value.strip():
            return jsonify({"error": "title must not be blank"}), 400
        title_value = title_value.strip()
        if len(title_value) > 200:
            return jsonify({"error": "title must not exceed 200 characters"}), 400
        data = {**data, "title": title_value}

    task = _row(row)

    if "description" in data:
        description_raw = data["description"]
        if not isinstance(description_raw, str):
            return jsonify({"error": "description must be a string"}), 400
        description_value = description_raw.strip()
        if description_raw and not description_value:
            return jsonify({"error": "description must not be blank"}), 400
        data = {**data, "description": description_value}

    due_date = task["due_date"]
    if "due_date" in data:
        error, parsed_due_date = _parse_due_date(data["due_date"])
        if error:
            return error
        due_date = parsed_due_date

    if "notes" in data:
        notes = data["notes"]
        if notes is not None and not isinstance(notes, str):
            return jsonify({"error": "notes must be a string or null"}), 400
    else:
        notes = task["notes"]

    if "urgent" in data:
        urgent = data["urgent"]
        if not isinstance(urgent, bool):
            return jsonify({"error": "urgent must be a boolean"}), 400
    else:
        urgent = task["urgent"]
    if "color" in data:
        color = data["color"]
        err = _validate_color(color)
        if err:
            return err
    else:
        color = task.get("color")

    if "assignee" in data:
        assignee = data["assignee"]
        if assignee is not None and not isinstance(assignee, str):
            return jsonify({"error": "assignee must be a string or null"}), 400
    else:
        assignee = task.get("assignee")

    db.execute(
        "UPDATE tasks SET title = ?, description = ?, completed = ?, priority = ?, due_date = ?, notes = ?, urgent = ?, color = ?, assignee = ? WHERE id = ?",
        (
            data.get("title", task["title"]),
            data.get("description", task["description"]),
            int(data.get("completed", task["completed"])),
            data.get("priority", task["priority"]),
            due_date,
            notes,
            int(urgent),
            color,
            assignee,
            task_id,
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return jsonify(_row(row))


@app.route("/tasks/completed", methods=["DELETE"])
def delete_completed_tasks():
    db = get_db()
    cur = db.execute("DELETE FROM tasks WHERE completed = 1")
    db.commit()
    return jsonify({"deleted": cur.rowcount})


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    db = get_db()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        return jsonify({"error": "Task not found"}), 404
    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    return jsonify({"message": "Task deleted"})


# Toggle mutates server state, so it must not be exposed as GET.
@app.route("/tasks/<int:task_id>/toggle", methods=["PATCH"])
def toggle_task(task_id):
    db = get_db()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        return jsonify({"error": "Task not found"}), 404
    new_completed = not bool(row["completed"])
    db.execute(
        "UPDATE tasks SET completed = ? WHERE id = ?", (int(new_completed), task_id)
    )
    db.commit()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return jsonify(_row(row))


if __name__ == "__main__":
    app.run(debug=True)
