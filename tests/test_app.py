from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Keep each test isolated from in-memory state changes in other tests."""
    original = deepcopy(activities)
    yield
    activities.clear()
    activities.update(deepcopy(original))


# ===== GET /activities Tests =====
def test_get_activities_success():
    """GET /activities returns a populated dictionary with expected fields."""
    response = client.get("/activities")

    assert response.status_code == 200
    payload = response.json()

    assert isinstance(payload, dict)
    assert len(payload) > 0

    for activity_name, activity_data in payload.items():
        assert "description" in activity_data
        assert "schedule" in activity_data
        assert "max_participants" in activity_data
        assert "participants" in activity_data
        assert isinstance(activity_data["participants"], list)
        assert isinstance(activity_data["max_participants"], int)
        assert activity_data["max_participants"] >= len(activity_data["participants"])


def test_get_activities_contains_expected_activity():
    """GET /activities includes a known activity and expected metadata."""
    response = client.get("/activities")
    payload = response.json()

    assert "Chess Club" in payload
    assert payload["Chess Club"]["description"] == "Learn strategies and compete in chess tournaments"
    assert payload["Chess Club"]["schedule"] == "Fridays, 3:30 PM - 5:00 PM"
    assert payload["Chess Club"]["max_participants"] == 12


# ===== POST /activities/{activity_name}/signup Tests =====
def test_signup_for_activity_success():
    """Successful signup adds the student to the participant list."""
    activity_name = "Programming Class"
    email = "newstudent@mergington.edu"

    response = client.post(f"/activities/{activity_name}/signup?email={email}")

    assert response.status_code == 200
    result = response.json()
    assert "message" in result
    assert email in result["message"]
    assert activity_name in result["message"]

    payload = client.get("/activities").json()
    assert email in payload[activity_name]["participants"]


def test_signup_requires_email_query_parameter():
    """POST signup without the required email parameter is rejected."""
    response = client.post("/activities/Chess Club/signup")

    assert response.status_code == 422


def test_signup_for_activity_not_found():
    """POST signup for a missing activity returns a 404 error."""
    response = client.post("/activities/Nonexistent Activity/signup?email=student@mergington.edu")

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_duplicate_email():
    """A student cannot sign up twice for the same activity."""
    activity_name = "Tennis Club"
    email = "duplicate@mergington.edu"

    first_response = client.post(f"/activities/{activity_name}/signup?email={email}")
    assert first_response.status_code == 200

    second_response = client.post(f"/activities/{activity_name}/signup?email={email}")
    assert second_response.status_code == 400
    assert "already signed up" in second_response.json()["detail"]


# ===== DELETE /activities/{activity_name}/unregister Tests =====
def test_unregister_participant_success():
    """A registered participant can be removed from an activity."""
    activity_name = "Chess Club"
    email = "newstudent@mergington.edu"

    signup_response = client.post(f"/activities/{activity_name}/signup?email={email}")
    assert signup_response.status_code == 200

    response = client.delete(f"/activities/{activity_name}/unregister?email={email}")

    assert response.status_code == 200
    assert response.json()["message"] == f"Unregistered {email} from {activity_name}"

    payload = client.get("/activities").json()
    assert email not in payload[activity_name]["participants"]


def test_unregister_participant_not_found():
    """Deleting an activity that does not exist returns 404."""
    response = client.delete("/activities/Nonexistent Activity/unregister?email=missing@mergington.edu")

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_participant_not_registered():
    """Unregistering a student who is not enrolled returns 404."""
    activity_name = "Drama Club"
    email = "notregistered@mergington.edu"

    response = client.delete(f"/activities/{activity_name}/unregister?email={email}")

    assert response.status_code == 404
    assert "not registered" in response.json()["detail"]


def test_unregister_requires_email_query_parameter():
    """DELETE unregister without email should fail validation."""
    response = client.delete("/activities/Chess Club/unregister")

    assert response.status_code == 422


# ===== Root endpoint test =====
def test_root_redirect():
    """The root path redirects to the static HTML frontend."""
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"
