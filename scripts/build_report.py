"""Convert pytest hook output into the JSON report required by the lab."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    raw_path = Path(os.environ.get("TEST_RESULTS_PATH", "test-results.json"))
    output_path = Path(os.environ.get("REPORT_OUTPUT_PATH", "testreport.json"))
    test_step_outcome = os.environ.get("TEST_STEP_OUTCOME", "unknown")

    if raw_path.exists():
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        raw_tests = raw.get("tests", [])
    else:
        raw_tests = []

    tests = []
    for test in raw_tests:
        tests.append(
            {
                "name": test.get("name", "unnamed test"),
                "result": test.get("result", "unknown"),
                "failure_message": test.get("failure_message"),
            }
        )

    total = len(tests)
    passed = sum(test["result"] == "passed" for test in tests)
    failed = sum(test["result"] == "failed" for test in tests)
    skipped = sum(test["result"] == "skipped" for test in tests)

    # A collection/setup failure can occur before any individual test is recorded.
    # In that case, preserve the failed test-stage status in the final report.
    overall_status = "failed" if failed > 0 or test_step_outcome != "success" else "passed"
    pipeline_error = None
    if test_step_outcome != "success" and failed == 0:
        pipeline_error = (
            "The pytest step did not finish successfully. Check the CI log for "
            "collection, setup, or environment errors."
        )

    repository = os.environ.get("GITHUB_REPOSITORY", "local/assignment-portal")
    run_id = os.environ.get("GITHUB_RUN_ID", "local-run")
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    run_url = f"{server_url}/{repository}/actions/runs/{run_id}" if run_id != "local-run" else None

    report = {
        "repository": repository,
        "branch": os.environ.get("GITHUB_REF_NAME", os.environ.get("BRANCH", "local")),
        "commit_sha": os.environ.get("GITHUB_SHA", os.environ.get("COMMIT_SHA", "local")),
        "pipeline_run_id": run_id,
        "pipeline_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
        "pipeline_run_url": run_url,
        "execution_timestamp": datetime.now(timezone.utc).isoformat(),
        "tests": tests,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "overall_status": overall_status,
        },
        "test_step_outcome": test_step_outcome,
        "pipeline_error": pipeline_error,
    }

    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
