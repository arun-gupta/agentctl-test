from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory storage — lost on restart (see issue #1)
tasks = {}
_next_id = 1


def _next():
    global _next_id
    tid = _next_id
    _next_id += 1
    return tid


@app.route("/tasks", methods=["GET"])
def list_tasks():
    # Returns all tasks with no filtering or pagination (see issues #4, #7)
    return jsonify(list(tasks.values()))


@app.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)


@app.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json(silent=True) or {}
    # Bug: no validation — title can be None or empty (see issue #3)
    task = {
        "id": _next(),
        "title": data.get("title"),
        "description": data.get("description", ""),
        "completed": False,
    }
    tasks[task["id"]] = task
    return jsonify(task), 201


@app.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    data = request.get_json(silent=True) or {}
    task["title"] = data.get("title", task["title"])
    task["description"] = data.get("description", task["description"])
    task["completed"] = data.get("completed", task["completed"])
    return jsonify(task)


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    task = tasks.pop(task_id, None)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify({"message": "Task deleted"})


# Bug: toggle should be PATCH, not GET — causes caching issues (see issue #4)
@app.route("/tasks/<int:task_id>/toggle", methods=["GET"])
def toggle_task(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    task["completed"] = not task["completed"]
    return jsonify(task)


if __name__ == "__main__":
    app.run(debug=True)
