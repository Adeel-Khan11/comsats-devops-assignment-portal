"""Required automated tests for the assignment submission portal."""

import sqlite3

import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path):
    database_file = tmp_path / "test-submissions.sqlite3"
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "pytest-secret",
            "DATABASE": str(database_file),
        }
    )
    application.config["TEST_DATABASE_FILE"] = database_file
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def valid_submission():
    return {
        "student_name": "Ali Khan",
        "registration_number": "FA22-BCS-001",
        "assignment_title": "CSC418 DevOps Mid Course",
        "submission_url": "https://github.com/example/student-assignment",
    }


def saved_submission_count(app):
    with sqlite3.connect(app.config["TEST_DATABASE_FILE"]) as connection:
        return connection.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]


def test_complete_valid_submission_is_saved_and_displayed(client, app):
    response = client.post("/submit", data=valid_submission(), follow_redirects=True)

    assert response.status_code == 200
    assert b"Submission saved successfully." in response.data
    assert b"Ali Khan" in response.data
    assert b"FA22-BCS-001" in response.data
    assert b"CSC418 DevOps Mid Course" in response.data
    assert b"https://github.com/example/student-assignment" in response.data
    assert saved_submission_count(app) == 1


def test_missing_registration_number_is_rejected_and_not_saved(client, app):
    data = valid_submission()
    data["registration_number"] = "   "

    response = client.post("/submit", data=data)

    assert response.status_code == 400
    assert b"Registration number is required." in response.data
    assert saved_submission_count(app) == 0


def test_invalid_submission_url_is_rejected_and_not_saved(client, app):
    data = valid_submission()
    data["submission_url"] = "javascript:alert(1)"

    response = client.post("/submit", data=data)

    assert response.status_code == 400
    assert b"Please enter a valid HTTP or HTTPS submission URL." in response.data
    assert saved_submission_count(app) == 0


def test_missing_assignment_title_is_rejected(client, app):
    data = valid_submission()
    data["assignment_title"] = ""

    response = client.post("/submit", data=data)

    assert response.status_code == 400
    assert b"Assignment title is required." in response.data
    assert saved_submission_count(app) == 0
