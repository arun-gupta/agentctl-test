import base64
import csv
import io
import json
import sqlite3
import time
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, g, Response

app = Flask(__name__)


@app.before_request
def _record_request_id():
    g._request_id = str(uuid.uuid4())


@app.before_request
def _record_start_time():
    g._request_start = time.monotonic()


@app.after_request
def _add_response_time_header(response):
    start = g.get("_request_start", time.monotonic())
    elapsed_ms = round((time.monotonic() - start) * 1000)
    response.headers["X-Response-Time"] = f"{elapsed_ms}ms"
    response.headers["X-Request-ID"] = g.get("_request_id", "")
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response
app.config["DATABASE"] = "tasks.db"

PRIORITY_LEVELS = {"low", "medium", "high"}
SORT_FIELDS = {"created_at", "priority", "title"}
SORT_ORDERS = {"asc", "desc"}
DEFAULT_PAGE_SIZE = 20
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
            "created_at TEXT NOT NULL DEFAULT '')"
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


def _tasks_order_by(sort, order):
    direction = order.upper()
    return f"{_tasks_sort_expression(sort)} {direction}, id ASC"


def _tasks_sort_expression(sort):
    if sort == "priority":
        return PRIORITY_SORT_SQL
    if sort == "title":
        return "LOWER(title)"
    return "created_at"


def _pagination_error(param_name):
    return jsonify({"error": f"{param_name} must be a positive integer"}), 400


def _parse_positive_int(param_name, raw_value):
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return _pagination_error(param_name), None
    if value < 1:
        return _pagination_error(param_name), None
    return None, value


def _cursor_error():
    return jsonify({"error": "cursor must be a valid pagination token"}), 400


def _query_cursor_error():
    return jsonify({"error": "cursor is not valid for the current query"}), 400


def _task_sort_value(row, sort):
    if sort == "priority":
        return {"low": 1, "medium": 2, "high": 3}[row["priority"]]
    if sort == "title":
        return row["title"].lower()
    return row["created_at"]


def _encode_tasks_cursor(sort, order, priority, row):
    payload = {
        "sort": sort,
        "order": order,
        "priority": priority,
        "value": _task_sort_value(row, sort),
        "id": row["id"],
    }
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(encoded).decode("ascii").rstrip("=")


def _decode_tasks_cursor(raw_cursor):
    if not isinstance(raw_cursor, str) or not raw_cursor:
        return _cursor_error(), None
    padded = raw_cursor + "=" * (-len(raw_cursor) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        payload = json.loads(decoded)
    except (ValueError, UnicodeDecodeError):
        return _cursor_error(), None
    if not isinstance(payload, dict):
        return _cursor_error(), None

    sort = payload.get("sort")
    order = payload.get("order")
    priority = payload.get("priority")
    value = payload.get("value")
    task_id = payload.get("id")

    if sort not in SORT_FIELDS or order not in SORT_ORDERS:
        return _cursor_error(), None
    if priority is not None and priority not in PRIORITY_LEVELS:
        return _cursor_error(), None
    if not isinstance(task_id, int) or task_id < 1:
        return _cursor_error(), None
    if sort == "priority":
        if not isinstance(value, int) or value not in {1, 2, 3}:
            return _cursor_error(), None
    elif not isinstance(value, str):
        return _cursor_error(), None

    return None, payload


def _tasks_cursor_where_clause(sort, order):
    comparator = ">" if order == "asc" else "<"
    sort_expression = _tasks_sort_expression(sort)
    return (
        f"({sort_expression} {comparator} ? "
        f"OR ({sort_expression} = ? AND id > ?))"
    )


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
    return jsonify({"status": "ok"})


@app.route("/tasks", methods=["GET"])
def list_tasks():
    priority = request.args.get("priority")
    cursor_str = request.args.get("cursor")
    per_page_str = request.args.get("per_page", str(DEFAULT_PAGE_SIZE))
    sort = request.args.get("sort", "created_at")
    order = request.args.get("order", "asc")

    error, per_page = _parse_positive_int("per_page", per_page_str)
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

    cursor = None
    if cursor_str is not None:
        error, cursor = _decode_tasks_cursor(cursor_str)
        if error:
            return error
        if (
            cursor["sort"] != sort
            or cursor["order"] != order
            or cursor["priority"] != priority
        ):
            return _query_cursor_error()

    order_by = _tasks_order_by(sort, order)
    db = get_db()
    total_params = []
    where_clauses = []

    if priority is not None:
        total_params.append(priority)
        where_clauses.append("priority = ?")

    query_params = list(total_params)
    if cursor is not None:
        where_clauses.append(_tasks_cursor_where_clause(sort, order))
        query_params.extend([cursor["value"], cursor["value"], cursor["id"]])

    total_where_sql = " WHERE priority = ?" if priority is not None else ""
    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    total = db.execute(
        f"SELECT COUNT(*) FROM tasks{total_where_sql}",
        tuple(total_params),
    ).fetchone()[0]
    rows = db.execute(
        f"SELECT * FROM tasks{where_sql} ORDER BY {order_by} LIMIT ?",
        (*query_params, per_page + 1),
    ).fetchall()

    page_rows = rows[:per_page]
    next_cursor = None
    if len(rows) > per_page and page_rows:
        next_cursor = _encode_tasks_cursor(sort, order, priority, page_rows[-1])

    return jsonify({
        "items": [_row(r) for r in page_rows],
        "total": total,
        "per_page": per_page,
        "next_cursor": next_cursor,
    })


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
    rows = get_db().execute("SELECT * FROM tasks ORDER BY id ASC").fetchall()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "title", "description", "completed", "priority", "due_date", "notes", "created_at"])
    for row in rows:
        writer.writerow([
            row["id"],
            row["title"],
            row["description"],
            str(bool(row["completed"])).lower(),
            row["priority"],
            row["due_date"] if row["due_date"] is not None else "",
            row["notes"] if row["notes"] is not None else "",
            row["created_at"],
        ])
    return Response(
        buf.getvalue(),
        status=200,
        mimetype="text/csv",
        headers={"Content-Disposition": 'attachment; filename="tasks.csv"'},
    )


@app.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
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
    if len(title) > 200:
        return jsonify({"error": "title must not exceed 200 characters"}), 400

    error, due_date = _parse_due_date(data.get("due_date"))
    if error:
        return error

    notes = data.get("notes")
    if notes is not None and not isinstance(notes, str):
        return jsonify({"error": "notes must be a string or null"}), 400

    db = get_db()
    cur = db.execute(
        "INSERT INTO tasks (title, description, completed, priority, due_date, notes, created_at) "
        "VALUES (?, ?, 0, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%S', 'now'))",
        (title, data.get("description", ""), priority, due_date, notes),
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
        if len(title_value) > 200:
            return jsonify({"error": "title must not exceed 200 characters"}), 400

    task = _row(row)

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

    db.execute(
        "UPDATE tasks SET title = ?, description = ?, completed = ?, priority = ?, due_date = ?, notes = ? WHERE id = ?",
        (
            data.get("title", task["title"]),
            data.get("description", task["description"]),
            int(data.get("completed", task["completed"])),
            data.get("priority", task["priority"]),
            due_date,
            notes,
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
