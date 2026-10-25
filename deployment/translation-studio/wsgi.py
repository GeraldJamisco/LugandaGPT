"""WSGI entry point for the LugandaGPT Translation Studio deployment."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from translation_studio.app import create_app

DB_PATH = ROOT / "data" / "studio" / "studio.sqlite3"
EXPORT_DIR = ROOT / "data" / "exports"
SOURCE_PATH = Path(
    os.environ.get(
        "STUDIO_SOURCE",
        str(ROOT / "data" / "source" / "pilot-v1" / "source_draft.json"),
    )
)

application = create_app(
    db_path=str(DB_PATH),
    source_path=str(SOURCE_PATH),
    export_dir=str(EXPORT_DIR),
)
