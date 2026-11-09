"""Blind A/B comparison of two models' benchmark answers.

  make : pair two answer files, hide which model is A or B, write a self-contained
         scoring page (HTML) plus a separate key file. Reviewers never see the key.
  tally: join the reviewers' exported CSV with the key and count preferences
         per category. Counts only; no overall score (spec 11.4).

  python -m benchmark.blind make --a answers-base.jsonl --b answers-v0.2.jsonl --tag v0.2-vs-base --out-dir data/benchmark/blind
  python -m benchmark.blind tally --key data/benchmark/blind/key-v0.2-vs-base.json --csv blind-v0.2-vs-base-Group-1-2026-11-10.csv
"""

import argparse
import csv
import json
import random
import sys
from pathlib import Path


def _read(path):
    return {r["item_id"]: r for r in (json.loads(l) for l in open(path, encoding="utf-8") if l.strip())}


def make_pairs(a_rows, b_rows, seed=11):
    """Return (pairs, key). pairs carry no model names."""
    rng = random.Random(seed)
    ids = sorted(set(a_rows) & set(b_rows))
    pairs, key = [], {}
    for iid in ids:
        a, b = a_rows[iid], b_rows[iid]
        left, right = (a, b) if rng.random() < 0.5 else (b, a)
        pairs.append({"item_id": iid, "category": a.get("category", ""), "prompt": a["prompt"],
                      "expected_behavior": a.get("expected_behavior", ""),
                      "A": left["answer"], "B": right["answer"]})
        key[iid] = {"A": left["model"], "B": right["model"]}
    rng.shuffle(pairs)
    return pairs, key


def tally(key, rows):
    """rows: dicts with item_id, category, choice in {A,B,both_good,both_bad,''}."""
    out = {}
    for r in rows:
        k = key.get(r["item_id"])
        if not k or not r.get("choice"):
            continue
        cat = out.setdefault(r.get("category") or "?", {})
        c = r["choice"]
        label = k[c] if c in ("A", "B") else c
        cat[label] = cat.get(label, 0) + 1
    return out


PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark"><title>Blind comparison</title><style>
body{font-family:system-ui,sans-serif;max-width:860px;margin:0 auto;padding:16px;background:#14171c;color:#e6e8eb;line-height:1.5}
h1{font-size:1.3rem}.muted{color:#9aa4b2;font-size:.9rem}.card{background:#1e232b;border:1px solid #333b47;border-radius:10px;padding:16px;margin:12px 0}
.q{font-size:1.1rem;white-space:pre-wrap}.guide{background:#222a3d;border-radius:8px;padding:10px;margin:10px 0;font-size:.92rem}
.ans{border:1px solid #3a4452;border-radius:8px;padding:12px;margin:8px 0;white-space:pre-wrap;font-size:1.05rem}.ans b{color:#7ea2ff}
label.opt{display:block;padding:10px;border:1px solid #3a4452;border-radius:8px;margin:6px 0;cursor:pointer}
label.opt:has(input:checked){background:#1f3550;border-color:#4a90e2}
input[type=text]{width:100%;box-sizing:border-box;font:inherit;padding:8px;background:#12151a;color:#e6e8eb;border:1px solid #3a4452;border-radius:6px}
button{font:inherit;padding:10px 16px;margin:4px 4px 4px 0;border-radius:8px;border:1px solid #556;background:#262c36;color:#e6e8eb;cursor:pointer}
button.p{background:#2f6fc4;border-color:#2f6fc4;color:#fff}.bar{height:8px;background:#333b47;border-radius:4px}.bar div{height:8px;background:#4a90e2;border-radius:4px}
</style></head><body><h1>Which answer is better?</h1>
<p class="muted">Two AI answers to the same question. You are not told which AI wrote which. Judge the Luganda and whether it does what the guide says. Nothing leaves this computer.</p>
<p>Your name or code: <input type="text" id="who" value="Group-1" style="width:12em"></p>
<div class="bar"><div id="prog" style="width:0"></div></div><p id="count" class="muted"></p><div id="app"></div>
<script>
const TAG=__TAG__, ITEMS=__DATA__, KEY="blind-"+TAG; let ans={}, i=0;
try{ans=JSON.parse(localStorage.getItem(KEY)||"{}")}catch(e){}
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(ans))}catch(e){}};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const done=()=>ITEMS.filter(x=>(ans[x.item_id]||{}).choice).length;
const code=()=>(document.getElementById('who').value||"x").replace(/[^\w-]/g,"");
function head(){document.getElementById('count').textContent="Question "+(i+1)+" of "+ITEMS.length+" - "+done()+" answered";
 document.getElementById('prog').style.width=(done()/ITEMS.length*100)+"%"}
function show(){const it=ITEMS[i],a=ans[it.item_id]||{};head();
 const o=[["A","A is better"],["B","B is better"],["both_good","Both are good"],["both_bad","Both are bad"]];
 document.getElementById('app').innerHTML='<div class="card"><div class="muted">'+esc(it.category)+'</div><div class="q">'+esc(it.prompt)+'</div>'+
 (it.expected_behavior?'<div class="guide"><b>What a good answer must do:</b> '+esc(it.expected_behavior)+'</div>':'')+
 '<div class="ans"><b>Answer A</b><br>'+esc(it.A)+'</div><div class="ans"><b>Answer B</b><br>'+esc(it.B)+'</div>'+
 o.map(x=>'<label class="opt"><input type="radio" name="v" value="'+x[0]+'"'+(a.choice==x[0]?' checked':'')+'> '+x[1]+'</label>').join('')+
 '<p>Why? (optional)</p><input type="text" id="note" value="'+esc(a.note||"")+'"></div>'+
 '<button id="prev">Back</button><button class="p" id="next">'+(i==ITEMS.length-1?'Finish':'Save and next')+'</button> <button id="exp">Export CSV</button><button id="bak">Backup JSON</button>';
 document.getElementById('prev').onclick=()=>{keep();if(i>0)i--;show()};
 document.getElementById('next').onclick=()=>{keep();if(i<ITEMS.length-1)i++;show()};
 document.getElementById('exp').onclick=()=>{keep();csv()};
 document.getElementById('bak').onclick=()=>{keep();dl("blind-"+TAG+"-backup-"+code()+".json",JSON.stringify(ans,null,1),"application/json")}}
function keep(){const it=ITEMS[i],v=document.querySelector('input[name=v]:checked');
 ans[it.item_id]={choice:v?v.value:(ans[it.item_id]||{}).choice||"",note:document.getElementById('note').value};save();head()}
const q=s=>'"'+String(s).replace(/"/g,'""')+'"';
function csv(){const r=[["item_id","category","choice","note","reviewer"].join(",")];
 ITEMS.forEach(it=>{const a=ans[it.item_id]||{};r.push([it.item_id,it.category,a.choice||"",a.note||"",code()].map(q).join(","))});
 dl("blind-"+TAG+"-"+code()+"-"+new Date().toISOString().slice(0,10)+".csv","﻿"+r.join("\n"),"text/csv")}
function dl(n,t,m){const b=new Blob([t],{type:m+";charset=utf-8"}),u=URL.createObjectURL(b),a=document.createElement('a');a.href=u;a.download=n;a.click()}
show();
</script></body></html>"""


def write_outputs(pairs, key, tag, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = json.dumps(pairs, ensure_ascii=False).replace("</", "<\\/")
    page = PAGE.replace("__TAG__", json.dumps(tag)).replace("__DATA__", data)
    (out_dir / f"blind-{tag}.html").write_text(page, encoding="utf-8")
    (out_dir / f"key-{tag}.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    return out_dir / f"blind-{tag}.html", out_dir / f"key-{tag}.json"


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--a", required=True); m.add_argument("--b", required=True)
    m.add_argument("--tag", required=True); m.add_argument("--out-dir", default="data/benchmark/blind")
    m.add_argument("--seed", type=int, default=11)
    t = sub.add_parser("tally")
    t.add_argument("--key", required=True); t.add_argument("--csv", required=True)
    a = p.parse_args(argv)
    if a.cmd == "make":
        pairs, key = make_pairs(_read(a.a), _read(a.b), a.seed)
        page, keyf = write_outputs(pairs, key, a.tag, a.out_dir)
        print(f"{len(pairs)} pairs. Page for reviewers: {page}. Key (do NOT share with reviewers): {keyf}")
    else:
        key = json.loads(Path(a.key).read_text(encoding="utf-8"))
        rows = list(csv.DictReader(open(a.csv, encoding="utf-8-sig")))
        print(json.dumps(tally(key, rows), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
