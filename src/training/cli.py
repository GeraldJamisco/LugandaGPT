"""Command line tools for the English source draft.

The Gemma 1B training, inference, and Runpod commands that used to live here
were archived on 2026-11-02 (see archive/2026-11-02-gemma-runpod-reporter/).
Only the source-draft commands that the Translation Studio depends on remain.
"""

import argparse
import json
import sys
from pathlib import Path

from .errors import TrainingError
from .source_pilot import (
    load_source_draft,
    validate_source_exports,
    write_source_exports,
)
from .storage import sha256_file

DEFAULT_SOURCE_DRAFT = "data/source/pilot-v1/source_draft.json"


def _print(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _validate_source(args):
    loaded = load_source_draft(args.path)
    exports = validate_source_exports(loaded, Path(args.path).parent)
    _print(
        {
            "status": "source_draft_valid",
            "path": str(loaded["path"]),
            "sha256": loaded["sha256"],
            "dataset_status": loaded["summary"]["status"],
            "pilot_count": loaded["summary"]["pilot_count"],
            "evaluation_count": loaded["summary"]["evaluation_count"],
            "capability_counts": loaded["summary"]["capability_counts"],
            "pilot_split_counts": loaded["summary"]["pilot_split_counts"],
            "composition": {
                "multi_sentence": loaded["summary"]["multi_sentence"],
                "uncertainty_cases": loaded["summary"]["uncertainty_cases"],
                "constraint_examples": loaded["summary"]["constraint_examples"],
                "prior_context_conversations": loaded["summary"][
                    "prior_context_conversations"
                ],
            },
            "translation_status_counts": loaded["summary"][
                "translation_status_counts"
            ],
            "native_review_status_counts": loaded["summary"][
                "native_review_status_counts"
            ],
            "training_authorized": False,
            "training_blocker": loaded["summary"]["training_blocker"],
            "exports": exports,
        }
    )
    return 0


def _export_source(args):
    loaded = load_source_draft(args.path)
    output = Path(args.output_dir) if args.output_dir else Path(args.path).parent
    manifest = write_source_exports(loaded, output)
    _print(
        {
            "status": "source_exports_written",
            "output_dir": str(output.resolve()),
            "pilot_count": manifest["pilot_count"],
            "evaluation_count": manifest["evaluation_count"],
            "translator_rows": manifest["pilot_count"]
            + manifest["evaluation_count"],
            "training_authorized": False,
        }
    )
    return 0


def _hash_file(args):
    path = Path(args.path)
    if not path.is_file():
        raise TrainingError(f"file not found: {path}")
    _print({"path": str(path), "sha256": sha256_file(path), "size": path.stat().st_size})
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m training",
        description="LugandaGPT source-draft tools.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_source = subparsers.add_parser(
        "validate-source",
        help="validate the English source draft and translator exports",
    )
    validate_source.add_argument("path", nargs="?", default=DEFAULT_SOURCE_DRAFT)
    validate_source.set_defaults(handler=_validate_source)

    export_source = subparsers.add_parser(
        "export-source",
        help="write JSONL, translator CSV, and a source manifest",
    )
    export_source.add_argument("path", nargs="?", default=DEFAULT_SOURCE_DRAFT)
    export_source.add_argument("--output-dir")
    export_source.set_defaults(handler=_export_source)

    hash_file = subparsers.add_parser("hash", help="print a local file SHA-256")
    hash_file.add_argument("path")
    hash_file.set_defaults(handler=_hash_file)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except TrainingError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
