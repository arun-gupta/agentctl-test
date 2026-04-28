import pytest
from app import app


@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    app.config["DATABASE"] = str(tmp_path / "test.db")


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_list_empty(client):
    r = client.get("/tasks")
    assert r.status_code == 200
    assert r.get_json() == []


def test_create_task(client):
    r = client.post("/tasks", json={"title": "Buy milk", "description": "2% please"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["title"] == "Buy milk"
    assert data["completed"] is False
    assert data["priority"] == "medium"


def test_create_task_with_priority(client):
    r = client.post("/tasks", json={"title": "Urgent", "priority": "high"})
    assert r.status_code == 201
    assert r.get_json()["priority"] == "high"


def test_create_task_with_invalid_priority(client):
    r = client.post("/tasks", json={"title": "Bad", "priority": "urgent"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "Priority must be one of: low, medium, high"


def test_get_task(client):
    client.post("/tasks", json={"title": "Hello"})
    r = client.get("/tasks/1")
    assert r.status_code == 200
    assert r.get_json()["id"] == 1
    assert r.get_json()["priority"] == "medium"


def test_get_missing_task(client):
    r = client.get("/tasks/999")
    assert r.status_code == 404


def test_update_task(client):
    client.post("/tasks", json={"title": "Original"})
    r = client.put("/tasks/1", json={"title": "Updated", "completed": True, "priority": "high"})
    assert r.status_code == 200
    assert r.get_json()["title"] == "Updated"
    assert r.get_json()["completed"] is True
    assert r.get_json()["priority"] == "high"


def test_update_task_with_invalid_priority(client):
    client.post("/tasks", json={"title": "Original"})
    r = client.put("/tasks/1", json={"priority": "urgent"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "Priority must be one of: low, medium, high"


def test_delete_task(client):
    client.post("/tasks", json={"title": "Temporary"})
    r = client.delete("/tasks/1")
    assert r.status_code == 200
    assert client.get("/tasks/1").status_code == 404


def test_list_tasks_can_filter_by_priority(client):
    client.post("/tasks", json={"title": "Low", "priority": "low"})
    client.post("/tasks", json={"title": "High", "priority": "high"})
    client.post("/tasks", json={"title": "Medium"})

    r = client.get("/tasks?priority=high")

    assert r.status_code == 200
    assert r.get_json() == [
        {"id": 2, "title": "High", "description": "", "completed": False, "priority": "high"}
    ]


def test_list_tasks_with_invalid_priority_filter(client):
    r = client.get("/tasks?priority=urgent")
    assert r.status_code == 400
    assert r.get_json()["error"] == "Priority must be one of: low, medium, high"


def test_toggle_task(client):
    client.post("/tasks", json={"title": "Toggle me"})
    r = client.get("/tasks/1/toggle")  # NOTE: uses GET — see issue #4
    assert r.status_code == 200
    assert r.get_json()["completed"] is True


def test_create_task_without_title_should_fail(client):
    r = client.post("/tasks", json={})
    assert r.status_code == 400
    assert r.get_json()["error"] == "title is required"


def test_create_task_blank_title_should_fail(client):
    r = client.post("/tasks", json={"title": "   "})
    assert r.status_code == 400
    assert r.get_json()["error"] == "title must not be blank"
