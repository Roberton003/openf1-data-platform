import json
import logging
import os
import smtplib
import subprocess
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from src.web.config import settings

# Setup logging
ALERTS_DIR = os.path.join(settings.BASE_DIR, "data/alerts")
os.makedirs(ALERTS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(ALERTS_DIR, "ci_alerts.log")),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("ci_monitor")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def fetch_github_api(url: str, token: str = None) -> dict:
    """Fetches data from the GitHub API with exponential backoff retry."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "OpenF1-CI-Monitor",
    }
    if token and token.strip():
        headers["Authorization"] = f"Bearer {token.strip()}"

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()


def get_latest_runs(repo: str, token: str = None) -> list:
    """Retrieves the list of workflow runs from GitHub."""
    url = f"https://api.github.com/repos/{repo}/actions/runs"
    try:
        data = fetch_github_api(url, token)
        return data.get("workflow_runs", [])
    except Exception as e:
        logger.error(f"Error fetching workflow runs from GitHub Actions API: {e}")
        return []


def get_run_jobs(repo: str, run_id: int, token: str = None) -> list:
    """Retrieves the list of jobs for a specific workflow run."""
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs"
    try:
        data = fetch_github_api(url, token)
        return data.get("jobs", [])
    except Exception as e:
        logger.error(
            f"Error fetching jobs for run {run_id} from GitHub Actions API: {e}"
        )
        return []


def notify_local(workflow_name: str, conclusion: str, run_id: int):
    """Sends a desktop notification on Linux or falls back to system logs."""
    message = (
        f"Workflow '{workflow_name}' failed with status: {conclusion} (ID: {run_id})"
    )
    logger.warning(f"[CI ALERT] {message}")

    try:
        # Use notify-send for native desktop notification on Linux
        subprocess.run(
            [
                "notify-send",
                "CI/CD Alert - OpenF1",
                message,
                "-u",
                "critical",
                "-i",
                "dialog-error",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("Local GUI notification sent successfully.")
    except Exception as e:
        # Fallback if notify-send or desktop environment is missing
        logger.info(
            f"Local GUI notification skipped or unavailable (headless environment). Reason: {e}"
        )


def send_alert_email(
    run_id: int,
    workflow_name: str,
    conclusion: str,
    commit_sha: str,
    failed_steps: list,
) -> dict:
    """Dispatches email alert via SMTP or logs Mock Email if credentials are missing."""
    subject = f"[OpenF1 Alert] CI/CD Pipeline Failure: {workflow_name} (Run #{run_id})"
    body = (
        f"A CI/CD Pipeline failure was detected in your repository.\n\n"
        f"Repository: {settings.GITHUB_REPO}\n"
        f"Workflow Name: {workflow_name}\n"
        f"Run ID: {run_id}\n"
        f"Conclusion: {conclusion}\n"
        f"Commit SHA: {commit_sha}\n"
        f"Failed Steps: {', '.join(failed_steps) if failed_steps else 'Unknown'}\n"
        f"Alert Time: {datetime.now().isoformat()}\n\n"
        f"This is an automated alert from OpenF1 Monitoring Service.\n"
    )

    # Check if we have valid SMTP configuration
    has_smtp = all(
        [
            settings.SMTP_HOST,
            settings.SMTP_USER,
            settings.SMTP_PASSWORD,
            settings.ALERT_EMAIL_RECEIVER,
        ]
    )

    result = {
        "sent": False,
        "mode": "SMTP" if has_smtp else "MOCK",
        "recipient": settings.ALERT_EMAIL_RECEIVER or "developer@local",
        "file_path": None,
    }

    if has_smtp:
        try:
            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
            msg["To"] = settings.ALERT_EMAIL_RECEIVER
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(msg["From"], msg["To"], msg.as_string())

            logger.info(
                f"Alert email sent successfully to {settings.ALERT_EMAIL_RECEIVER}."
            )
            result["sent"] = True
        except Exception as e:
            logger.error(f"SMTP sending failed, falling back to local file. Error: {e}")
            # Fall back to writing mock email on failure
            result["mode"] = "MOCK_FALLBACK"

    if not result["sent"]:
        logger.info("SMTP credentials are not configured. Email alert skipped.")

    return result


def execute_healing_action(failed_steps: list, run_id: int) -> list:
    """Executes corresponding local corrective actions based on failed pipeline steps."""
    actions_taken = []

    # We normalized checks to search in failed steps
    has_format_fail = False
    has_lint_fail = False
    has_test_fail = False

    if failed_steps:
        for step in failed_steps:
            step_lower = step.lower()
            if "black" in step_lower or "format" in step_lower or "isort" in step_lower:
                has_format_fail = True
            if "flake8" in step_lower or "lint" in step_lower or "static" in step_lower:
                has_lint_fail = True
            if "pytest" in step_lower or "test" in step_lower:
                has_test_fail = True
    else:
        # Defensively assume all checks should run if we couldn't parse specific steps
        has_format_fail = True
        has_lint_fail = True
        has_test_fail = True

    # 1. Format healing: Run 'make format'
    if has_format_fail:
        logger.info(
            "Triggering Auto-Healing: format issue detected. Running 'make format'..."
        )
        try:
            res = subprocess.run(
                ["make", "format"],
                cwd=settings.BASE_DIR,
                capture_output=True,
                text=True,
            )
            actions_taken.append(
                {
                    "action": "make format",
                    "status": "success" if res.returncode == 0 else "failed",
                    "stdout": res.stdout,
                    "stderr": res.stderr,
                }
            )
            logger.info(
                f"Auto-Healing: 'make format' completed with exit code {res.returncode}"
            )
        except Exception as e:
            logger.error(f"Failed to run 'make format': {e}")
            actions_taken.append(
                {"action": "make format", "status": "error", "error": str(e)}
            )

    # 2. Lint healing: Run 'make lint' and log results
    if has_lint_fail:
        logger.info(
            "Triggering Auto-Healing: lint issue detected. Logging 'make lint'..."
        )
        try:
            res = subprocess.run(
                ["make", "lint"], cwd=settings.BASE_DIR, capture_output=True, text=True
            )
            lint_file = os.path.join(ALERTS_DIR, f"flake8_errors_{run_id}.txt")
            with open(lint_file, "w", encoding="utf-8") as f:
                f.write(f"Flake8 execution logs for Run {run_id}:\n")
                f.write(f"Return Code: {res.returncode}\n")
                f.write("-" * 50 + "\n")
                f.write(res.stdout or "")
                f.write(res.stderr or "")
            actions_taken.append(
                {"action": "make lint", "status": "logged", "file_path": lint_file}
            )
            logger.info(f"Auto-Healing: 'make lint' logged to {lint_file}")
        except Exception as e:
            logger.error(f"Failed to run 'make lint': {e}")
            actions_taken.append(
                {"action": "make lint", "status": "error", "error": str(e)}
            )

    # 3. Test healing: Run 'make test' and log traceback details
    if has_test_fail:
        logger.info(
            "Triggering Auto-Healing: test issue detected. Logging failing tracebacks..."
        )
        try:
            res = subprocess.run(
                ["make", "test"], cwd=settings.BASE_DIR, capture_output=True, text=True
            )
            test_file = os.path.join(ALERTS_DIR, f"pytest_errors_{run_id}.txt")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(f"Pytest execution tracebacks for Run {run_id}:\n")
                f.write(f"Return Code: {res.returncode}\n")
                f.write("-" * 50 + "\n")
                f.write(res.stdout or "")
                f.write(res.stderr or "")
            actions_taken.append(
                {"action": "make test", "status": "logged", "file_path": test_file}
            )
            logger.info(f"Auto-Healing: 'make test' logged to {test_file}")
        except Exception as e:
            logger.error(f"Failed to run 'make test': {e}")
            actions_taken.append(
                {"action": "make test", "status": "error", "error": str(e)}
            )

    return actions_taken


def check_and_heal_ci(target_run_id: int = None) -> dict:
    """Checks the status of the latest run or a specific target run, and executes alerts/healing."""
    logger.info("Starting CI/CD pipeline health check...")
    repo = settings.GITHUB_REPO
    token = settings.GITHUB_TOKEN

    runs = get_latest_runs(repo, token)
    if not runs:
        logger.warning("No workflow runs retrieved. Exiting health check.")
        return {"status": "error", "message": "No workflow runs found"}

    # Select the target run
    selected_run = None
    if target_run_id:
        for r in runs:
            if r.get("id") == target_run_id:
                selected_run = r
                break
        if not selected_run:
            logger.warning(
                f"Target Run ID {target_run_id} not found in retrieved list. Defaulting to latest."
            )

    if not selected_run:
        selected_run = runs[0]

    run_id = selected_run.get("id")
    workflow_name = selected_run.get("name", "Unknown Workflow")
    status = selected_run.get("status")
    conclusion = selected_run.get("conclusion")
    commit_sha = selected_run.get("head_sha", "Unknown")

    logger.info(
        f"Latest run evaluated: ID={run_id}, Name={workflow_name}, Status={status}, Conclusion={conclusion}"
    )

    report = {
        "evaluated_run_id": run_id,
        "workflow_name": workflow_name,
        "status": status,
        "conclusion": conclusion,
        "commit_sha": commit_sha,
        "alert_triggered": False,
        "auto_healing_executed": False,
        "actions": [],
    }

    # We trigger alerts only if the status is completed and conclusion is in failure, timed_out, cancelled
    is_failed = conclusion in ["failure", "timed_out", "cancelled"]

    if status == "completed" and is_failed:
        logger.warning(f"Pipeline failure detected on Run {run_id}!")
        report["alert_triggered"] = True

        # 1. Fetch failing steps
        failed_steps = []
        jobs = get_run_jobs(repo, run_id, token)
        for job in jobs:
            for step in job.get("steps", []):
                if step.get("conclusion") == "failure":
                    failed_steps.append(step.get("name", "Unknown Step"))

        # 2. Local desktop notification
        notify_local(workflow_name, conclusion, run_id)

        # 3. Send email alert
        email_info = send_alert_email(
            run_id, workflow_name, conclusion, commit_sha, failed_steps
        )
        report["email_alert"] = email_info

        # 4. Auto-Healing
        if settings.AUTO_HEAL_CI:
            logger.info(
                f"Auto-healing is enabled. Starting corrective actions for Run {run_id}..."
            )
            actions = execute_healing_action(failed_steps, run_id)
            report["auto_healing_executed"] = True
            report["actions"] = actions

            # Save the final consolidated healing report
            report_file = os.path.join(ALERTS_DIR, f"ci_healing_report_{run_id}.json")
            try:
                with open(report_file, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=4, default=str)
                logger.info(f"Consolidated healing report written to {report_file}")
            except Exception as e:
                logger.error(f"Failed to write consolidated healing report: {e}")
        else:
            logger.info("Auto-healing is disabled by configuration.")
    else:
        logger.info(
            f"Pipeline status is '{status}' with conclusion '{conclusion}'. No alerts triggered."
        )

    return report
