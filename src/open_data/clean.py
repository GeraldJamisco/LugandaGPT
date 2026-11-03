"""Make the downloaded open data Luganda-only and readable.

SALT: keep only the English source and the Luganda text. All other languages are
dropped. Train rows go to one file, dev and test rows to a separate held-out file.
Wikipedia: strip wiki markup and keep plain Luganda paragraphs.
"""

import bz2
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ENGLISH_WORDS = frozenset("the and of is was in to for with that this are".split())


def salt_rows(path):
    """Yield (split, id, english, luganda) from the full SALT file, dropping other languages."""
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            lug = " ".join((row.get("lug_text") or "").split())
            eng = " ".join((row.get("eng_source_text") or "").split())
            if lug:
                yield row["split"], row["id"], eng, lug


def write_salt(src, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    counts = {"train": 0, "heldout": 0}
    with open(out / "salt-luganda-train.jsonl", "w", encoding="utf-8") as train, \
            open(out / "salt-luganda-heldout.jsonl", "w", encoding="utf-8") as held:
        for split, rid, eng, lug in salt_rows(src):
            rec = {"id": f"SALT-{split}-{rid}", "split": split, "english": eng, "luganda": lug}
            if split == "train":
                train.write(json.dumps(rec, ensure_ascii=False) + "\n")
                counts["train"] += 1
            else:
                held.write(json.dumps(rec, ensure_ascii=False) + "\n")
                counts["heldout"] += 1
    return counts


_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
_FILE = re.compile(r"\[\[(?:File|Image|Kategoori|Category|Ekifaananyi|Fayiro)[^\[\]]*(?:\[\[[^\[\]]*\]\][^\[\]]*)*\]\]", re.I)


def clean_wikitext(text):
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", text, flags=re.S | re.I)
    text = re.sub(r"<(gallery|table|math|code|source|syntaxhighlight)[^>]*>.*?</\1>", "", text, flags=re.S | re.I)
    text = re.sub(r"\{\|.*?\|\}", "", text, flags=re.S)
    for _ in range(6):
        new = _TEMPLATE.sub("", text)
        if new == text:
            break
        text = new
    text = _FILE.sub("", text)
    text = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"\[https?://[^\s\]]+\s*([^\]]*)\]", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("'''", "").replace("''", "")
    return text


def paragraphs(text, min_words=12):
    for block in clean_wikitext(text).split("\n"):
        block = " ".join(block.split())
        if not block or block[0] in "*#:;=|!{}" or block.startswith("__"):
            continue
        words = block.split()
        if len(words) < min_words:
            continue
        low = [w.lower().strip(".,;:!?()\"'") for w in words]
        if sum(w in ENGLISH_WORDS for w in low) / len(words) > 0.12:
            continue
        yield block


def write_wikipedia(src, out_path):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    articles = count = 0
    with open(out_path, "w", encoding="utf-8") as handle:
        for _, el in ET.iterparse(bz2.open(src), events=("end",)):
            if not el.tag.endswith("}page"):
                continue
            ns = el.find("./{*}ns")
            title = el.find("./{*}title")
            node = el.find("./{*}revision/{*}text")
            text = (node.text or "") if node is not None else ""
            if ns is not None and ns.text == "0" and not text.lstrip().lower().startswith(("#redirect", "#kyusa")):
                got = False
                for n, para in enumerate(paragraphs(text), 1):
                    handle.write(json.dumps({"id": f"WIKI-{articles + 1:05d}-{n:02d}", "title": title.text if title is not None else "", "text": para}, ensure_ascii=False) + "\n")
                    count += 1
                    got = True
                articles += got
            el.clear()
    return {"articles": articles, "paragraphs": count}
