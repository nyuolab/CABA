"""Shared helpers for the Hugging Face renderers: manifests, item files, multiple-choice formatting and the image rule."""
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from caba_paths import DATA as _DATA, MANIFESTS as _MAN, RAW as _RAW  # noqa: E402
import json, os, re, ast, glob, math
import pandas as pd, pyarrow.parquet as pq
H = str(_DATA) + "/"
MAN = str(_MAN) + "/"
SEED = 20261004
L = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# ---- image rule (fixed, applied to every rendered request) ----
STRICT = r"(?:figures?|fig\.|images?|pictures?|photos?|photographs?|photomicrographs?|micrographs?|exhibits?|illustrations?|diagrams?|graphs?)"
BROAD = r"(?:figures?|fig\.|images?|pictures?|photos?|photographs?|photomicrographs?|micrographs?|exhibits?|illustrations?|diagrams?|graphs?|radiographs?|x-?rays?|ecgs?|ekgs?|electrocardiograms?|tracings?|smears?|scans?)"
IMAGE_RULE_PATTERNS = [
    r"\b(?:shown|seen|depicted|displayed|illustrated|pictured|presented)\s+(?:in|on|below|above)\s+(?:the\s+)?(?:accompanying\s+|following\s+|attached\s+|adjacent\s+)?" + STRICT + r"\b",
    r"\b(?:see|refer\s+to)\s+(?:the\s+)?(?:accompanying\s+|following\s+|attached\s+)?" + STRICT + r"\b",
    r"\bthe\s+(?:following|accompanying|attached|adjacent)\s+" + BROAD + r"\b",
    r"\b(?:this|these)\s+" + STRICT + r"\b",
    r"\b(?:figure|fig\.)\s*\d+",
    r"\b" + BROAD + r"\s+(?:below|above|attached|shown)\b",
]
IMAGE_RE = re.compile("|".join("(?:%s)" % p for p in IMAGE_RULE_PATTERNS), re.I)
IMAGE_RULE_TEXT = ("An item is excluded as needing an unreleased image if its rendered request matches (case-insensitive) any of: "
    "(1) shown/seen/depicted/displayed/illustrated/pictured/presented + in/on/below/above + [the] [accompanying/following/attached/adjacent] + figure|image|picture|photo(graph)|(photo)micrograph|exhibit|illustration|diagram|graph; "
    "(2) see/refer to + [the] [accompanying/following/attached] + one of those words; "
    "(3) 'the following/accompanying/attached/adjacent' + one of those words or radiograph|x-ray|ECG|EKG|electrocardiogram|tracing|smear|scan; "
    "(4) this/these + figure|image|picture|photo(graph)|(photo)micrograph|exhibit|illustration|diagram|graph; "
    "(5) 'figure N' or 'fig. N'; "
    "(6) any word of (3) followed by below|above|attached|shown. "
    "Regex: " + IMAGE_RE.pattern)

def mcq(stem, opts):
    """opts: list of (label, text)."""
    return stem.strip() + "\n" + "\n".join(f"{l}. {str(t).strip()}" for l, t in opts)

def isnan(x):
    return x is None or (isinstance(x, float) and math.isnan(x))

def man(slug):
    return json.load(open(MAN + slug + ".json"))

def item_files(slug):
    m = man(slug)
    out = []
    for f in m["files"]:
        role = f.get("role", "items")
        p = f["path"]
        if "card" in role or "SPLIT" in role or p.endswith("README.md") or "/_card/" in p:
            continue
        out.append(p)
    return out
