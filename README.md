# COMSATS CSC418 — DevOps Assignment Submission Portal

A Flask + SQLite assignment portal with automated Pytest checks, GitHub Actions CI, an authenticated local JSON report receiver, optional SMTP email reports, and conditional GitHub Pages deployment.

## 1. Requirements

- Python 3.10 or newer (the GitHub workflow uses Python 3.12)
- Git and a GitHub account
- `cloudflared` for the local report receiver tunnel
- A computer that stays online during the CI demonstration

## 2. Project structure

```text
.
├── app.py
├── requirements.txt
├── templates/index.html
├── static/style.css
├── tests/
│   ├── conftest.py
│   └── test_portal.py
├── scripts/
│   ├── build_report.py
│   └── send_email.py
├── receiver/receiver.py
├── docs/index.html
└── .github/workflows/ci.yml
```

## 3. Run the portal locally

### Windows PowerShell

```powershell
cd devops-assignment-portal
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

### macOS / Linux

```bash
cd devops-assignment-portal
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. Fill in all four fields and submit a valid `https://` or `http://` link. The Flask app stores submissions in `instance/submissions.sqlite3` and displays saved records on the page.

## 4. Run automated tests locally

```bash
python -m pytest -q
```

The tests cover:

1. A complete submission with a valid URL is saved and displayed.
2. A missing registration number is rejected and is not saved.
3. An invalid URL is rejected and is not saved.
4. An additional missing-assignment-title validation test.

The Pytest hook in `tests/conftest.py` records actual outcomes (including failure messages) in `test-results.json` even when a test fails. To build the same report format locally:

```bash
python scripts/build_report.py
```

The resulting `testreport.json` is a local test report; GitHub Actions creates a new report containing the actual GitHub repository, branch, commit, run ID, and execution time.

## 5. Start the local HTTP report receiver

The receiver saves incoming reports to `testreport.json` in its current working directory. It requires a secret bearer token. Generate a strong token with `python -c "import secrets; print(secrets.token_urlsafe(32))"`, then use the same value in the receiver terminal and the GitHub secret.

### Windows PowerShell — terminal 1

Open a second terminal in the project folder and run:

```powershell
$env:REPORT_RECEIVER_TOKEN = "replace-this-with-a-long-random-secret"
$env:REPORT_FILE = "$PWD\testreport.json"
python receiver/receiver.py
```

### macOS / Linux — terminal 1

```bash
export REPORT_RECEIVER_TOKEN='replace-this-with-a-long-random-secret'
export REPORT_FILE="$PWD/testreport.json"
python receiver/receiver.py
```

The receiver listens on `127.0.0.1:5001` (localhost only). Check it locally at <http://127.0.0.1:5001/health>. Keep this terminal running.

**Security:** use a long random token, keep it private, and do not commit it to Git. The receiver authenticates every report using `Authorization: Bearer <token>`.

## 6. Expose the receiver with Cloudflare Quick Tunnel

Install `cloudflared` from the official Cloudflare installation instructions. In terminal 2, run:

```bash
cloudflared tunnel --url http://localhost:5001
```

Cloudflare prints a temporary address similar to:

```text
https://random-words.trycloudflare.com
```

Your GitHub Actions receiver URL must include `/report`, for example:

```text
https://random-words.trycloudflare.com/report
```

Keep both the receiver and tunnel terminals running during every push/test demonstration. Quick Tunnel addresses change when the tunnel is restarted, so update the GitHub secret if the URL changes. Quick Tunnels are intended for temporary testing, not production hosting.

## 7. Create the GitHub repository and push the project

1. On GitHub, create a new repository named `comsats-devops-assignment-portal` (or another name you prefer).
2. Do not initialize it with a README if you already have this project locally.
3. In a terminal opened in this project folder, run:

```bash
git init
git add .
git commit -m "Initial assignment portal with tests and CI"
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/comsats-devops-assignment-portal.git
git push -u origin main
```

Replace `YOUR_GITHUB_USERNAME` with your GitHub username. The `push` event automatically starts `.github/workflows/ci.yml`.

## 8. Configure the mandatory GitHub Actions secrets

In your GitHub repository:

1. Open **Settings → Secrets and variables → Actions**.
2. Select **New repository secret**.
3. Add these two secrets:

| Secret name | Value |
|---|---|
| `REPORT_RECEIVER_URL` | Your current Cloudflare URL ending in `/report` |
| `REPORT_RECEIVER_TOKEN` | Exactly the same token used in the receiver terminal |

Do not put the token directly in the workflow YAML or source code.

## 9. Understand the CI workflow

For every push to every branch, GitHub Actions runs three jobs:

1. **`test` job:** checks out the pushed commit, installs Python/dependencies, and runs `pytest -q`. The pytest step is a normal failing step: a failed test makes this job red. A `pytest_sessionfinish` hook writes the actual test results, and an `if: always()` step builds `testreport.json` even when pytest fails. The report is uploaded as a short-lived workflow artifact.
2. **`report` job:** runs with `if: always()` and downloads the report artifact even if the `test` job failed. It sends the JSON to your local receiver using an authenticated HTTP POST and optionally emails the report.
3. **`deploy-pages` job:** runs only for a push to `main` when the automated test job succeeded. A report-receiver outage does not change the test result or deployment eligibility.

This separation is important: the actual test stage fails normally, but the independent report job still runs after a failing test. The report is not a GitHub push notification; it contains the per-test results captured by pytest.

To see the report, open the `testreport.json` file in your project folder on your own computer. It is overwritten with the latest run. You can also inspect the receiver terminal for the saved run ID and status.

## 10. Demonstrate passing, failing, and corrected runs

Keep the receiver and tunnel running for all three demonstrations.

### A. Passing run

Run the tests locally first:

```bash
python -m pytest -q
```

Then push your current working code:

```bash
git add .
git commit -m "Demonstrate passing CI tests"
git push
```

Expected: all tests pass, the Actions job is green, and the local `testreport.json` shows `overall_status: "passed"` and `failed: 0`.

### B. Intentionally introduce a defect

For a safe demonstration, temporarily break URL validation in `app.py`. Find this condition:

```python
if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc or not hostname:
    return False
```

Temporarily change it to:

```python
if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc or not hostname:
    return True  # INTENTIONAL BUG FOR CI DEMONSTRATION
```

Now the invalid-URL test should fail because the application incorrectly accepts a `javascript:` URL. Commit and push the defect:

```bash
git add app.py
git commit -m "Demonstrate failing CI with URL validation defect"
git push
```

Expected: the invalid URL test fails, the Actions job is red, but the local receiver still receives a report showing a failed test, a failure message, and `overall_status: "failed"`.

### C. Fix the defect

Restore the correct condition:

```python
if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc or not hostname:
    return False
```

Then push the fix:

```bash
git add app.py
git commit -m "Fix URL validation and restore passing CI"
git push
```

Expected: tests pass again, the Actions job is green, and `testreport.json` is automatically updated with the corrected passing run.

**Evidence to capture:** GitHub Actions summary for each of the three commits, the test log showing pass/fail, and the local `testreport.json` after each run. Save copies/screenshots before the next run overwrites the JSON file.

## 11. Bonus 1 — Conditional GitHub Pages deployment

The workflow includes a separate `deploy-pages` job. It runs only when:

- the event is a push to `main`; and
- the automated test job succeeds. The report-delivery job may fail independently without changing the test outcome.

The deployed content is the static demo in `docs/index.html`. It uses browser local storage because GitHub Pages serves static files and cannot run the Flask/SQLite backend. The full server-backed portal remains the locally run Flask application.

To enable Pages:

1. Open repository **Settings → Pages**.
2. Under **Build and deployment → Source**, select **GitHub Actions**.
3. Push a passing commit to `main`.
4. Open the Pages deployment job in the Actions tab and copy the published URL.

Typical URL format:

```text
https://YOUR_GITHUB_USERNAME.github.io/REPOSITORY_NAME/
```

The exact URL depends on your GitHub username and repository name. A failing test prevents the deployment job from running, leaving the previously published version unchanged.

## 12. Bonus 2 — Email test report

The workflow includes an optional email step. If `MAIL_TO` is not configured, it skips the email. To enable it, add these repository Actions secrets:

| Secret | Purpose |
|---|---|
| `MAIL_HOST` | SMTP server hostname |
| `MAIL_PORT` | SMTP port, usually `587` for STARTTLS or `465` for SSL |
| `MAIL_USERNAME` | SMTP account username |
| `MAIL_PASSWORD` | SMTP password or provider-specific app password |
| `MAIL_FROM` | Sender email address |
| `MAIL_TO` | Recipient email address |
| `MAIL_USE_SSL` | `false` for port 587 STARTTLS; `true` for port 465 SSL |

The email contains the commit, overall result, counts, individual test results, and the JSON report as an attachment. For Gmail, use an app password where supported; do not use your normal account password. The email step runs after both passing and failing tests. It is marked `continue-on-error` so an email-provider outage does not hide the actual test result or prevent a successful Pages deployment.

## 13. Troubleshooting

- **GitHub run says receiver secrets are missing:** add `REPORT_RECEIVER_URL` and `REPORT_RECEIVER_TOKEN` under repository Actions secrets.
- **Receiver returns 401:** the token in the receiver terminal and GitHub secret do not match. Set both to the same value.
- **Receiver cannot be reached:** confirm the Flask receiver and `cloudflared` are still running, and verify the URL ends with `/report`.
- **Cloudflare URL changed:** restart the Quick Tunnel, copy its new URL, and update `REPORT_RECEIVER_URL` in GitHub secrets.
- **Tests pass locally but fail on GitHub:** open the Actions log and inspect the first traceback. Confirm `requirements.txt` is committed.
- **Pages does not deploy:** confirm Pages source is set to GitHub Actions and the push was to `main` with a successful test job.
- **Email is skipped:** configure `MAIL_TO`. If email is attempted but fails, inspect the optional email step log and check SMTP host, port, credentials, and provider security requirements.

## 14. What to submit to the instructor

- GitHub repository URL.
- Setup and run instructions (this README).
- Screenshot/evidence of the passing test run.
- Screenshot/evidence of the intentionally failing test run.
- Screenshot/evidence of the corrected passing run.
- Local `testreport.json` evidence for all three runs (save each version before it is overwritten).
- GitHub Pages URL if attempting the deployment bonus.
- Received email screenshot if attempting the email bonus.

---

**Security and academic note:** use your own GitHub account, add your own student details, perform the three actual pushes, and capture evidence from your own Actions runs and local receiver. Do not submit fabricated pipeline screenshots or reports.
