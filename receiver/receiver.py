"""Authenticated local HTTP receiver for GitHub Actions test reports."""

import hmac
import json
import os
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024  # 1 MiB


def expected_token() -> str:
    return os.environ.get("REPORT_RECEIVER_TOKEN", "")


def report_path() -> Path:
    return Path(os.environ.get("REPORT_FILE", "testreport.json")).resolve()


@app.get("/health")
def health():
    return jsonify({"status": "ok", "receiver": "assignment-test-report"}), 200


@app.post("/report")
def receive_report():
    token = expected_token()
    if not token:
        return jsonify({"error": "Receiver token is not configured on this computer."}), 503

    authorization = request.headers.get("Authorization", "")
    supplied_token = authorization.removeprefix("Bearer ")
    if not hmac.compare_digest(supplied_token, token):
        return jsonify({"error": "Unauthorized"}), 401

    report = request.get_json(silent=True)
    if not isinstance(report, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    required = {"repository", "branch", "commit_sha", "pipeline_run_id", "execution_timestamp", "tests", "summary"}
    missing = sorted(required.difference(report.keys()))
    if missing:
        return jsonify({"error": "Missing report fields", "fields": missing}), 400
    if not isinstance(report["tests"], list) or not isinstance(report["summary"], dict):
        return jsonify({"error": "The tests field must be a list and summary must be an object."}), 400

    destination = report_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(json.dumps(report, indent=2), encoding="utf-8")
    temporary.replace(destination)

    print(
        f"Saved pipeline run {report['pipeline_run_id']} "
        f"({report['summary'].get('overall_status', 'unknown')}) to {destination}"
    )
    return jsonify({"message": "Report received and saved.", "file": str(destination)}), 201


if __name__ == "__main__":
    host = os.environ.get("RECEIVER_HOST", "127.0.0.1")
    port = int(os.environ.get("RECEIVER_PORT", "5001"))
    app.run(host=host, port=port, debug=False)
