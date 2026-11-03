import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "data" / "external"

WIKIPEDIA_URL = "https://dumps.wikimedia.org/lgwiki/latest/lgwiki-latest-pages-articles.xml.bz2"
USER_AGENT = "LugandaGPT-research/0.1 (open data download; contact: project owner)"

SOURCES = {
    "luganda-wikipedia": {
        "url": WIKIPEDIA_URL,
        "licence": "CC BY-SA 4.0 (Wikipedia text licence; confirm on the dump page and keep attribution)",
        "note": "Raw dump. Contains wiki markup and tables. Extraction and cleaning come later.",
    },
    "salt-text": {
        "url": "https://huggingface.co/datasets/Sunbird/salt",
        "licence": "CC BY-SA 4.0 (per salt.sunbird.ai); gated, you must accept the terms on Hugging Face",
        "note": "Text subset text-all. Overlaps with Sunflower training data are possible. Keep its test splits out of training.",
    },
}


def _utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_provenance(name, path, extra=None):
    path = Path(path)
    record = {
        "source": name,
        "url": SOURCES[name]["url"],
        "licence": SOURCES[name]["licence"],
        "note": SOURCES[name]["note"],
        "file": str(path.relative_to(PROJECT_ROOT)) if PROJECT_ROOT in path.parents else str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "retrieved_utc": _utc_now(),
        "approval": "D-023",
        "review_status": "unreviewed",
    }
    if extra:
        record.update(extra)
    target = path.with_suffix(path.suffix + ".provenance.json")
    target.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


def fetch_wikipedia(opener=urllib.request.urlopen, out_dir=OUT_DIR):
    out = Path(out_dir) / "luganda-wikipedia"
    out.mkdir(parents=True, exist_ok=True)
    target = out / "lgwiki-latest-pages-articles.xml.bz2"
    request = urllib.request.Request(WIKIPEDIA_URL, headers={"User-Agent": USER_AGENT})
    with opener(request, timeout=120) as response, open(target, "wb") as handle:
        while True:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            handle.write(chunk)
    return write_provenance("luganda-wikipedia", target)


def fetch_salt_text(out_dir=OUT_DIR):
    """Needs `pip install datasets` and a Hugging Face token with SALT access (HF_TOKEN)."""
    try:
        from datasets import load_dataset
    except ImportError as error:
        raise SystemExit("Install the datasets package first: pip install datasets") from error
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit("Set HF_TOKEN to a Hugging Face token that can read Sunbird/salt")
    out = Path(out_dir) / "salt"
    out.mkdir(parents=True, exist_ok=True)
    data = load_dataset("Sunbird/salt", "text-all", token=token)
    target = out / "salt-text-all.jsonl"
    splits = {}
    with open(target, "w", encoding="utf-8") as handle:
        for split, rows in data.items():
            splits[split] = len(rows)
            for row in rows:
                # Luganda project: keep only English source and Luganda; never write other languages.
                keep = {"id": row.get("id"), "eng_source_text": row.get("eng_source_text"), "lug_text": row.get("lug_text")}
                handle.write(json.dumps({"split": split, **keep}, ensure_ascii=False) + "\n")
    return write_provenance("salt-text", target, {"splits": splits})
