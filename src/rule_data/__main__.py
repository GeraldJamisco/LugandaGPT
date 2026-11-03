import csv
import sys
from pathlib import Path

from .time_days import generate_all

out = Path(sys.argv[1] if len(sys.argv) > 1 else "data/synthetic/time-days-all.csv")
out.parent.mkdir(parents=True, exist_ok=True)
rows = generate_all()
with open(out, "w", newline="", encoding="utf-8") as handle:
    w = csv.DictWriter(handle, fieldnames=["id", "kind", "question", "answer", "alt_answer", "source", "review_status"])
    w.writeheader()
    for n, r in enumerate(rows, 1):
        w.writerow({"id": f"RG-TIME-{n:03d}", **r, "source": "rule_generated_from_group_rules", "review_status": "unreviewed"})
print(f"wrote {len(rows)} rows to {out}")
