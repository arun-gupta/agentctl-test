import pytest
from app import app, get_db


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
    data = r.get_json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["per_page"] == 20
    assert data["pages"] == 0


def test_create_task(client):
    r = client.post("/tasks", json={"title": "Buy milk", "description": "2% please"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["title"] == "Buy milk"
    assert data["completed"] is False
    assert data["priority"] == "medium"
    assert data["due_date"] is None
    assert data["created_at"]


def test_create_task_with_priority(client):
    r = client.post("/tasks", json={"title": "Urgent", "priority": "high"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["priority"] == "high"
    assert data["due_date"] is None
    assert data["created_at"]


def test_create_task_with_invalid_priority(client):
    r = client.post("/tasks", json={"title": "Bad", "priority": "urgent"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "Priority must be one of: low, medium, high"



def test_create_task_with_due_date(client):
    r = client.post("/tasks", json={"title": "Pay bills", "due_date": "2024-05-01"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["due_date"] == "2024-05-01"
    assert data["created_at"]


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
    created = client.post("/tasks", json={"title": "Hello"}).get_json()
    r = client.get("/tasks/1")
    assert r.status_code == 200
    data = r.get_json()
    assert data["id"] == 1
    assert data["priority"] == "medium"
    assert data["due_date"] is None
    assert data["created_at"] == created["created_at"]


def test_get_missing_task(client):
    r = client.get("/tasks/999")
    assert r.status_code == 404


def test_update_task(client):
    created = client.post("/tasks", json={"title": "Original"}).get_json()
    r = client.put("/tasks/1", json={"title": "Updated", "completed": True, "priority": "high"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["title"] == "Updated"
    assert data["completed"] is True
    assert data["priority"] == "high"
    assert data["due_date"] is None
    assert data["created_at"] == created["created_at"]


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
    low = client.post("/tasks", json={"title": "Low", "priority": "low"}).get_json()
    high = client.post("/tasks", json={"title": "High", "priority": "high"}).get_json()
    medium = client.post("/tasks", json={"title": "Medium"}).get_json()

    r = client.get("/tasks?priority=high")

    assert r.status_code == 200
    data = r.get_json()
    assert data["items"] == [
        {
            "id": 2,
            "title": "High",
            "description": "",
            "completed": False,
            "priority": "high",
            "due_date": None,
            "notes": None,
            "created_at": high["created_at"],
        }
    ]
    assert data["total"] == 1
    assert low["created_at"]
    assert medium["created_at"]


def test_list_tasks_with_invalid_priority_filter(client):
    r = client.get("/tasks?priority=urgent")
    assert r.status_code == 400
    assert r.get_json()["error"] == "Priority must be one of: low, medium, high"


def test_list_tasks_default_sort_is_created_at_ascending(client):
    client.post("/tasks", json={"title": "First"})
    client.post("/tasks", json={"title": "Second"})
    client.post("/tasks", json={"title": "Third"})

    r = client.get("/tasks")

    assert r.status_code == 200
    assert [item["title"] for item in r.get_json()["items"]] == ["First", "Second", "Third"]


def test_list_tasks_can_sort_by_priority_desc(client):
    client.post("/tasks", json={"title": "Low", "priority": "low"})
    client.post("/tasks", json={"title": "Medium"})
    client.post("/tasks", json={"title": "High", "priority": "high"})

    r = client.get("/tasks?sort=priority&order=desc")

    assert r.status_code == 200
    assert [item["priority"] for item in r.get_json()["items"]] == ["high", "medium", "low"]


def test_list_tasks_can_sort_by_title_ascending(client):
    client.post("/tasks", json={"title": "Zulu"})
    client.post("/tasks", json={"title": "alpha"})
    client.post("/tasks", json={"title": "Bravo"})

    r = client.get("/tasks?sort=title&order=asc")

    assert r.status_code == 200
    assert [item["title"] for item in r.get_json()["items"]] == ["alpha", "Bravo", "Zulu"]


def test_list_tasks_can_sort_by_created_at_desc(client):
    client.post("/tasks", json={"title": "Oldest"})
    client.post("/tasks", json={"title": "Middle"})
    client.post("/tasks", json={"title": "Newest"})

    with app.app_context():
        db = get_db()
        db.execute("UPDATE tasks SET created_at = ? WHERE id = ?", ("2024-01-01T08:00:00", 1))
        db.execute("UPDATE tasks SET created_at = ? WHERE id = ?", ("2024-01-02T08:00:00", 2))
        db.execute("UPDATE tasks SET created_at = ? WHERE id = ?", ("2024-01-03T08:00:00", 3))
        db.commit()

    r = client.get("/tasks?sort=created_at&order=desc")

    assert r.status_code == 200
    assert [item["title"] for item in r.get_json()["items"]] == ["Newest", "Middle", "Oldest"]


def test_list_tasks_rejects_invalid_sort(client):
    r = client.get("/tasks?sort=due_date")
    assert r.status_code == 400
    assert r.get_json()["error"] == "sort must be one of: created_at, priority, title"


def test_list_tasks_rejects_invalid_order(client):
    r = client.get("/tasks?order=up")
    assert r.status_code == 400
    assert r.get_json()["error"] == "order must be one of: asc, desc"


def test_toggle_task(client):
    created = client.post("/tasks", json={"title": "Toggle me"}).get_json()
    r = client.patch("/tasks/1/toggle")
    assert r.status_code == 200
    assert r.get_json()["completed"] is True
    assert r.get_json()["created_at"] == created["created_at"]


def test_create_task_has_created_at(client):
    r = client.post("/tasks", json={"title": "Hello"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["created_at"]


def test_created_at_not_changed_on_update(client):
    created = client.post("/tasks", json={"title": "Original"}).get_json()
    r = client.put("/tasks/1", json={"title": "Updated"})
    assert r.status_code == 200
    assert r.get_json()["created_at"] == created["created_at"]


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




def test_create_task_title_too_long(client):
    long_title = "a" * 201
    r = client.post("/tasks", json={"title": long_title})
    assert r.status_code == 400
    assert r.get_json()["error"] == "title must not exceed 200 characters"


def test_create_task_title_at_max_length(client):
    max_title = "a" * 200
    r = client.post("/tasks", json={"title": max_title})
    assert r.status_code == 201
    assert r.get_json()["title"] == max_title


def test_update_task_title_too_long(client):
    client.post("/tasks", json={"title": "Original"})
    long_title = "a" * 201
    r = client.put("/tasks/1", json={"title": long_title})
    assert r.status_code == 400
    assert r.get_json()["error"] == "title must not exceed 200 characters"

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


def test_delete_completed_tasks(client):
    client.post("/tasks", json={"title": "Done"})
    client.post("/tasks", json={"title": "Not done"})
    client.patch("/tasks/1/toggle")

    r = client.delete("/tasks/completed")
    assert r.status_code == 200
    assert r.get_json() == {"deleted": 1}

    remaining = client.get("/tasks").get_json()
    assert remaining["total"] == 1
    assert remaining["items"][0]["title"] == "Not done"


def test_delete_completed_tasks_none_exist(client):
    client.post("/tasks", json={"title": "Not done"})
    r = client.delete("/tasks/completed")
    assert r.status_code == 200
    assert r.get_json() == {"deleted": 0}


def test_delete_completed_tasks_empty_db(client):
    r = client.delete("/tasks/completed")
    assert r.status_code == 200
    assert r.get_json() == {"deleted": 0}


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


# --- Pagination tests ---

def test_pagination_defaults(client):
    for i in range(5):
        client.post("/tasks", json={"title": f"Task {i}"})
    r = client.get("/tasks")
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["per_page"] == 20
    assert data["pages"] == 1
    assert len(data["items"]) == 5


def test_pagination_limits_items(client):
    for i in range(5):
        client.post("/tasks", json={"title": f"Task {i}"})
    r = client.get("/tasks?page=1&per_page=2")
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["per_page"] == 2
    assert data["pages"] == 3
    assert len(data["items"]) == 2


def test_pagination_second_page(client):
    for i in range(5):
        client.post("/tasks", json={"title": f"Task {i}"})
    r = client.get("/tasks?page=2&per_page=2")
    assert r.status_code == 200
    data = r.get_json()
    assert data["page"] == 2
    assert len(data["items"]) == 2


def test_pagination_out_of_range_returns_empty(client):
    client.post("/tasks", json={"title": "Only task"})
    r = client.get("/tasks?page=100&per_page=20")
    assert r.status_code == 200
    data = r.get_json()
    assert data["items"] == []
    assert data["total"] == 1
    assert data["page"] == 100


def test_pagination_invalid_page_returns_400(client):
    r = client.get("/tasks?page=abc")
    assert r.status_code == 400
    assert "page" in r.get_json()["error"]


def test_pagination_invalid_per_page_returns_400(client):
    r = client.get("/tasks?per_page=abc")
    assert r.status_code == 400
    assert "per_page" in r.get_json()["error"]


def test_pagination_negative_page_returns_400(client):
    r = client.get("/tasks?page=-1")
    assert r.status_code == 400
    assert "page" in r.get_json()["error"]


def test_pagination_zero_per_page_returns_400(client):
    r = client.get("/tasks?per_page=0")
    assert r.status_code == 400
    assert "per_page" in r.get_json()["error"]


def test_pagination_with_priority_filter(client):
    for _ in range(3):
        client.post("/tasks", json={"title": "high task", "priority": "high"})
    for _ in range(2):
        client.post("/tasks", json={"title": "low task", "priority": "low"})
    r = client.get("/tasks?priority=high&per_page=2")
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 3
    assert data["pages"] == 2
    assert len(data["items"]) == 2
    assert all(item["priority"] == "high" for item in data["items"])


# --- Export tests ---

def test_export_content_type(client):
    r = client.get("/tasks/export")
    assert r.status_code == 200
    assert r.content_type == "text/csv; charset=utf-8"


def test_export_content_disposition(client):
    r = client.get("/tasks/export")
    assert r.headers["Content-Disposition"] == 'attachment; filename="tasks.csv"'


def test_export_empty_returns_header_only(client):
    r = client.get("/tasks/export")
    assert r.status_code == 200
    lines = r.data.decode().splitlines()
    assert lines == ["id,title,description,completed,priority,due_date,notes,created_at"]


def test_export_includes_all_tasks(client):
    import csv, io
    client.post("/tasks", json={"title": "Buy milk", "description": "2% please", "priority": "medium"})
    client.post("/tasks", json={"title": "Urgent", "priority": "high"})
    r = client.get("/tasks/export")
    assert r.status_code == 200
    reader = csv.DictReader(io.StringIO(r.data.decode()))
    rows = list(reader)
    assert len(rows) == 2
    assert rows[0]["title"] == "Buy milk"
    assert rows[0]["description"] == "2% please"
    assert rows[0]["completed"] == "false"
    assert rows[0]["priority"] == "medium"
    assert rows[1]["title"] == "Urgent"
    assert rows[1]["priority"] == "high"


def test_export_completed_field(client):
    import csv, io
    client.post("/tasks", json={"title": "Done task"})
    client.patch("/tasks/1/toggle")
    r = client.get("/tasks/export")
    reader = csv.DictReader(io.StringIO(r.data.decode()))
    rows = list(reader)
    assert rows[0]["completed"] == "true"


def test_export_quotes_commas_and_newlines(client):
    import csv, io
    client.post("/tasks", json={"title": "A, B", "description": "line1\nline2"})
    r = client.get("/tasks/export")
    reader = csv.DictReader(io.StringIO(r.data.decode()))
    rows = list(reader)
    assert rows[0]["title"] == "A, B"
    assert rows[0]["description"] == "line1\nline2"


def test_export_due_date_field(client):
    import csv, io
    client.post("/tasks", json={"title": "Pay bills", "due_date": "2024-05-01"})
    r = client.get("/tasks/export")
    reader = csv.DictReader(io.StringIO(r.data.decode()))
    rows = list(reader)
    assert rows[0]["due_date"] == "2024-05-01"


def test_export_null_due_date_is_empty_string(client):
    import csv, io
    client.post("/tasks", json={"title": "No date"})
    r = client.get("/tasks/export")
    reader = csv.DictReader(io.StringIO(r.data.decode()))
    rows = list(reader)
    assert rows[0]["due_date"] == ""


def test_export_notes_field(client):
    import csv, io
    client.post("/tasks", json={"title": "With notes", "notes": "my note"})
    r = client.get("/tasks/export")
    reader = csv.DictReader(io.StringIO(r.data.decode()))
    rows = list(reader)
    assert rows[0]["notes"] == "my note"


def test_export_null_notes_is_empty_string(client):
    import csv, io
    client.post("/tasks", json={"title": "No notes"})
    r = client.get("/tasks/export")
    reader = csv.DictReader(io.StringIO(r.data.decode()))
    rows = list(reader)
    assert rows[0]["notes"] == ""


# --- notes field tests ---

def test_create_task_with_notes(client):
    r = client.post("/tasks", json={"title": "Task", "notes": "some notes here"})
    assert r.status_code == 201
    assert r.get_json()["notes"] == "some notes here"


def test_create_task_without_notes_defaults_to_null(client):
    r = client.post("/tasks", json={"title": "Task"})
    assert r.status_code == 201
    assert r.get_json()["notes"] is None


def test_create_task_with_explicit_null_notes(client):
    r = client.post("/tasks", json={"title": "Task", "notes": None})
    assert r.status_code == 201
    assert r.get_json()["notes"] is None


def test_create_task_notes_long_multiline(client):
    long_notes = "line\n" * 1000 + "end"
    r = client.post("/tasks", json={"title": "Task", "notes": long_notes})
    assert r.status_code == 201
    assert r.get_json()["notes"] == long_notes


def test_create_task_notes_unicode(client):
    notes = "emoji 🎉 CJK 你好 newline\n"
    r = client.post("/tasks", json={"title": "Task", "notes": notes})
    assert r.status_code == 201
    assert r.get_json()["notes"] == notes


def test_create_task_notes_integer_returns_400(client):
    r = client.post("/tasks", json={"title": "Task", "notes": 42})
    assert r.status_code == 400
    assert r.get_json()["error"] == "notes must be a string or null"


def test_create_task_notes_list_returns_400(client):
    r = client.post("/tasks", json={"title": "Task", "notes": ["a", "b"]})
    assert r.status_code == 400
    assert r.get_json()["error"] == "notes must be a string or null"


def test_get_task_includes_notes(client):
    client.post("/tasks", json={"title": "Task", "notes": "detail here"})
    r = client.get("/tasks/1")
    assert r.status_code == 200
    assert r.get_json()["notes"] == "detail here"


def test_get_task_notes_null_when_not_set(client):
    client.post("/tasks", json={"title": "Task"})
    r = client.get("/tasks/1")
    assert r.status_code == 200
    assert r.get_json()["notes"] is None


def test_list_tasks_includes_notes(client):
    client.post("/tasks", json={"title": "A", "notes": "n1"})
    client.post("/tasks", json={"title": "B"})
    r = client.get("/tasks")
    assert r.status_code == 200
    items = r.get_json()["items"]
    assert items[0]["notes"] == "n1"
    assert items[1]["notes"] is None


def test_list_tasks_filtered_includes_notes(client):
    client.post("/tasks", json={"title": "H", "priority": "high", "notes": "high note"})
    client.post("/tasks", json={"title": "L", "priority": "low"})
    r = client.get("/tasks?priority=high")
    assert r.status_code == 200
    items = r.get_json()["items"]
    assert len(items) == 1
    assert items[0]["notes"] == "high note"


def test_list_tasks_paginated_includes_notes(client):
    client.post("/tasks", json={"title": "A", "notes": "note A"})
    client.post("/tasks", json={"title": "B", "notes": "note B"})
    client.post("/tasks", json={"title": "C"})
    r = client.get("/tasks?page=1&per_page=2")
    assert r.status_code == 200
    items = r.get_json()["items"]
    assert len(items) == 2
    assert all("notes" in item for item in items)


def test_update_task_notes_to_new_value(client):
    client.post("/tasks", json={"title": "Task", "notes": "old"})
    r = client.put("/tasks/1", json={"notes": "new value"})
    assert r.status_code == 200
    assert r.get_json()["notes"] == "new value"


def test_update_task_notes_to_null_clears_it(client):
    client.post("/tasks", json={"title": "Task", "notes": "has notes"})
    r = client.put("/tasks/1", json={"notes": None})
    assert r.status_code == 200
    assert r.get_json()["notes"] is None


def test_update_task_omitting_notes_preserves_value(client):
    client.post("/tasks", json={"title": "Task", "notes": "keep me"})
    r = client.put("/tasks/1", json={"title": "Updated title"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["title"] == "Updated title"
    assert data["notes"] == "keep me"


def test_update_other_fields_preserves_notes(client):
    client.post("/tasks", json={"title": "Task", "notes": "preserved"})
    r = client.put("/tasks/1", json={"priority": "high", "completed": True})
    assert r.status_code == 200
    data = r.get_json()
    assert data["priority"] == "high"
    assert data["notes"] == "preserved"


def test_update_task_set_notes_when_previously_null(client):
    client.post("/tasks", json={"title": "Task"})
    r = client.put("/tasks/1", json={"notes": "now has notes"})
    assert r.status_code == 200
    assert r.get_json()["notes"] == "now has notes"


def test_update_task_notes_integer_returns_400(client):
    client.post("/tasks", json={"title": "Task"})
    r = client.put("/tasks/1", json={"notes": 99})
    assert r.status_code == 400
    assert r.get_json()["error"] == "notes must be a string or null"


def test_toggle_preserves_notes(client):
    client.post("/tasks", json={"title": "Task", "notes": "still here"})
    r = client.patch("/tasks/1/toggle")
    assert r.status_code == 200
    assert r.get_json()["notes"] == "still here"


# --- X-Response-Time header tests ---

import re

_RT_PATTERN = re.compile(r"^\d+ms$")


def test_response_time_header_on_success(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert _RT_PATTERN.match(r.headers.get("X-Response-Time", ""))


def test_response_time_header_on_list(client):
    r = client.get("/tasks")
    assert r.status_code == 200
    assert _RT_PATTERN.match(r.headers.get("X-Response-Time", ""))


def test_response_time_header_on_create(client):
    r = client.post("/tasks", json={"title": "Timer test"})
    assert r.status_code == 201
    assert _RT_PATTERN.match(r.headers.get("X-Response-Time", ""))


def test_response_time_header_on_error(client):
    r = client.post("/tasks", json={})
    assert r.status_code == 400
    assert _RT_PATTERN.match(r.headers.get("X-Response-Time", ""))


def test_response_time_header_on_not_found(client):
    r = client.get("/tasks/999")
    assert r.status_code == 404
    assert _RT_PATTERN.match(r.headers.get("X-Response-Time", ""))


def test_response_time_header_non_negative(client):
    r = client.get("/health")
    value = r.headers.get("X-Response-Time", "")
    assert _RT_PATTERN.match(value)
    assert int(value[:-2]) >= 0


def test_response_time_header_independent_per_request(client):
    r1 = client.get("/health")
    r2 = client.get("/health")
    assert _RT_PATTERN.match(r1.headers.get("X-Response-Time", ""))
    assert _RT_PATTERN.match(r2.headers.get("X-Response-Time", ""))
