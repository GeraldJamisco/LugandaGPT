"""Command line checks for benchmark records.

The CLI only reads local files. It never downloads data, calls a model, or
contacts a review service.
"""

import argparse
import sys

from .errors import BenchmarkError
from .item import category_counts
from .runs import RunManifest
from .storage import read_json, sha256_file
from .versioning import read_manifest, load_approved_benchmark, load_item_file


def _optional_mapping(path, label):
    if not path:
        return None
    value = read_json(path)
    if not isinstance(value, dict):
        raise BenchmarkError(f"{label} must be a JSON object")
    return value


def _validate(args):
    evidence = _optional_mapping(args.evidence, "evidence")
    source_exceptions = _optional_mapping(args.source_exceptions, "source exceptions")
    items = load_item_file(
        args.items,
        expected_version=args.version,
        evidence_by_id=evidence,
        source_exceptions=source_exceptions,
    )
    counts = category_counts(items)
    print(f"OK: {len(items)} item(s) validated for {args.version}")
    for category, count in counts.items():
        if count:
            print(f"  {category}: {count}")
    if args.manifest:
        manifest = read_manifest(args.manifest)
        if manifest.version != args.version:
            raise BenchmarkError(
                f"manifest version {manifest.version} does not match {args.version}"
            )
        if manifest.status == "approved":
            load_approved_benchmark(
                args.items,
                args.manifest,
                evidence_by_id=evidence,
                source_exceptions=source_exceptions,
            )
            print("Approved benchmark verified against its manifest and approval record.")
        else:
            actual = sha256_file(args.items)
            if actual != manifest.item_file_sha256:
                raise BenchmarkError("item file hash does not match the manifest")
            print(f"Manifest status: {manifest.status}")
    return 0


def _validate_run(args):
    value = read_json(args.manifest)
    manifest = RunManifest.from_dict(value)
    print(f"Run {manifest.run_id}: {manifest.run_status}")
    print(f"Manifest SHA-256: {manifest.manifest_sha256()}")
    if manifest.run_status in ("failed", "incomplete"):
        print("This run is not a completed evaluation.", file=sys.stderr)
        return 2
    return 0


def _hash(args):
    print(sha256_file(args.items))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="python -m benchmark")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate a benchmark item file")
    validate.add_argument("items", help="path to an item JSONL file")
    validate.add_argument("--version", required=True, help="expected benchmark version")
    validate.add_argument("--manifest", help="optional benchmark manifest to check")
    validate.add_argument(
        "--evidence",
        help="JSON object mapping item IDs to review evidence records",
    )
    validate.add_argument(
        "--source-exceptions",
        help="JSON object mapping item IDs to owner source exceptions",
    )
    validate.set_defaults(func=_validate)

    validate_run = subparsers.add_parser(
        "validate-run", help="validate an evaluation run manifest"
    )
    validate_run.add_argument("manifest", help="path to run_manifest.json")
    validate_run.set_defaults(func=_validate_run)

    hash_file = subparsers.add_parser("hash", help="print an item file SHA-256")
    hash_file.add_argument("items", help="path to an item JSONL file")
    hash_file.set_defaults(func=_hash)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except BenchmarkError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
