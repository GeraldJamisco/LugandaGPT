"""Build the first fine-tuning set (train-v0.1) under decision D-024.

Sources: rule-generated time/day data, native-written situations, cleaned SALT train split
(with the group's corrections; the rejected sentence excluded). SALT dev/test and Wikipedia are never used.
Output is chat-format JSONL plus a manifest. No credentials are read.
"""
import csv
import hashlib
import json
import random
import re
from pathlib import Path

from rule_data.normalize import normalize

HELDOUT_PATTERN = re.compile(r"\b(8:00am|9:00am|10:00am|1:00pm|2:00pm)\b")


def _msg(id_, source, user, assistant):
    return {"id": id_, "source": source,
            "messages": [{"role": "user", "content": user}, {"role": "assistant", "content": assistant}]}


def time_days(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    return [_msg(r["id"], "rule_time_days", r["question"], r["answer"]) for r in rows]


def situations(path):
    out = []
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        text = (r.get("luganda_normalised") or "").strip()
        if text:
            prompt = r.get("prompt") or ("Write this in Luganda: " + r["english_situation"])
            out.append(_msg(r["id"], "native_situations", prompt, text))
    return out


def time_frames(path):
    """Luganda-hour to English-time questions in sentence frames written by the native group."""
    if not Path(path).exists():
        return []
    return [_msg(r["id"], "rule_time_frames", r["question"], r["answer"])
            for r in (json.loads(l) for l in open(path, encoding="utf-8") if l.strip())]


def salt(train_path, check_csv, seed=7, max_salt=None, to_english=True):
    fixes, drops = {}, set()
    for r in csv.DictReader(open(check_csv, encoding="utf-8-sig")):
        if not r["id"].startswith("SALT-train-"):
            continue
        if r["verdict"] == "drop":
            drops.add(r["id"])
        elif r["verdict"] == "fix" and r["corrected_luganda"].strip():
            fixes[r["id"]] = r["corrected_luganda"].strip()
    rng = random.Random(seed)
    out = []
    for line in open(train_path, encoding="utf-8"):
        r = json.loads(line)
        if r.get("split") != "train" or r["id"] in drops:
            continue
        lug = normalize(fixes.get(r["id"], r["luganda"]).strip())
        eng = r["english"].strip()
        if not lug or not eng:
            continue
        if not to_english or rng.random() < 0.5:
            out.append(_msg(r["id"], "salt_train", "Translate into Luganda: " + eng, lug))
        else:
            out.append(_msg(r["id"], "salt_train", "Translate into English: " + lug, eng))
    if max_salt is not None and len(out) > max_salt:
        rng.shuffle(out)
        out = out[:max_salt]
    return out, len(fixes), len(drops)


def build(root, out_path, repeat_rule=1, repeat_native=1, max_salt=None, salt_to_english=True, repeat_frames=1):
    root = Path(root)
    t = time_days(root / "data/synthetic/time-days-all.csv")
    n = situations(root / "data/synthetic/situations-native-v0.3.jsonl")
    s, nfix, ndrop = salt(root / "data/external/clean/salt-luganda-train.jsonl",
                          root / "data/external/outside-check-Group-1-2026-11-04.csv", max_salt=max_salt, to_english=salt_to_english)
    fr = time_frames(root / "data/synthetic/time-frames-v0.1.jsonl")
    rows = t * repeat_rule + n * repeat_native + fr * repeat_frames + s
    for r in rows:
        text = " ".join(m["content"] for m in r["messages"])
        if HELDOUT_PATTERN.search(text):
            raise ValueError("held-out hour in training row " + r["id"])
    random.Random(1).shuffle(rows)
    out_path = Path(out_path)
    with open(out_path, "w", encoding="utf-8", newline="\n") as h:
        for r in rows:
            h.write(json.dumps(r, ensure_ascii=False) + "\n")
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
    manifest = {"file": out_path.name, "sha256": digest, "rows": len(rows),
                "unique_time_days": len(t), "unique_native_situations": len(n), "salt_rows": len(s),
                "repeat_rule": repeat_rule, "repeat_native": repeat_native, "max_salt": max_salt,
                "unique_time_frames": len(fr), "repeat_frames": repeat_frames, "salt_to_english": salt_to_english,
                "salt_corrected": nfix, "salt_dropped": ndrop, "decisions": ["D-020", "D-022", "D-023", "D-024"],
                "excluded": ["salt dev/test", "wikipedia", "held-out clock hours and day facts"]}
    Path(str(out_path) + ".manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    p.add_argument("--output", default="data/training/train-v0.1.jsonl")
    p.add_argument("--repeat-rule", type=int, default=1)
    p.add_argument("--repeat-native", type=int, default=1)
    p.add_argument("--max-salt", type=int, default=None)
    p.add_argument("--no-salt-to-english", action="store_true")
    p.add_argument("--repeat-frames", type=int, default=1)
    a = p.parse_args()
    print(json.dumps(build(a.root, a.output, a.repeat_rule, a.repeat_native, a.max_salt, not a.no_salt_to_english, a.repeat_frames), indent=1))
