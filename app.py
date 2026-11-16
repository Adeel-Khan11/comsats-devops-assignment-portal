"""Student Assignment Submission Portal built with Flask and SQLite."""

import os
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, flash, redirect, render_template, request, url_for


def is_valid_submission_url(value: str) -> bool:
    """Return True only for absolute HTTP(S) URLs with a usable hostname."""
    if not value or any(character.isspace() for character in value):
        return False

    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        # Accessing .port also validates that a supplied port is numeric and in range.
        _ = parsed.port
    except ValueError:
        return False

    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc or not hostname:
        return True

    # Accept ordinary DNS names, IPv4 addresses and localhost. This deliberately
    # rejects malformed host strings such as "bad host" or "example..com".
    if ".." in hostname or hostname.startswith(".") or hostname.endswith("."):
        return False
    if not re.fullmatch(r"[A-Za-z0-9._:-]+", hostname):
        return False

    return True


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    default_database = Path(app.instance_path) / "submissions.sqlite3"
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-this-secret"),
        DATABASE=os.environ.get("DATABASE_PATH", str(default_database)),
    )

    if test_config:
        app.config.update(test_config)

    database_path = Path(app.config["DATABASE"])
    if str(database_path) != ":memory:":
        database_path.parent.mkdir(parents=True, exist_ok=True)

    def connect_db() -> sqlite3.Connection:
        connection = sqlite3.connect(app.config["DATABASE"])
        connection.row_factory = sqlite3.Row
        return connection

    def initialize_database() -> None:
        with connect_db() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_name TEXT NOT NULL,
                    registration_number TEXT NOT NULL,
                    assignment_title TEXT NOT NULL,
                    submission_url TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def all_submissions() -> list[sqlite3.Row]:
        with connect_db() as connection:
            return connection.execute(
                "SELECT * FROM submissions ORDER BY id DESC"
            ).fetchall()

    initialize_database()

    @app.get("/")
    def index():
        return render_template("index.html", submissions=all_submissions(), values={})

    @app.post("/submit")
    def submit():
        values = {
            "student_name": request.form.get("student_name", "").strip(),
            "registration_number": request.form.get("registration_number", "").strip(),
            "assignment_title": request.form.get("assignment_title", "").strip(),
            "submission_url": request.form.get("submission_url", "").strip(),
        }

        labels = {
            "student_name": "Student name",
            "registration_number": "Registration number",
            "assignment_title": "Assignment title",
            "submission_url": "Submission URL",
        }
        errors = [f"{labels[key]} is required." for key, value in values.items() if not value]

        if values["submission_url"] and not is_valid_submission_url(values["submission_url"]):
            errors.append("Please enter a valid HTTP or HTTPS submission URL.")

        if errors:
            return (
                render_template(
                    "index.html",
                    submissions=all_submissions(),
                    values=values,
                    errors=errors,
                ),
                400,
            )

        with connect_db() as connection:
            connection.execute(
                """
                INSERT INTO submissions
                    (student_name, registration_number, assignment_title, submission_url)
                VALUES (?, ?, ?, ?)
                """,
                (
                    values["student_name"],
                    values["registration_number"],
                    values["assignment_title"],
                    values["submission_url"],
                ),
            )

        flash("Submission saved successfully.", "success")
        return redirect(url_for("index"), code=303)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
