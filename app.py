import sqlite3
from flask import Flask, request, jsonify, g

app = Flask(__name__)
app.config["DATABASE"] = "tasks.db"

PRIORITY_LEVELS = {"low", "medium", "high"}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute(
            "CREATE TABLE IF NOT EXISTS tasks ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "title TEXT, "
            "description TEXT NOT NULL DEFAULT '', "
            "completed INTEGER NOT NULL DEFAULT 0, "
            "priority TEXT NOT NULL DEFAULT 'medium')"
        )
        g.db.commit()
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
    }


def _validate_priority(priority):
    if priority not in PRIORITY_LEVELS:
        return jsonify({"error": "Priority must be one of: low, medium, high"}), 400
    return None


@app.route("/tasks", methods=["GET"])
def list_tasks():
    priority = request.args.get("priority")

    if priority is not None:
        error = _validate_priority(priority)
        if error:
            return error
        rows = get_db().execute(
            "SELECT * FROM tasks WHERE priority = ?", (priority,)
        ).fetchall()
    else:
        # Returns all tasks with no pagination (see issue #7)
        rows = get_db().execute("SELECT * FROM tasks").fetchall()

    return jsonify([_row(r) for r in rows])


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

    db = get_db()
    cur = db.execute(
        "INSERT INTO tasks (title, description, completed, priority) VALUES (?, ?, 0, ?)",
        (title, data.get("description", ""), priority),
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

    task = _row(row)
    db.execute(
        "UPDATE tasks SET title = ?, description = ?, completed = ?, priority = ? WHERE id = ?",
        (
            data.get("title", task["title"]),
            data.get("description", task["description"]),
            int(data.get("completed", task["completed"])),
            data.get("priority", task["priority"]),
            task_id,
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return jsonify(_row(row))


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
