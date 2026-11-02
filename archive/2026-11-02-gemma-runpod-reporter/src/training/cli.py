"""Local-first command line interface for training preparation.

Commands that could spend money or load the model require a config that is
explicitly approved for execution. There are no flags that skip authorization,
data checks, preflight, or the step and runtime caps.
"""

import argparse
import json
import sys
from pathlib import Path

from .artifacts import (
    record_final_cost,
    verify_artifact_inventory,
)
from .config import load_config
from .data import load_pilot_dataset
from .errors import TrainingError
from .inference import run_inference
from .modeling import load_tokenizer
from .runner import preflight as run_preflight
from .runner import run_training
from .source_pilot import (
    load_source_draft,
    validate_source_exports,
    write_source_exports,
)
from .storage import sha256_file

DEFAULT_SOURCE_DRAFT = "data/source/pilot-v1/source_draft.json"


def _print(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _validate_config(args):
    loaded = load_config(args.config, project_root=args.project_root)
    _print(
        {
            "status": "config_valid",
            "config_sha256": loaded.sha256,
            "experiment_id": loaded["experiment"]["id"],
            "execution_authorized": loaded["experiment"]["execution_authorized"],
            "authorization_status": loaded["experiment"]["authorization_status"],
            "base_model": loaded["base_model"]["id"],
            "base_revision": loaded["base_model"]["revision"],
            "lora": {
                "r": loaded["lora"]["r"],
                "expected_trainable_parameters": loaded["lora"][
                    "expected_trainable_parameters"
                ],
            },
            "dataset_version": loaded["dataset"]["version"],
            "dependencies": loaded["dependencies"],
            "next": "validate-data, then preflight, then train after approval",
        }
    )
    return 0


def _validate_data(args):
    loaded = load_config(args.config, project_root=args.project_root)
    tokenizer = None
    tokenizer_source = args.tokenizer_path or args.model_path
    if tokenizer_source:
        tokenizer = load_tokenizer(
            loaded,
            model_path=tokenizer_source,
            local_files_only=True,
        )
    dataset = load_pilot_dataset(
        loaded,
        project_root=args.project_root,
        require_complete=not args.allow_incomplete,
        require_approved=not args.allow_draft,
        tokenizer=tokenizer,
        require_token_checks=args.require_tokenizer,
    )
    _print(
        {
            "status": "data_valid",
            "config_sha256": loaded.sha256,
            "dataset_version": loaded["dataset"]["version"],
            "reviewed": dataset.summary["reviewed"],
            "counts": dataset.summary["counts"],
            "capability_counts": dataset.summary["capability_counts"],
            "audit": dataset.summary["audit"],
            "contamination": dataset.summary["contamination"],
            "token_checks": dataset.summary["token_checks"],
            "hashes": dataset.hashes,
            "provenance_sha256": dataset.provenance_sha256,
        }
    )
    return 0


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


def _preflight(args):
    result = run_preflight(
        args.config,
        project_root=args.project_root,
        tokenizer_path=args.tokenizer_path,
        model_path=args.model_path,
    )
    _print(result)
    return 0


def _train(args):
    output = run_training(
        args.config,
        project_root=args.project_root,
        model_path=args.model_path,
        tokenizer_path=args.tokenizer_path,
        output_dir=args.output_dir,
        pod_id=args.pod_id,
        region=args.region,
        host=args.host,
        image=args.image,
        resume_from_checkpoint=args.resume_from_checkpoint,
    )
    _print(
        {
            "status": "training_completed",
            "run_dir": str(output),
            "next": "verify-artifacts, export, record-cost, then terminate the Pod",
        }
    )
    return 0


def _infer(args):
    output = run_inference(
        args.config,
        run_dir=args.run_dir,
        new_adapter=args.new_adapter,
        existing_adapter=args.existing_adapter,
        project_root=args.project_root,
        model_path=args.model_path,
        tokenizer_path=args.tokenizer_path,
    )
    _print({"status": "inference_completed", "inference_dir": str(output)})
    return 0


def _verify_artifacts(args):
    verify_artifact_inventory(args.run_dir)
    _print({"status": "artifacts_verified", "run_dir": str(Path(args.run_dir).resolve())})
    return 0


def _record_cost(args):
    record = record_final_cost(
        args.run_dir,
        final_credit_charge_usd=args.final_credit_charge,
        final_cash_charge_usd=args.final_cash_charge,
        remaining_credit_usd=args.remaining_credit,
        sales_tax_usd=args.sales_tax,
        payment_fee_usd=args.payment_fee,
        notes=args.notes,
    )
    _print({"status": "cost_recorded", "cost": record})
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
        description="LugandaGPT training preparation and guarded smoke-test tools.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_config = subparsers.add_parser(
        "validate-config", help="validate the YAML configuration only"
    )
    validate_config.add_argument("config")
    validate_config.add_argument("--project-root")
    validate_config.set_defaults(handler=_validate_config)

    validate_data = subparsers.add_parser(
        "validate-data", help="validate pilot, evaluation, provenance, and contamination"
    )
    validate_data.add_argument("config")
    validate_data.add_argument("--project-root")
    validate_data.add_argument("--tokenizer-path")
    validate_data.add_argument("--model-path")
    validate_data.add_argument("--allow-incomplete", action="store_true")
    validate_data.add_argument("--allow-draft", action="store_true")
    validate_data.add_argument("--require-tokenizer", action="store_true")
    validate_data.set_defaults(handler=_validate_data)

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

    preflight = subparsers.add_parser(
        "preflight", help="check authorization, runtime, tokenizer, and data"
    )
    preflight.add_argument("config")
    preflight.add_argument("--project-root")
    preflight.add_argument("--tokenizer-path")
    preflight.add_argument("--model-path")
    preflight.set_defaults(handler=_preflight)

    train = subparsers.add_parser(
        "train", help="run the authorized smoke test on the verified GPU"
    )
    train.add_argument("config")
    train.add_argument("--project-root")
    train.add_argument("--model-path")
    train.add_argument("--tokenizer-path")
    train.add_argument("--output-dir")
    train.add_argument("--pod-id", required=True)
    train.add_argument("--region", required=True)
    train.add_argument("--host", required=True)
    train.add_argument("--image", required=True)
    train.add_argument("--resume-from-checkpoint")
    train.set_defaults(handler=_train)

    infer = subparsers.add_parser(
        "infer", help="generate base, existing-adapter, and new-adapter outputs"
    )
    infer.add_argument("config")
    infer.add_argument("--run-dir", required=True)
    infer.add_argument("--new-adapter", required=True)
    infer.add_argument("--existing-adapter", required=True)
    infer.add_argument("--project-root")
    infer.add_argument("--model-path")
    infer.add_argument("--tokenizer-path")
    infer.set_defaults(handler=_infer)

    verify = subparsers.add_parser(
        "verify-artifacts", help="verify every checksum in a run directory"
    )
    verify.add_argument("run_dir")
    verify.set_defaults(handler=_verify_artifacts)

    cost = subparsers.add_parser(
        "record-cost", help="record final billing after the Pod is terminated"
    )
    cost.add_argument("run_dir")
    cost.add_argument("--final-credit-charge", type=float, required=True)
    cost.add_argument("--final-cash-charge", type=float, required=True)
    cost.add_argument("--remaining-credit", type=float, required=True)
    cost.add_argument("--sales-tax", type=float, default=0.0)
    cost.add_argument("--payment-fee", type=float, default=0.0)
    cost.add_argument("--notes", default="")
    cost.set_defaults(handler=_record_cost)

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
