import argparse
import json

from .fetch import fetch_salt_text, fetch_wikipedia

parser = argparse.ArgumentParser(prog="python -m open_data")
parser.add_argument("source", choices=["luganda-wikipedia", "salt-text", "clean"])
args = parser.parse_args()
if args.source == "clean":
    from pathlib import Path
    from .clean import write_salt, write_wikipedia
    root = Path(__file__).resolve().parents[2] / "data" / "external"
    result = {
        "salt": write_salt(root / "salt" / "salt-text-all.jsonl", root / "clean"),
        "wikipedia": write_wikipedia(root / "luganda-wikipedia" / "lgwiki-latest-pages-articles.xml.bz2", root / "clean" / "wikipedia-paragraphs.jsonl"),
    }
    print(json.dumps(result, indent=2))
else:
    record = fetch_wikipedia() if args.source == "luganda-wikipedia" else fetch_salt_text()
    print(json.dumps(record, ensure_ascii=False, indent=2))
