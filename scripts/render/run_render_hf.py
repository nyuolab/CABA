"""CABA v1.0 render (docs/protocol.md, section 3) for benchmarks hosted on Hugging Face. No LLM calls, no API keys.
Writes $CABA_DATA/rendered/<slug>.jsonl and a rendering block in registry/manifests/<slug>.json.

    python scripts/render/run_render_hf.py [slug ...]
"""
import os, sys, random, statistics, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_loaders_hf import *
OUT = H + "rendered/"
SLUGS = sys.argv[1:] or sorted(LOADERS)
rows = []
for slug in SLUGS:
    m = man(slug)
    items, info = LOADERS[slug](slug)
    items = add_stems(slug, items)
    excl = {"non_english": 0, "image": 0, "duplicate": 0}
    usable, seen = [], set()
    for it in items:
        if it.get("image") or image_hit(it.get("stem")):
            excl["image"] += 1; continue
        if it["request"] in seen:
            excl["duplicate"] += 1; continue
        seen.add(it["request"]); usable.append(it)
    rng = random.Random(SEED)
    samp = rng.sample(usable, 200) if len(usable) > 200 else list(usable)
    with open(OUT + slug + ".jsonl", "w") as f:
        for it in samp:
            rec = {"benchmark": m["benchmark"], "slug": slug, "item_id": it["item_id"]}
            if it.get("component"): rec["component"] = it["component"]
            rec["request"] = it["request"]; rec["n_chars"] = len(it["request"])
            if it.get("candidate"): rec["candidate"] = it["candidate"]
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    nch = [len(it["request"]) for it in samp]
    r = {"rule": info["rule"], "template_source": info["template_source"], "n_usable": len(usable), "n_sampled": len(samp),
         "seed": SEED, "excluded": excl,
         "image_rule": ("Structured: non-empty HEAD-QA 'image' field. Plus stem rule: " if slug == "head_qa" else "") + IMAGE_RULE_TEXT2,
         "mean_chars": round(statistics.mean(nch), 1), "max_chars": max(nch),
         "n_released_rendered": len(items), "n_unrenderable": 0, "rendered_file": OUT + slug + ".jsonl",
         "version": 2}
    if any(it.get("component") for it in samp):
        r["components_sampled"] = dict(collections.Counter(it["component"] for it in samp))
    if slug == "medhallu":
        r["candidates_sampled"] = dict(collections.Counter(it["candidate"] for it in samp))
    m["rendering"] = r
    with open(MAN + slug + ".json", "w") as f:
        json.dump(m, f, indent=2, ensure_ascii=False)
    rows.append(dict(slug=slug, rendering=r))
    print(f"{slug}: usable {len(usable)}, sampled {len(samp)}, excluded {excl}", flush=True)
json.dump(rows, open(H + "render_hf_summary.json", "w"), indent=1, default=str)
