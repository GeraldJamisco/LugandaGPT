"""Run directories, manifests, and checksum inventories."""

import datetime as _datetime
import json
import math
import shutil
from pathlib import Path

from .constants import CASH_CAP_USD, HARD_CREDIT_STOP_USD
from .errors import ArtifactError
from .environment import (
    collect_gpu_record,
    collect_host_record,
    collect_installed_packages,
    environment_freeze_text,
)
from .storage import (
    pretty_json,
    read_json,
    sha256_file,
    write_json,
)

MANIFEST_NAME = "run_manifest.json"
MANIFEST_HASH_NAME = "run_manifest.sha256"
ARTIFACT_NAME = "artifact_manifest.json"
ARTIFACT_HASH_NAME = "artifact_manifest.sha256"


def utc_now():
    return _datetime.datetime.now(_datetime.timezone.utc).isoformat()


def _jsonable(value):
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (_datetime.date, _datetime.datetime)):
        return value.isoformat()
    return value


def prepare_run_directory(config, output_dir=None):
    path = Path(output_dir or config["training"]["output_dir"])
    if path.exists():
        try:
            non_empty = any(path.iterdir())
        except OSError as error:
            raise ArtifactError(f"cannot inspect run directory {path}: {error}") from error
        if non_empty:
            raise ArtifactError(
                f"run directory already exists and is not empty: {path}; "
                "use a new run directory"
            )
    try:
        (path / "logs").mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ArtifactError(f"cannot create run directory {path}: {error}") from error
    return path


def export_config_snapshot(output_dir, loaded_config):
    output = Path(output_dir)
    try:
        source = loaded_config.path.read_bytes()
    except OSError as error:
        raise ArtifactError(f"cannot read the source config: {error}") from error
    config_copy = output / "config.snapshot.yaml"
    config_copy.write_bytes(source)
    resolved = output / "resolved_config.json"
    write_json(resolved, _jsonable(loaded_config.data))
    return {
        "source_config_sha256": loaded_config.sha256,
        "snapshot": "config.snapshot.yaml",
        "resolved": "resolved_config.json",
    }


def export_environment(output_dir, runtime_record=None, code_manifest=None, git_record=None):
    output = Path(output_dir)
    packages = collect_installed_packages()
    write_json(output / "environment.json", {
        "packages": packages,
        "runtime": runtime_record,
        "code": code_manifest,
        "git": git_record,
    })
    (output / "environment_freeze.txt").write_text(
        environment_freeze_text(), encoding="utf-8", newline="\n"
    )
    write_json(output / "gpu.json", collect_gpu_record())
    write_json(output / "host.json", collect_host_record())
    return {
        "environment": "environment.json",
        "environment_freeze": "environment_freeze.txt",
        "gpu": "gpu.json",
        "host": "host.json",
    }


def _hash_tree(root):
    root = Path(root)
    files = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return files


def export_checkpoint_manifest(output_dir):
    output = Path(output_dir)
    checkpoints = []
    for path in sorted(output.glob("checkpoint-*")):
        if not path.is_dir():
            continue
        checkpoints.append(
            {
                "name": path.name,
                "files": _hash_tree(path),
            }
        )
    write_json(output / "checkpoint_manifest.json", {"checkpoints": checkpoints})
    return checkpoints


def write_run_manifest(output_dir, manifest):
    output = Path(output_dir)
    value = _jsonable(manifest)
    write_json(output / MANIFEST_NAME, value)
    digest = sha256_file(output / MANIFEST_NAME)
    (output / MANIFEST_HASH_NAME).write_text(digest + "\n", encoding="utf-8", newline="\n")
    return digest


def read_run_manifest(output_dir):
    output = Path(output_dir)
    value = read_json(output / MANIFEST_NAME)
    expected_path = output / MANIFEST_HASH_NAME
    if not expected_path.is_file():
        raise ArtifactError("run manifest hash sidecar is missing")
    expected = expected_path.read_text(encoding="utf-8").strip()
    actual = sha256_file(output / MANIFEST_NAME)
    if expected != actual:
        raise ArtifactError("run manifest does not match its hash sidecar")
    return value


def write_artifact_inventory(output_dir):
    output = Path(output_dir)
    excluded = {ARTIFACT_NAME, ARTIFACT_HASH_NAME}
    files = [
        item
        for item in _hash_tree(output)
        if item["path"] not in excluded
    ]
    manifest = {
        "generated_at_utc": utc_now(),
        "root": str(output),
        "files": files,
        "file_count": len(files),
    }
    write_json(output / ARTIFACT_NAME, manifest)
    digest = sha256_file(output / ARTIFACT_NAME)
    (output / ARTIFACT_HASH_NAME).write_text(digest + "\n", encoding="utf-8", newline="\n")
    return manifest


def verify_artifact_inventory(output_dir):
    output = Path(output_dir)
    if not (output / ARTIFACT_NAME).is_file():
        raise ArtifactError("artifact manifest is missing")
    manifest = read_json(output / ARTIFACT_NAME)
    sidecar = output / ARTIFACT_HASH_NAME
    if not sidecar.is_file():
        raise ArtifactError("artifact manifest hash sidecar is missing")
    if sidecar.read_text(encoding="utf-8").strip() != sha256_file(
        output / ARTIFACT_NAME
    ):
        raise ArtifactError("artifact manifest does not match its hash sidecar")
    listed = {}
    for item in manifest.get("files", []):
        relative = item.get("path")
        if not isinstance(relative, str) or not relative:
            raise ArtifactError("artifact manifest contains an invalid path")
        path = (output / relative).resolve()
        try:
            path.relative_to(output.resolve())
        except ValueError as error:
            raise ArtifactError(f"artifact path escapes the run directory: {relative}") from error
        if not path.is_file():
            raise ArtifactError(f"listed artifact is missing: {relative}")
        if path.stat().st_size != item.get("size"):
            raise ArtifactError(f"artifact size changed: {relative}")
        if sha256_file(path) != item.get("sha256"):
            raise ArtifactError(f"artifact hash changed: {relative}")
        listed[relative] = True
    actual = {
        item["path"] for item in _hash_tree(output) if item["path"] not in {ARTIFACT_NAME, ARTIFACT_HASH_NAME}
    }
    unlisted = sorted(actual - set(listed))
    if unlisted:
        raise ArtifactError(f"unlisted files in run directory: {unlisted}")
    return True


def record_final_cost(
    output_dir,
    *,
    final_credit_charge_usd,
    final_cash_charge_usd,
    remaining_credit_usd,
    sales_tax_usd=0.0,
    payment_fee_usd=0.0,
    notes="",
):
    output = Path(output_dir)
    numbers = {
        "final_credit_charge_usd": final_credit_charge_usd,
        "final_cash_charge_usd": final_cash_charge_usd,
        "remaining_credit_usd": remaining_credit_usd,
        "sales_tax_usd": sales_tax_usd,
        "payment_fee_usd": payment_fee_usd,
    }
    for name, value in numbers.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ArtifactError(f"{name} must be a non-negative number")
        if not math.isfinite(value) or value < 0:
            raise ArtifactError(f"{name} must be a finite non-negative number")
    breaches = []
    if final_cash_charge_usd > CASH_CAP_USD:
        breaches.append(
            f"cash charge ${final_cash_charge_usd:.2f} exceeds the "
            f"${CASH_CAP_USD:.2f} cap"
        )
    if final_credit_charge_usd > HARD_CREDIT_STOP_USD:
        breaches.append(
            f"credit charge ${final_credit_charge_usd:.2f} exceeds the "
            f"${HARD_CREDIT_STOP_USD:.2f} hard stop"
        )
    record = {
        "recorded_at_utc": utc_now(),
        **numbers,
        "cash_cap_usd": CASH_CAP_USD,
        "hard_credit_stop_usd": HARD_CREDIT_STOP_USD,
        "within_caps": not breaches,
        "breaches": breaches,
        "notes": notes,
    }
    write_json(output / "cost_record.json", record)
    manifest = read_run_manifest(output)
    manifest["cost"] = record
    manifest["final_billing_recorded"] = True
    write_run_manifest(output, manifest)
    write_artifact_inventory(output)
    return record


def copy_file(source, destination):
    source = Path(source)
    destination = Path(destination)
    if not source.is_file():
        raise ArtifactError(f"source file missing: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def write_json_text(path, value):
    path = Path(path)
    path.write_text(pretty_json(_jsonable(value)), encoding="utf-8", newline="\n")
    return path


def load_json_file(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ArtifactError(f"cannot read JSON file {path}: {error}") from error
