"""Runtime verification and evidence collection.

No check here substitutes for a human billing or data approval. The runtime
check verifies the GPU and packages; the training manifest records what was
actually present.
"""

import importlib.metadata
import platform
import socket
import subprocess
import sys
from pathlib import Path

from .constants import DISTRIBUTION_NAMES
from .errors import EnvironmentError
from .storage import sha256_file

PACKAGE_KEYS = (
    "torch",
    "transformers",
    "peft",
    "accelerate",
    "bitsandbytes",
    "datasets",
    "trl",
    "huggingface_hub",
    "tokenizers",
    "safetensors",
    "sentencepiece",
)


def _distribution_name(key):
    return DISTRIBUTION_NAMES.get(key, key)


def installed_versions():
    versions = {}
    for key in PACKAGE_KEYS:
        name = _distribution_name(key)
        try:
            versions[key] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[key] = None
    return versions


def _normalise_torch_version(value):
    return value.split("+", 1)[0]


def check_runtime(config, require_gpu=True):
    """Verify Python, pinned packages, CUDA, BF16, and the named GPU."""
    expected_python = config["dependencies"]["python"]
    actual_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    if actual_python != expected_python:
        raise EnvironmentError(
            f"Python {expected_python} is required; found {actual_python}"
        )
    versions = installed_versions()
    missing = [key for key, value in versions.items() if value is None]
    if missing:
        raise EnvironmentError(
            "required training packages are not installed: "
            + ", ".join(sorted(missing))
        )
    mismatches = []
    for key in PACKAGE_KEYS:
        expected = config["dependencies"][key]
        actual = versions[key]
        if key == "torch":
            actual = _normalise_torch_version(actual)
        if actual != expected:
            mismatches.append(f"{key}: expected {expected}, found {actual}")
    if mismatches:
        raise EnvironmentError("; ".join(mismatches))

    if not require_gpu:
        return {"versions": versions, "gpu_checked": False}

    try:
        import torch
    except ImportError as error:
        raise EnvironmentError("PyTorch cannot be imported") from error

    expected_cuda = config["dependencies"]["torch_cuda"]
    if torch.version.cuda != expected_cuda:
        raise EnvironmentError(
            f"PyTorch CUDA {expected_cuda} is required; found {torch.version.cuda}"
        )
    if not torch.cuda.is_available():
        raise EnvironmentError("CUDA is not available")
    if torch.cuda.device_count() < 1:
        raise EnvironmentError("no CUDA device is visible")
    if not torch.cuda.is_bf16_supported():
        raise EnvironmentError("the GPU does not report BF16 support")
    properties = torch.cuda.get_device_properties(0)
    name = properties.name
    if "4090" not in name:
        raise EnvironmentError(
            f"the approved GPU is an RTX 4090; found {name!r}"
        )
    total_gb = properties.total_memory / (1024**3)
    if total_gb < 23.0:
        raise EnvironmentError(
            f"the approved GPU has 24 GB; only {total_gb:.2f} GiB is visible"
        )
    if (properties.major, properties.minor) < (8, 9):
        raise EnvironmentError(
            f"compute capability {(properties.major, properties.minor)} is below Ada"
        )
    try:
        import bitsandbytes
    except ImportError as error:
        raise EnvironmentError("bitsandbytes cannot be imported") from error
    if bitsandbytes.__version__ != config["dependencies"]["bitsandbytes"]:
        raise EnvironmentError(
            "bitsandbytes version changed after the package check"
        )
    return {
        "versions": versions,
        "gpu_checked": True,
        "gpu_name": name,
        "gpu_total_memory_gb": round(total_gb, 3),
        "compute_capability": f"{properties.major}.{properties.minor}",
        "multi_processor_count": properties.multi_processor_count,
        "cuda": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(),
        "python": sys.version,
        "platform": platform.platform(),
        "torch": torch.__version__,
    }


def collect_installed_packages():
    records = []
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata.get("Name")
        if not name:
            continue
        records.append({"name": name, "version": distribution.version})
    return sorted(records, key=lambda item: item["name"].casefold())


def environment_freeze_text():
    return "\n".join(
        f"{item['name']}=={item['version']}" for item in collect_installed_packages()
    ) + "\n"


def collect_nvidia_smi():
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total,memory.used,temperature.gpu",
                "--format=csv",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return {"available": False, "error": str(error)}
    return {
        "available": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def collect_gpu_record():
    try:
        import torch
    except ImportError:
        return {"available": False, "error": "torch is not installed"}
    if not torch.cuda.is_available():
        return {"available": False, "error": "CUDA is not available"}
    properties = torch.cuda.get_device_properties(0)
    return {
        "available": True,
        "name": properties.name,
        "total_memory_gb": round(properties.total_memory / (1024**3), 3),
        "allocated_memory_gb": round(torch.cuda.memory_allocated(0) / (1024**3), 3),
        "reserved_memory_gb": round(torch.cuda.memory_reserved(0) / (1024**3), 3),
        "max_allocated_memory_gb": round(torch.cuda.max_memory_allocated(0) / (1024**3), 3),
        "compute_capability": f"{properties.major}.{properties.minor}",
        "cuda": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(),
        "torch": torch.__version__,
        "nvidia_smi": collect_nvidia_smi(),
    }


def collect_code_manifest(project_root):
    root = Path(project_root).resolve()
    package_root = Path(__file__).resolve().parent
    files = {}
    for path in sorted(package_root.glob("*.py")):
        files[f"src/training/{path.name}"] = sha256_file(path)
    return {"project_root": str(root), "training_files": files}


def collect_git_record(project_root):
    def run(*args):
        try:
            completed = subprocess.run(
                ["git", *args],
                cwd=str(project_root),
                check=False,
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (OSError, subprocess.SubprocessError) as error:
            return {"error": str(error)}
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }

    return {
        "head": run("rev-parse", "HEAD"),
        "status": run("status", "--porcelain"),
    }


def collect_host_record():
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version,
        "python_executable": sys.executable,
    }
