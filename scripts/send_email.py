"""Optional SMTP email sender for the CI test report."""

import json
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


def main() -> None:
    recipient = os.environ.get("MAIL_TO", "").strip()
    if not recipient:
        print("MAIL_TO is not configured; skipping optional email report.")
        return

    host = os.environ.get("MAIL_HOST", "").strip()
    sender = os.environ.get("MAIL_FROM", os.environ.get("MAIL_USERNAME", "")).strip()
    if not host or not sender:
        raise SystemExit("MAIL_TO is set, but MAIL_HOST or MAIL_FROM is missing.")

    report_path = Path("testreport.json")
    if not report_path.exists():
        raise SystemExit("testreport.json does not exist; cannot send email.")

    report_bytes = report_path.read_bytes()
    report = json.loads(report_bytes)
    summary = report["summary"]
    status = summary["overall_status"].upper()
    sha = report.get("commit_sha", "unknown")

    message = EmailMessage()
    message["Subject"] = f"[DevOps CI] {status} - {report.get('repository')} - {sha[:8]}"
    message["From"] = sender
    message["To"] = recipient

    lines = [
        "COMSATS CSC418 DevOps test report",
        f"Repository: {report.get('repository')}",
        f"Branch: {report.get('branch')}",
        f"Commit: {sha}",
        f"Pipeline run: {report.get('pipeline_run_id')}",
        f"Overall status: {status}",
        f"Total: {summary.get('total', 0)} | Passed: {summary.get('passed', 0)} | Failed: {summary.get('failed', 0)} | Skipped: {summary.get('skipped', 0)}",
        "",
        "Individual tests:",
    ]
    for test in report.get("tests", []):
        lines.append(f"- {test.get('name')}: {test.get('result')}")
        if test.get("failure_message"):
            lines.append(f"  Failure: {test['failure_message']}")
    message.set_content("\n".join(lines))
    message.add_attachment(
        report_bytes,
        maintype="application",
        subtype="json",
        filename="testreport.json",
    )

    port = int(os.environ.get("MAIL_PORT", "587"))
    username = os.environ.get("MAIL_USERNAME", "")
    password = os.environ.get("MAIL_PASSWORD", "")
    use_ssl = os.environ.get("MAIL_USE_SSL", "false").lower() == "true"

    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)

    print(f"Email report sent to {recipient}.")


if __name__ == "__main__":
    main()
