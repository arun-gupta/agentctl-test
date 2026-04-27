import pytest
from app import app, tasks, _next_id


@pytest.fixture(autouse=True)
def clear_tasks():
    tasks.clear()
    global _next_id
    import app as _app
    _app._next_id = 1
    yield
    tasks.clear()


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


def test_get_task(client):
    client.post("/tasks", json={"title": "Hello"})
    r = client.get("/tasks/1")
    assert r.status_code == 200
    assert r.get_json()["id"] == 1


def test_get_missing_task(client):
    r = client.get("/tasks/999")
    assert r.status_code == 404


def test_update_task(client):
    client.post("/tasks", json={"title": "Original"})
    r = client.put("/tasks/1", json={"title": "Updated", "completed": True})
    assert r.status_code == 200
    assert r.get_json()["title"] == "Updated"
    assert r.get_json()["completed"] is True


def test_delete_task(client):
    client.post("/tasks", json={"title": "Temporary"})
    r = client.delete("/tasks/1")
    assert r.status_code == 200
    assert client.get("/tasks/1").status_code == 404


def test_toggle_task(client):
    client.post("/tasks", json={"title": "Toggle me"})
    r = client.get("/tasks/1/toggle")  # NOTE: uses GET — see issue #4
    assert r.status_code == 200
    assert r.get_json()["completed"] is True


# Known failures that map to open issues
def test_create_task_without_title_should_fail(client):
    # Issue #3: no validation — this currently succeeds with title=None
    r = client.post("/tasks", json={})
    # Should return 400, but currently returns 201 (bug)
    assert r.status_code == 201  # change to 400 once issue #3 is fixed
