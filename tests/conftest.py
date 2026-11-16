"""Pytest plugin: record the real outcome of each executed test."""

import json
import os
from pathlib import Path

import pytest

_TEST_RESULTS: dict[str, dict] = {}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    result = _TEST_RESULTS.setdefault(
        item.nodeid,
        {
            "name": item.nodeid,
            "result": "unknown",
            "failure_message": None,
        },
    )

    # Capture failures in setup, test-call, or teardown phases.
    if report.failed:
        result["result"] = "failed"
        result["failure_message"] = str(report.longrepr)
    elif report.skipped and result["result"] != "failed":
        result["result"] = "skipped"
        result["failure_message"] = str(report.longrepr)
    elif report.when == "call" and report.passed and result["result"] != "failed":
        result["result"] = "passed"


def pytest_sessionfinish(session, exitstatus):
    """Write the test results even when one or more tests fail."""
    output_path = Path(os.environ.get("TEST_RESULTS_PATH", "test-results.json"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pytest_exit_status": int(exitstatus),
        "tests": list(_TEST_RESULTS.values()),
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
