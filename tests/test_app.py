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


def test_health_check(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


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
    assert data["due_date"] is None


def test_create_task_with_priority(client):
    r = client.post("/tasks", json={"title": "Urgent", "priority": "high"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["priority"] == "high"
    assert data["due_date"] is None


def test_create_task_with_invalid_priority(client):
    r = client.post("/tasks", json={"title": "Bad", "priority": "urgent"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "Priority must be one of: low, medium, high"



def test_create_task_with_due_date(client):
    r = client.post("/tasks", json={"title": "Pay bills", "due_date": "2024-05-01"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["due_date"] == "2024-05-01"


def test_create_task_with_invalid_due_date(client):
    r = client.post("/tasks", json={"title": "Bad date", "due_date": "not-a-date"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "due_date must be an ISO 8601 string"


def test_update_task_due_date(client):
    client.post("/tasks", json={"title": "Original"})
    r = client.put("/tasks/1", json={"due_date": "2024-05-02T09:00:00Z"})
    assert r.status_code == 200
    assert r.get_json()["due_date"] == "2024-05-02T09:00:00Z"


def test_update_task_clear_due_date(client):
    client.post("/tasks", json={"title": "With date", "due_date": "2024-12-31"})
    r = client.put("/tasks/1", json={"due_date": None})
    assert r.status_code == 200
    assert r.get_json()["due_date"] is None


def test_get_task(client):
    client.post("/tasks", json={"title": "Hello"})
    r = client.get("/tasks/1")
    assert r.status_code == 200
    data = r.get_json()
    assert data["id"] == 1
    assert data["priority"] == "medium"
    assert data["due_date"] is None


def test_get_missing_task(client):
    r = client.get("/tasks/999")
    assert r.status_code == 404


def test_update_task(client):
    client.post("/tasks", json={"title": "Original"})
    r = client.put("/tasks/1", json={"title": "Updated", "completed": True, "priority": "high"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["title"] == "Updated"
    assert data["completed"] is True
    assert data["priority"] == "high"
    assert data["due_date"] is None


def test_update_task_with_invalid_priority(client):
    client.post("/tasks", json={"title": "Original"})
    r = client.put("/tasks/1", json={"priority": "urgent"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "Priority must be one of: low, medium, high"


def test_update_task_title_too_long(client):
    client.post("/tasks", json={"title": "Original"})
    long_title = "a" * 201
    r = client.put("/tasks/1", json={"title": long_title})
    assert r.status_code == 400
    assert r.get_json()["error"] == "title must be at most 200 characters"



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
        {"id": 2, "title": "High", "description": "", "completed": False, "priority": "high", "due_date": None}
    ]


def test_list_tasks_with_invalid_priority_filter(client):
    r = client.get("/tasks?priority=urgent")
    assert r.status_code == 400
    assert r.get_json()["error"] == "Priority must be one of: low, medium, high"


def test_toggle_task(client):
    client.post("/tasks", json={"title": "Toggle me"})
    r = client.patch("/tasks/1/toggle")
    assert r.status_code == 200
    assert r.get_json()["completed"] is True


def test_toggle_task_get_not_allowed(client):
    client.post("/tasks", json={"title": "Toggle me"})
    r = client.get("/tasks/1/toggle")
    assert r.status_code == 405


def test_create_task_without_title_should_fail(client):
    r = client.post("/tasks", json={})
    assert r.status_code == 400
    assert r.get_json()["error"] == "title is required"


def test_create_task_blank_title_should_fail(client):
    r = client.post("/tasks", json={"title": "   "})
    assert r.status_code == 400
    assert r.get_json()["error"] == "title must not be blank"



def test_create_task_title_at_limit_succeeds(client):
    title = "a" * 200
    r = client.post("/tasks", json={"title": title})
    assert r.status_code == 201
    assert r.get_json()["title"] == title


def test_create_task_title_too_long(client):
    long_title = "a" * 201
    r = client.post("/tasks", json={"title": long_title})
    assert r.status_code == 400
    assert r.get_json()["error"] == "title must be at most 200 characters"


def test_stats_empty(client):
    r = client.get("/tasks/stats")
    assert r.status_code == 200
    assert r.get_json() == {
        "total": 0,
        "completed": 0,
        "incomplete": 0,
        "by_priority": {"low": 0, "medium": 0, "high": 0},
    }


def test_stats_counts(client):
    client.post("/tasks", json={"title": "A", "priority": "low"})
    client.post("/tasks", json={"title": "B", "priority": "medium"})
    client.post("/tasks", json={"title": "C", "priority": "medium"})
    client.post("/tasks", json={"title": "D", "priority": "high"})
    client.patch("/tasks/2/toggle")
    client.patch("/tasks/4/toggle")

    r = client.get("/tasks/stats")
    assert r.status_code == 200
    assert r.get_json() == {
        "total": 4,
        "completed": 2,
        "incomplete": 2,
        "by_priority": {"low": 1, "medium": 2, "high": 1},
    }


def test_create_task_with_invalid_json(client):
    r = client.post("/tasks", data=b"bad", content_type="application/json")
    assert r.status_code == 400
    assert r.get_json()["error"] == "request body must be valid JSON"


def test_create_task_with_empty_body_and_json_content_type(client):
    r = client.post("/tasks", data=b"", content_type="application/json")
    assert r.status_code == 400
    assert r.get_json()["error"] == "title is required"


def test_update_task_with_invalid_json(client):
    client.post("/tasks", json={"title": "Original"})
    r = client.put("/tasks/1", data=b"bad", content_type="application/json")
    assert r.status_code == 400
    assert r.get_json()["error"] == "request body must be valid JSON"


def test_update_task_with_empty_body_and_json_content_type(client):
    client.post("/tasks", json={"title": "Original"})
    r = client.put("/tasks/1", data=b"", content_type="application/json")
    assert r.status_code == 200
    assert r.get_json()["title"] == "Original"


def test_stats_all_completed(client):
    client.post("/tasks", json={"title": "A", "priority": "low"})
    client.post("/tasks", json={"title": "B", "priority": "high"})
    client.patch("/tasks/1/toggle")
    client.patch("/tasks/2/toggle")

    r = client.get("/tasks/stats")
    assert r.status_code == 200
    data = r.get_json()
    assert data["incomplete"] == 0
    assert data["completed"] == data["total"]
