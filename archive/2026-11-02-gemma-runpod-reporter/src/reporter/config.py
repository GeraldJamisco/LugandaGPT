"""Local paths, environment variables and defaults for the reporter.

Credentials are read from the process environment only. Nothing in this
file holds a secret, and no configuration file holding secrets is written
into this repository.
"""

from datetime import timedelta, timezone
from pathlib import Path

# Layout: src/reporter/config.py -> src -> repository root.
PACKAGE_DIR = Path(__file__).resolve().parent
SRC_DIR = PACKAGE_DIR.parent
REPO_ROOT = SRC_DIR.parent

DOCS_DIR = REPO_ROOT / "docs"
GIT_DIR = REPO_ROOT

# Reporting runs on East Africa Time, the project's home time zone. EAT is
# UTC+3 all year with no daylight saving, so a fixed offset is exact and
# needs no time-zone database on Windows.
REPORT_TZ = timezone(timedelta(hours=3), "EAT")
REPORT_TZ_NAME = "EAT (Africa/Kampala, UTC+3)"

# Scheduled report slots in EAT: three per day, eight hours apart.
SCHEDULE_HOURS_EAT = (6, 14, 22)

REPORTS_ROOT = REPO_ROOT / "reports" / "reporter"
ARCHIVE_DIR = REPORTS_ROOT / "archive"
TEST_RUNS_DIR = REPORTS_ROOT / "test_runs"
STATE_FILE = REPORTS_ROOT / "state.json"
HUMAN_ACTIVITY_FILE = REPORTS_ROOT / "human_activity.json"
API_USAGE_FILE = REPORTS_ROOT / "api_usage.json"
EXIT_CRITERIA_FILE = REPORTS_ROOT / "exit_criteria_verification.json"
DELIVERY_LOG = REPORTS_ROOT / "delivery.log"
PID_FILE = REPORTS_ROOT / "server.pid"

STATIC_DIR = PACKAGE_DIR / "static"
STATIC_FILES = ("index.html", "style.css", "app.js")

EXPERIMENT_LOG = DOCS_DIR / "EXPERIMENT_LOG.md"
ROADMAP_FILE = DOCS_DIR / "ROADMAP.md"
DECISIONS_FILE = DOCS_DIR / "DECISIONS.md"

# Environment variables. A username is not a chat id; both values must be
# supplied by the owner on this machine.
TOKEN_ENV = "LUGANDAGPT_TELEGRAM_BOT_TOKEN"
CHAT_ENV = "LUGANDAGPT_TELEGRAM_CHAT_ID"
BOT_USERNAME = "LugandaGPT_Proj_Reporter_bot"

DEFAULT_INTERVAL_HOURS = 8
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

TELEGRAM_API = "https://api.telegram.org"
TELEGRAM_MESSAGE_LIMIT = 4096
HTTP_TIMEOUT_SECONDS = 15
MAX_POST_BODY_BYTES = 4096

# Paths are exposed to the dashboard only as report ids, never as raw
# filesystem paths.
def ensure_dirs() -> None:
    """Create the local output directories. Never touches project code."""
    for path in (REPORTS_ROOT, ARCHIVE_DIR, TEST_RUNS_DIR):
        path.mkdir(parents=True, exist_ok=True)
