import pytest
from app import app, get_db, _rate_limit_store


@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    app.config["DATABASE"] = str(tmp_path / "test.db")
    app.config["RATE_LIMIT_ENABLED"] = False
    app.config["LIST_PAGE_SIZE_DEFAULT"] = 20
    app.config["LIST_PAGE_SIZE_MAX"] = 100
    _rate_limit_store.clear()


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health_check(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"
    assert isinstance(data["uptime_seconds"], int)
    assert data["uptime_seconds"] >= 0


def test_health_check_uptime_increases(client):
    import time
    r1 = client.get("/health")
    time.sleep(0.01)
    r2 = client.get("/health")
    assert r2.get_json()["uptime_seconds"] >= r1.get_json()["uptime_seconds"]


def test_health_check_response_has_only_expected_keys(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert set(r.get_json().keys()) == {"status", "uptime_seconds"}


def test_list_empty(client):
    r = client.get("/tasks")
    assert r.status_code == 200
    data = r.get_json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page_size"] == 20
    assert data["next_cursor"] is None


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
            "urgent": False,
            "color": None,
            "assignee": None,
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


# --- Input sanitization tests ---

# POST title stripping

def test_create_task_title_strips_spaces(client):
    r = client.post("/tasks", json={"title": "  Buy milk  "})
    assert r.status_code == 201
    assert r.get_json()["title"] == "Buy milk"


def test_create_task_title_strips_tabs(client):
    r = client.post("/tasks", json={"title": "\tBuy milk\t"})
    assert r.status_code == 201
    assert r.get_json()["title"] == "Buy milk"


def test_create_task_title_strips_newlines(client):
    r = client.post("/tasks", json={"title": "\n  Buy milk  \n"})
    assert r.status_code == 201
    assert r.get_json()["title"] == "Buy milk"


def test_create_task_title_strips_leading_only(client):
    r = client.post("/tasks", json={"title": "  leading only"})
    assert r.status_code == 201
    assert r.get_json()["title"] == "leading only"


def test_create_task_title_strips_trailing_only(client):
    r = client.post("/tasks", json={"title": "trailing only  "})
    assert r.status_code == 201
    assert r.get_json()["title"] == "trailing only"


def test_create_task_title_tabs_and_newlines_only_rejected(client):
    r = client.post("/tasks", json={"title": "\t\n"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "title must not be blank"


def test_create_task_title_preserves_internal_whitespace(client):
    r = client.post("/tasks", json={"title": "Buy  milk"})
    assert r.status_code == 201
    assert r.get_json()["title"] == "Buy  milk"


def test_create_task_stripped_title_in_response(client):
    r = client.post("/tasks", json={"title": "  Groceries  "})
    assert r.status_code == 201
    assert r.get_json()["title"] == "Groceries"


def test_create_task_stripped_title_on_get(client):
    client.post("/tasks", json={"title": "  Groceries  "})
    r = client.get("/tasks/1")
    assert r.status_code == 200
    assert r.get_json()["title"] == "Groceries"


# POST title length check after stripping

def test_create_task_title_stripped_to_200_accepted(client):
    padded = "   " + "a" * 200
    r = client.post("/tasks", json={"title": padded})
    assert r.status_code == 201
    assert r.get_json()["title"] == "a" * 200


def test_create_task_title_stripped_to_201_rejected(client):
    r = client.post("/tasks", json={"title": "a" * 201})
    assert r.status_code == 400
    assert r.get_json()["error"] == "title must not exceed 200 characters"


def test_create_task_title_padded_around_201_core_rejected(client):
    r = client.post("/tasks", json={"title": "  " + "a" * 201 + "  "})
    assert r.status_code == 400
    assert r.get_json()["error"] == "title must not exceed 200 characters"


# POST description stripping

def test_create_task_description_strips_spaces(client):
    r = client.post("/tasks", json={"title": "T", "description": "  Pick up 2%  "})
    assert r.status_code == 201
    assert r.get_json()["description"] == "Pick up 2%"


def test_create_task_description_strips_tabs(client):
    r = client.post("/tasks", json={"title": "T", "description": "\t notes \t"})
    assert r.status_code == 201
    assert r.get_json()["description"] == "notes"


def test_create_task_description_spaces_only_rejected(client):
    r = client.post("/tasks", json={"title": "T", "description": "   "})
    assert r.status_code == 400
    assert r.get_json()["error"] == "description must not be blank"


def test_create_task_description_tab_only_rejected(client):
    r = client.post("/tasks", json={"title": "T", "description": "\t"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "description must not be blank"


def test_create_task_description_newline_only_rejected(client):
    r = client.post("/tasks", json={"title": "T", "description": "\n"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "description must not be blank"


def test_create_task_description_empty_string_accepted(client):
    r = client.post("/tasks", json={"title": "T", "description": ""})
    assert r.status_code == 201
    assert r.get_json()["description"] == ""


def test_create_task_description_absent_defaults_to_empty(client):
    r = client.post("/tasks", json={"title": "T"})
    assert r.status_code == 201
    assert r.get_json()["description"] == ""


def test_create_task_description_preserves_internal_whitespace(client):
    r = client.post("/tasks", json={"title": "T", "description": "line1  line2"})
    assert r.status_code == 201
    assert r.get_json()["description"] == "line1  line2"


def test_create_task_stripped_description_in_response(client):
    r = client.post("/tasks", json={"title": "T", "description": "  Needs milk  "})
    assert r.status_code == 201
    assert r.get_json()["description"] == "Needs milk"


# POST description type validation

def test_create_task_description_integer_rejected(client):
    r = client.post("/tasks", json={"title": "T", "description": 42})
    assert r.status_code == 400
    assert r.get_json()["error"] == "description must be a string"


def test_create_task_description_boolean_rejected(client):
    r = client.post("/tasks", json={"title": "T", "description": True})
    assert r.status_code == 400
    assert r.get_json()["error"] == "description must be a string"


def test_create_task_description_array_rejected(client):
    r = client.post("/tasks", json={"title": "T", "description": ["a"]})
    assert r.status_code == 400
    assert r.get_json()["error"] == "description must be a string"


def test_create_task_description_null_rejected(client):
    r = client.post("/tasks", json={"title": "T", "description": None})
    assert r.status_code == 400
    assert r.get_json()["error"] == "description must be a string"


# POST both fields sanitized together

def test_create_task_both_fields_stripped(client):
    r = client.post("/tasks", json={"title": "  Groceries  ", "description": "  Needs milk  "})
    assert r.status_code == 201
    data = r.get_json()
    assert data["title"] == "Groceries"
    assert data["description"] == "Needs milk"


# PUT title stripping

def test_update_task_title_strips_spaces(client):
    client.post("/tasks", json={"title": "Original"})
    r = client.put("/tasks/1", json={"title": "  Updated  "})
    assert r.status_code == 200
    assert r.get_json()["title"] == "Updated"


def test_update_task_title_strips_tabs(client):
    client.post("/tasks", json={"title": "Original"})
    r = client.put("/tasks/1", json={"title": "\tUpdated\t"})
    assert r.status_code == 200
    assert r.get_json()["title"] == "Updated"


def test_update_task_title_tabs_and_newlines_only_rejected(client):
    client.post("/tasks", json={"title": "Original"})
    r = client.put("/tasks/1", json={"title": "\t\n"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "title must not be blank"


def test_update_task_omitting_title_preserves_existing(client):
    client.post("/tasks", json={"title": "  Keep me  "})
    r = client.put("/tasks/1", json={"completed": True})
    assert r.status_code == 200
    assert r.get_json()["title"] == "Keep me"


# PUT title length after stripping

def test_update_task_title_stripped_to_200_accepted(client):
    client.post("/tasks", json={"title": "Original"})
    padded = "   " + "a" * 200
    r = client.put("/tasks/1", json={"title": padded})
    assert r.status_code == 200
    assert r.get_json()["title"] == "a" * 200


def test_update_task_title_stripped_to_201_rejected(client):
    client.post("/tasks", json={"title": "Original"})
    r = client.put("/tasks/1", json={"title": "a" * 201})
    assert r.status_code == 400
    assert r.get_json()["error"] == "title must not exceed 200 characters"


# PUT description stripping

def test_update_task_description_strips_spaces(client):
    client.post("/tasks", json={"title": "T"})
    r = client.put("/tasks/1", json={"description": "  New desc  "})
    assert r.status_code == 200
    assert r.get_json()["description"] == "New desc"


def test_update_task_description_strips_tabs_and_newlines(client):
    client.post("/tasks", json={"title": "T"})
    r = client.put("/tasks/1", json={"description": "\tnotes\n"})
    assert r.status_code == 200
    assert r.get_json()["description"] == "notes"


def test_update_task_description_spaces_only_rejected(client):
    client.post("/tasks", json={"title": "T"})
    r = client.put("/tasks/1", json={"description": "   "})
    assert r.status_code == 400
    assert r.get_json()["error"] == "description must not be blank"


def test_update_task_description_empty_string_accepted(client):
    client.post("/tasks", json={"title": "T", "description": "has content"})
    r = client.put("/tasks/1", json={"description": ""})
    assert r.status_code == 200
    assert r.get_json()["description"] == ""


def test_update_task_omitting_description_preserves_existing(client):
    client.post("/tasks", json={"title": "T", "description": "keep me"})
    r = client.put("/tasks/1", json={"title": "Updated"})
    assert r.status_code == 200
    assert r.get_json()["description"] == "keep me"


def test_update_task_description_preserves_internal_whitespace(client):
    client.post("/tasks", json={"title": "T"})
    r = client.put("/tasks/1", json={"description": "inner  spaces"})
    assert r.status_code == 200
    assert r.get_json()["description"] == "inner  spaces"


# PUT description type validation

def test_update_task_description_integer_rejected(client):
    client.post("/tasks", json={"title": "T"})
    r = client.put("/tasks/1", json={"description": 42})
    assert r.status_code == 400
    assert r.get_json()["error"] == "description must be a string"


def test_update_task_description_boolean_rejected(client):
    client.post("/tasks", json={"title": "T"})
    r = client.put("/tasks/1", json={"description": False})
    assert r.status_code == 400
    assert r.get_json()["error"] == "description must be a string"


def test_update_task_description_null_rejected(client):
    client.post("/tasks", json={"title": "T"})
    r = client.put("/tasks/1", json={"description": None})
    assert r.status_code == 400
    assert r.get_json()["error"] == "description must be a string"


# PUT both fields sanitized together

def test_update_task_both_fields_stripped(client):
    client.post("/tasks", json={"title": "Original"})
    r = client.put("/tasks/1", json={"title": "  Renamed  ", "description": "  New body  "})
    assert r.status_code == 200
    data = r.get_json()
    assert data["title"] == "Renamed"
    assert data["description"] == "New body"


# Round-trip and list verification

def test_create_task_stripped_title_appears_in_list(client):
    client.post("/tasks", json={"title": "  Listed  "})
    r = client.get("/tasks")
    assert r.status_code == 200
    assert r.get_json()["items"][0]["title"] == "Listed"


def test_create_task_stripped_title_appears_in_export(client):
    import csv, io
    client.post("/tasks", json={"title": "  Exported  ", "description": "  desc  "})
    r = client.get("/tasks/export")
    assert r.status_code == 200
    rows = list(csv.DictReader(io.StringIO(r.data.decode())))
    assert rows[0]["title"] == "Exported"
    assert rows[0]["description"] == "desc"


def test_create_then_update_preserves_stripped_title(client):
    client.post("/tasks", json={"title": "  Original  "})
    client.put("/tasks/1", json={"completed": True})
    r = client.get("/tasks/1")
    assert r.status_code == 200
    assert r.get_json()["title"] == "Original"


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
    assert data["page_size"] == 20
    assert data["next_cursor"] is None
    assert len(data["items"]) == 5


def test_pagination_limits_items(client):
    for i in range(5):
        client.post("/tasks", json={"title": f"Task {i}"})
    r = client.get("/tasks?page_size=2")
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 5
    assert data["page_size"] == 2
    assert data["next_cursor"]
    assert len(data["items"]) == 2


def test_pagination_next_cursor_returns_following_items(client):
    for i in range(5):
        client.post("/tasks", json={"title": f"Task {i}"})
    first_page = client.get("/tasks?page_size=2")
    cursor = first_page.get_json()["next_cursor"]
    r = client.get(f"/tasks?page_size=2&cursor={cursor}")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data["items"]) == 2
    assert [item["title"] for item in data["items"]] == ["Task 2", "Task 3"]
    assert data["next_cursor"]


def test_pagination_last_page_has_no_next_cursor(client):
    for i in range(3):
        client.post("/tasks", json={"title": f"Task {i}"})
    first_page = client.get("/tasks?page_size=2").get_json()
    r = client.get(f"/tasks?page_size=2&cursor={first_page['next_cursor']}")
    assert r.status_code == 200
    data = r.get_json()
    assert [item["title"] for item in data["items"]] == ["Task 2"]
    assert data["next_cursor"] is None


def test_pagination_invalid_cursor_returns_400(client):
    r = client.get("/tasks?cursor=not-a-real-cursor")
    assert r.status_code == 400
    assert "cursor" in r.get_json()["error"]


def test_pagination_invalid_page_size_returns_400(client):
    r = client.get("/tasks?page_size=abc")
    assert r.status_code == 400
    assert "page_size" in r.get_json()["error"]


def test_pagination_zero_page_size_returns_400(client):
    r = client.get("/tasks?page_size=0")
    assert r.status_code == 400
    assert "page_size" in r.get_json()["error"]


def test_pagination_cursor_must_match_query_shape(client):
    for i in range(3):
        client.post("/tasks", json={"title": f"Task {i}"})
    first_page = client.get("/tasks?page_size=2&sort=title&order=asc").get_json()
    r = client.get(f"/tasks?page_size=2&sort=title&order=desc&cursor={first_page['next_cursor']}")
    assert r.status_code == 400
    assert r.get_json()["error"] == "cursor does not match the current query"


def test_pagination_with_priority_filter(client):
    for _ in range(3):
        client.post("/tasks", json={"title": "high task", "priority": "high"})
    for _ in range(2):
        client.post("/tasks", json={"title": "low task", "priority": "low"})
    r = client.get("/tasks?priority=high&page_size=2")
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 3
    assert data["next_cursor"]
    assert len(data["items"]) == 2
    assert all(item["priority"] == "high" for item in data["items"])


def test_pagination_uses_configured_default_page_size(client):
    app.config["LIST_PAGE_SIZE_DEFAULT"] = 2
    for i in range(3):
        client.post("/tasks", json={"title": f"Task {i}"})

    r = client.get("/tasks")

    assert r.status_code == 200
    data = r.get_json()
    assert data["page_size"] == 2
    assert len(data["items"]) == 2
    assert data["next_cursor"]


def test_pagination_rejects_page_size_above_configured_max(client):
    app.config["LIST_PAGE_SIZE_MAX"] = 2

    r = client.get("/tasks?page_size=3")

    assert r.status_code == 400
    assert r.get_json()["error"] == "page_size must not exceed 2"


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
    assert lines == ["id,title,description,completed,priority,due_date,notes,created_at,urgent,assignee"]


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


def test_export_supports_cursor_pagination(client):
    import csv, io

    for i in range(3):
        client.post("/tasks", json={"title": f"Task {i}"})

    first_page = client.get("/tasks/export?page_size=2")
    assert first_page.status_code == 200
    assert first_page.headers["X-Page-Size"] == "2"
    assert first_page.headers["X-Total-Count"] == "3"
    assert first_page.headers["X-Next-Cursor"]

    first_rows = list(csv.DictReader(io.StringIO(first_page.data.decode())))
    assert [row["title"] for row in first_rows] == ["Task 0", "Task 1"]

    cursor = first_page.headers["X-Next-Cursor"]
    second_page = client.get(f"/tasks/export?page_size=2&cursor={cursor}")
    assert second_page.status_code == 200
    assert second_page.headers["X-Next-Cursor"] == ""

    second_rows = list(csv.DictReader(io.StringIO(second_page.data.decode())))
    assert [row["title"] for row in second_rows] == ["Task 2"]


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
    r = client.get("/tasks?page_size=2")
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


# --- X-Request-ID header tests ---

import uuid as _uuid_mod

_UUID4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def _assert_request_id(response):
    value = response.headers.get("X-Request-ID", "")
    assert _UUID4_PATTERN.match(value), f"X-Request-ID {value!r} is not a valid UUID v4"
    _uuid_mod.UUID(value, version=4)
    assert value


# Format validation

def test_request_id_is_valid_uuid4(client):
    r = client.get("/health")
    _assert_request_id(r)


def test_request_id_parseable_by_uuid_module(client):
    r = client.get("/health")
    value = r.headers.get("X-Request-ID", "")
    parsed = _uuid_mod.UUID(value, version=4)
    assert parsed.version == 4


def test_request_id_is_non_empty(client):
    r = client.get("/health")
    assert r.headers.get("X-Request-ID", "") != ""


# Coverage across all endpoints and HTTP methods

def test_request_id_on_get_health(client):
    _assert_request_id(client.get("/health"))


def test_request_id_on_get_tasks(client):
    _assert_request_id(client.get("/tasks"))


def test_request_id_on_post_tasks(client):
    _assert_request_id(client.post("/tasks", json={"title": "ID test"}))


def test_request_id_on_get_task(client):
    client.post("/tasks", json={"title": "ID test"})
    _assert_request_id(client.get("/tasks/1"))


def test_request_id_on_put_task(client):
    client.post("/tasks", json={"title": "ID test"})
    _assert_request_id(client.put("/tasks/1", json={"title": "Updated"}))


def test_request_id_on_delete_task(client):
    client.post("/tasks", json={"title": "ID test"})
    _assert_request_id(client.delete("/tasks/1"))


def test_request_id_on_patch_toggle(client):
    client.post("/tasks", json={"title": "ID test"})
    _assert_request_id(client.patch("/tasks/1/toggle"))


def test_request_id_on_get_stats(client):
    _assert_request_id(client.get("/tasks/stats"))


def test_request_id_on_get_export(client):
    _assert_request_id(client.get("/tasks/export"))


def test_request_id_on_delete_completed(client):
    _assert_request_id(client.delete("/tasks/completed"))


# Error and edge-case responses

def test_request_id_on_400_missing_title(client):
    r = client.post("/tasks", json={})
    assert r.status_code == 400
    _assert_request_id(r)


def test_request_id_on_400_invalid_priority(client):
    r = client.post("/tasks", json={"title": "X", "priority": "urgent"})
    assert r.status_code == 400
    _assert_request_id(r)


def test_request_id_on_404_task_not_found(client):
    r = client.get("/tasks/9999")
    assert r.status_code == 404
    _assert_request_id(r)


def test_request_id_on_405_wrong_method(client):
    client.post("/tasks", json={"title": "ID test"})
    r = client.get("/tasks/1/toggle")
    assert r.status_code == 405
    _assert_request_id(r)


def test_request_id_on_400_invalid_priority_filter(client):
    r = client.get("/tasks?priority=invalid")
    assert r.status_code == 400
    _assert_request_id(r)


def test_request_id_on_400_invalid_sort(client):
    r = client.get("/tasks?sort=invalid")
    assert r.status_code == 400
    _assert_request_id(r)


def test_request_id_on_400_invalid_cursor(client):
    r = client.get("/tasks?cursor=bad-cursor")
    assert r.status_code == 400
    _assert_request_id(r)


# Uniqueness and independence

def test_request_id_unique_across_two_requests(client):
    id1 = client.get("/health").headers.get("X-Request-ID")
    id2 = client.get("/health").headers.get("X-Request-ID")
    assert id1 != id2


def test_request_id_unique_across_ten_requests(client):
    ids = [client.get("/health").headers.get("X-Request-ID") for _ in range(10)]
    assert len(set(ids)) == 10


def test_request_id_independent_between_two_requests(client):
    r1 = client.get("/tasks")
    r2 = client.post("/tasks", json={"title": "Another"})
    assert r1.headers.get("X-Request-ID") != r2.headers.get("X-Request-ID")


# --- CORS tests ---

def test_cors_headers_on_health_check(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers["Access-Control-Allow-Origin"] == "*"
    assert r.headers["Access-Control-Allow-Methods"] == "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    assert r.headers["Access-Control-Allow-Headers"] == "Content-Type"


def test_cors_headers_on_tasks_list(client):
    r = client.get("/tasks")
    assert r.status_code == 200
    assert r.headers["Access-Control-Allow-Origin"] == "*"


def test_cors_headers_on_create_task(client):
    r = client.post("/tasks", json={"title": "CORS test"})
    assert r.status_code == 201
    assert r.headers["Access-Control-Allow-Origin"] == "*"


def test_cors_headers_on_toggle_task(client):
    client.post("/tasks", json={"title": "CORS toggle"})
    r = client.patch("/tasks/1/toggle")
    assert r.status_code == 200
    assert r.headers["Access-Control-Allow-Origin"] == "*"


def test_cors_headers_on_export_response(client):
    r = client.get("/tasks/export")
    assert r.status_code == 200
    assert r.headers["Access-Control-Allow-Origin"] == "*"


def test_cors_headers_on_validation_error(client):
    r = client.post("/tasks", json={})
    assert r.status_code == 400
    assert r.headers["Access-Control-Allow-Origin"] == "*"


def test_cors_headers_on_not_found(client):
    r = client.get("/tasks/999")
    assert r.status_code == 404
    assert r.headers["Access-Control-Allow-Origin"] == "*"


def test_cors_preflight_on_tasks(client):
    r = client.options("/tasks")
    assert r.status_code == 200
    assert r.headers["Access-Control-Allow-Origin"] == "*"
    assert r.headers["Access-Control-Allow-Methods"] == "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    assert r.headers["Access-Control-Allow-Headers"] == "Content-Type"


def test_cors_preflight_on_toggle_advertises_patch(client):
    client.post("/tasks", json={"title": "Preflight"})
    r = client.options("/tasks/1/toggle")
    assert r.status_code == 200
    allow_header = r.headers["Allow"]
    assert "PATCH" in allow_header
    assert "OPTIONS" in allow_header
    assert r.headers["Access-Control-Allow-Methods"] == "GET, POST, PUT, PATCH, DELETE, OPTIONS"


# --- Query parameter validation tests ---

def test_list_tasks_rejects_unknown_param(client):
    r = client.get("/tasks?foo=bar")
    assert r.status_code == 400
    assert r.get_json()["error"] == "unsupported query parameter: foo"


def test_list_tasks_rejects_unknown_param_alongside_valid_params(client):
    r = client.get("/tasks?priority=high&unknown=1")
    assert r.status_code == 400
    assert "unsupported query parameter" in r.get_json()["error"]


def test_list_tasks_all_known_params_accepted(client):
    r = client.get("/tasks?priority=high&sort=title&order=asc&page_size=10")
    assert r.status_code == 200


def test_list_tasks_unknown_param_returns_structured_error(client):
    r = client.get("/tasks?typo=yes")
    assert r.status_code == 400
    data = r.get_json()
    assert "error" in data
    assert "typo" in data["error"]


def test_health_rejects_unknown_param(client):
    r = client.get("/health?debug=true")
    assert r.status_code == 400
    assert r.get_json()["error"] == "unsupported query parameter: debug"


def test_export_rejects_unknown_param(client):
    r = client.get("/tasks/export?format=json")
    assert r.status_code == 400
    assert r.get_json()["error"] == "unsupported query parameter: format"


def test_stats_rejects_unknown_param(client):
    r = client.get("/tasks/stats?group=priority")
    assert r.status_code == 400
    assert r.get_json()["error"] == "unsupported query parameter: group"


def test_get_task_rejects_unknown_param(client):
    client.post("/tasks", json={"title": "Test"})
    r = client.get("/tasks/1?expand=true")
    assert r.status_code == 400
    assert r.get_json()["error"] == "unsupported query parameter: expand"


def test_unknown_param_error_includes_cors_headers(client):
    r = client.get("/tasks?bad=param")
    assert r.status_code == 400
    assert r.headers["Access-Control-Allow-Origin"] == "*"


def test_unknown_param_error_includes_request_id(client):
    r = client.get("/tasks?bad=param")
    assert r.status_code == 400
    _assert_request_id(r)


# --- Rate limiting tests ---

@pytest.fixture
def rate_limited_client(tmp_path):
    app.config["DATABASE"] = str(tmp_path / "rl_test.db")
    app.config["TESTING"] = True
    app.config["RATE_LIMIT_ENABLED"] = True
    app.config["RATE_LIMIT_REQUESTS"] = 3
    app.config["RATE_LIMIT_WINDOW"] = 60
    _rate_limit_store.clear()
    with app.test_client() as c:
        yield c
    app.config["RATE_LIMIT_ENABLED"] = False
    _rate_limit_store.clear()


def test_rate_limit_headers_present_on_normal_response(rate_limited_client):
    r = rate_limited_client.get("/health")
    assert r.status_code == 200
    assert r.headers.get("X-RateLimit-Limit") == "3"
    assert r.headers.get("X-RateLimit-Remaining") == "2"
    assert r.headers.get("X-RateLimit-Reset") is not None


def test_rate_limit_remaining_decrements(rate_limited_client):
    r1 = rate_limited_client.get("/health")
    r2 = rate_limited_client.get("/health")
    assert int(r1.headers["X-RateLimit-Remaining"]) > int(r2.headers["X-RateLimit-Remaining"])


def test_rate_limit_exceeded_returns_429(rate_limited_client):
    for _ in range(3):
        rate_limited_client.get("/health")
    r = rate_limited_client.get("/health")
    assert r.status_code == 429
    assert r.get_json()["error"] == "rate limit exceeded"


def test_rate_limit_429_has_retry_after_header(rate_limited_client):
    for _ in range(3):
        rate_limited_client.get("/health")
    r = rate_limited_client.get("/health")
    assert r.status_code == 429
    retry_after = r.headers.get("Retry-After")
    assert retry_after is not None
    assert int(retry_after) >= 1


def test_rate_limit_429_has_rate_limit_headers(rate_limited_client):
    for _ in range(3):
        rate_limited_client.get("/health")
    r = rate_limited_client.get("/health")
    assert r.status_code == 429
    assert r.headers.get("X-RateLimit-Limit") == "3"
    assert r.headers.get("X-RateLimit-Remaining") == "0"
    assert r.headers.get("X-RateLimit-Reset") is not None


def test_rate_limit_429_has_cors_headers(rate_limited_client):
    for _ in range(3):
        rate_limited_client.get("/health")
    r = rate_limited_client.get("/health")
    assert r.status_code == 429
    assert r.headers["Access-Control-Allow-Origin"] == "*"


def test_rate_limit_429_has_request_id(rate_limited_client):
    for _ in range(3):
        rate_limited_client.get("/health")
    r = rate_limited_client.get("/health")
    assert r.status_code == 429
    _assert_request_id(r)


def test_rate_limit_disabled_allows_unlimited_requests(client):
    for _ in range(200):
        r = client.get("/health")
        assert r.status_code == 200


def test_rate_limit_no_headers_when_disabled(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert "X-RateLimit-Limit" not in r.headers


def test_rate_limit_applies_across_endpoints(rate_limited_client):
    rate_limited_client.get("/health")
    rate_limited_client.get("/tasks")
    rate_limited_client.get("/health")
    r = rate_limited_client.get("/tasks")
    assert r.status_code == 429


def test_rate_limit_reset_time_is_unix_timestamp(rate_limited_client):
    import time
    r = rate_limited_client.get("/health")
    reset = int(r.headers["X-RateLimit-Reset"])
    now = int(time.time())
    assert reset >= now
    assert reset <= now + 61


# --- urgent field tests ---

def test_create_task_urgent_defaults_to_false(client):
    r = client.post("/tasks", json={"title": "Normal task"})
    assert r.status_code == 201
    assert r.get_json()["urgent"] is False


def test_create_task_with_urgent_true(client):
    r = client.post("/tasks", json={"title": "Fire drill", "urgent": True})
    assert r.status_code == 201
    assert r.get_json()["urgent"] is True


def test_create_task_with_urgent_false(client):
    r = client.post("/tasks", json={"title": "Later", "urgent": False})
    assert r.status_code == 201
    assert r.get_json()["urgent"] is False


def test_create_task_urgent_non_boolean_rejected(client):
    r = client.post("/tasks", json={"title": "Bad", "urgent": "yes"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "urgent must be a boolean"


def test_create_task_urgent_integer_rejected(client):
    r = client.post("/tasks", json={"title": "Bad", "urgent": 1})
    assert r.status_code == 400
    assert r.get_json()["error"] == "urgent must be a boolean"


def test_get_task_includes_urgent(client):
    client.post("/tasks", json={"title": "Task", "urgent": True})
    r = client.get("/tasks/1")
    assert r.status_code == 200
    assert r.get_json()["urgent"] is True


def test_list_tasks_includes_urgent(client):
    client.post("/tasks", json={"title": "A", "urgent": True})
    client.post("/tasks", json={"title": "B"})
    r = client.get("/tasks")
    assert r.status_code == 200
    items = r.get_json()["items"]
    assert items[0]["urgent"] is True
    assert items[1]["urgent"] is False


def test_update_task_urgent_to_true(client):
    client.post("/tasks", json={"title": "Task"})
    r = client.put("/tasks/1", json={"urgent": True})
    assert r.status_code == 200
    assert r.get_json()["urgent"] is True


def test_update_task_urgent_to_false(client):
    client.post("/tasks", json={"title": "Task", "urgent": True})
    r = client.put("/tasks/1", json={"urgent": False})
    assert r.status_code == 200
    assert r.get_json()["urgent"] is False


def test_update_task_urgent_non_boolean_rejected(client):
    client.post("/tasks", json={"title": "Task"})
    r = client.put("/tasks/1", json={"urgent": "true"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "urgent must be a boolean"


def test_update_task_omitting_urgent_preserves_value(client):
    client.post("/tasks", json={"title": "Task", "urgent": True})
    r = client.put("/tasks/1", json={"title": "Updated"})
    assert r.status_code == 200
    assert r.get_json()["urgent"] is True


def test_list_tasks_filter_urgent_true(client):
    client.post("/tasks", json={"title": "Urgent task", "urgent": True})
    client.post("/tasks", json={"title": "Normal task"})
    r = client.get("/tasks?urgent=true")
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Urgent task"
    assert data["items"][0]["urgent"] is True


def test_list_tasks_filter_urgent_false(client):
    client.post("/tasks", json={"title": "Urgent task", "urgent": True})
    client.post("/tasks", json={"title": "Normal task"})
    r = client.get("/tasks?urgent=false")
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Normal task"
    assert data["items"][0]["urgent"] is False


def test_list_tasks_filter_urgent_invalid_value_rejected(client):
    r = client.get("/tasks?urgent=yes")
    assert r.status_code == 400
    assert r.get_json()["error"] == "urgent must be true or false"


def test_list_tasks_urgent_sorts_before_non_urgent(client):
    client.post("/tasks", json={"title": "Normal A"})
    client.post("/tasks", json={"title": "Normal B"})
    client.post("/tasks", json={"title": "Urgent X", "urgent": True})
    r = client.get("/tasks?sort=created_at&order=asc")
    assert r.status_code == 200
    titles = [item["title"] for item in r.get_json()["items"]]
    assert titles[0] == "Urgent X"
    assert set(titles[1:]) == {"Normal A", "Normal B"}


def test_list_tasks_urgent_low_priority_sorts_before_non_urgent_high_priority(client):
    client.post("/tasks", json={"title": "High priority", "priority": "high"})
    client.post("/tasks", json={"title": "Urgent low", "priority": "low", "urgent": True})
    r = client.get("/tasks?sort=priority&order=desc")
    assert r.status_code == 200
    items = r.get_json()["items"]
    assert items[0]["title"] == "Urgent low"
    assert items[1]["title"] == "High priority"


def test_list_tasks_multiple_urgent_then_non_urgent(client):
    client.post("/tasks", json={"title": "U1", "urgent": True})
    client.post("/tasks", json={"title": "N1"})
    client.post("/tasks", json={"title": "U2", "urgent": True})
    client.post("/tasks", json={"title": "N2"})
    r = client.get("/tasks")
    assert r.status_code == 200
    items = r.get_json()["items"]
    urgent_items = [i for i in items if i["urgent"]]
    non_urgent_items = [i for i in items if not i["urgent"]]
    # All urgent items appear before any non-urgent item
    if urgent_items and non_urgent_items:
        last_urgent_pos = max(items.index(i) for i in urgent_items)
        first_non_urgent_pos = min(items.index(i) for i in non_urgent_items)
        assert last_urgent_pos < first_non_urgent_pos


def test_pagination_urgent_filter_cursor_shape_check(client):
    for i in range(3):
        client.post("/tasks", json={"title": f"Task {i}", "urgent": True})
    first_page = client.get("/tasks?urgent=true&page_size=2").get_json()
    r = client.get(f"/tasks?page_size=2&cursor={first_page['next_cursor']}")
    assert r.status_code == 400
    assert r.get_json()["error"] == "cursor does not match the current query"


def test_export_includes_urgent_column(client):
    import csv, io
    client.post("/tasks", json={"title": "Fire drill", "urgent": True})
    client.post("/tasks", json={"title": "Normal"})
    r = client.get("/tasks/export")
    assert r.status_code == 200
    reader = csv.DictReader(io.StringIO(r.data.decode()))
    rows = list(reader)
    assert rows[0]["urgent"] == "true"
    assert rows[1]["urgent"] == "false"

# --- assignee field tests ---

def test_create_task_with_assignee(client):
    r = client.post("/tasks", json={"title": "Task", "assignee": "alice"})
    assert r.status_code == 201
    assert r.get_json()["assignee"] == "alice"


def test_create_task_invalid_assignee_type(client):
    r = client.post("/tasks", json={"title": "Task", "assignee": 123})
    assert r.status_code == 400
    assert r.get_json()["error"] == "assignee must be a string or null"


def test_update_task_assignee(client):
    client.post("/tasks", json={"title": "Task"})
    r = client.put("/tasks/1", json={"assignee": "bob"})
    assert r.status_code == 200
    assert r.get_json()["assignee"] == "bob"


def test_update_task_clear_assignee(client):
    client.post("/tasks", json={"title": "Task", "assignee": "alice"})
    r = client.put("/tasks/1", json={"assignee": None})
    assert r.status_code == 200
    assert r.get_json()["assignee"] is None


def test_list_tasks_filter_by_assignee(client):
    client.post("/tasks", json={"title": "Task 1", "assignee": "alice"})
    client.post("/tasks", json={"title": "Task 2", "assignee": "bob"})
    client.post("/tasks", json={"title": "Task 3", "assignee": "alice"})
    
    r = client.get("/tasks?assignee=alice")
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 2
    assert [item["title"] for item in data["items"]] == ["Task 1", "Task 3"]


def test_export_includes_assignee(client):
    import csv, io
    client.post("/tasks", json={"title": "Task 1", "assignee": "alice"})
    r = client.get("/tasks/export")
    assert r.status_code == 200
    reader = csv.DictReader(io.StringIO(r.data.decode()))
    rows = list(reader)
    assert rows[0]["assignee"] == "alice"


def test_pagination_with_assignee_filter(client):
    for i in range(3):
        client.post("/tasks", json={"title": f"Task {i}", "assignee": "alice"})
    
    r = client.get("/tasks?assignee=alice&page_size=2")
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 3
    assert data["next_cursor"]
    assert len(data["items"]) == 2
    
    cursor = data["next_cursor"]
    r = client.get(f"/tasks?assignee=alice&page_size=2&cursor={cursor}")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Task 2"
