"""Helpers shared by render_loaders_hf.py."""
from render_lib import H, MAN, SEED, L, mcq, isnan, man, item_files
import json, os, re

# ---- image rule v2: applied only to the question stem (never to documents the item asks about) ----
VIS_STRICT = r"(?:figures?|fig\.|images?|pictures?|photos?|photographs?|photomicrographs?|micrographs?|exhibits?|illustrations?|diagrams?|graphs?)"
VIS_NOFIGPIC = r"(?:images?|photos?|photographs?|photomicrographs?|micrographs?|exhibits?|illustrations?|diagrams?|graphs?)"
VIS_BROAD = r"(?:figures?|fig\.|images?|pictures?|photos?|photographs?|photomicrographs?|micrographs?|exhibits?|illustrations?|diagrams?|graphs?|radiographs?|x-?rays?|ecgs?|ekgs?|electrocardiograms?|tracings?|smears?|scans?)"
PATS = [
  ("a", r"\b(?:shown|seen|depicted|displayed|illustrated|pictured|presented|visuali[sz]ed)\s+(?:in|on|below|above)\s+(?:the\s+|this\s+)?(?:accompanying\s+|following\s+|attached\s+|adjacent\s+)?" + VIS_STRICT + r"\b"),
  ("b1", r"\b(?:see|refer\s+to)\s+(?:the\s+|this\s+|these\s+)?(?:accompanying\s+|following\s+|attached\s+)?" + VIS_STRICT + r"\b"),
  ("b2", r"\blook\s+at\s+(?:the\s+|this\s+|these\s+|my\s+)?(?:accompanying\s+|following\s+|attached\s+)?" + VIS_BROAD + r"\b"),
  ("c", r"(?<!which of )(?<!which of\s)\bthe\s+(?:following|accompanying|attached|adjacent)\s+" + VIS_BROAD + r"\b"),
  ("d", r"\b(?:this|these)\s+" + VIS_NOFIGPIC + r"\b"),
  ("e", r"\b(?:figures?|figs?\.|images?)(?:\s*#?\s*\d+|\s+(?-i:[A-H])(?:\s*(?:-|–|and|,)\s*(?-i:[A-H]))?)\b"),
  ("f", r"\b" + VIS_BROAD + r"\s+(?:shown|attached|enclosed|below)\b"),
  ("g", r"\b(?:attached|enclosed|uploaded|sent|sending|attaching|uploading)\s+(?:herewith\s+)?(?:(?:this|these|the|a|an|my|his|her|some|few|a\s+few)\s+)?(?:(?!for\b|to\b|in\b|out\b)\w+\s+)?(?:pictures?|photos?|photographs?|images?|x-?rays?|radiographs?)\b"),
]
IMAGE_RE2 = re.compile("|".join("(?:%s)" % p for _, p in PATS), re.I)
IMAGE_RULE_TEXT2 = (
 "Exclude an item as needing an unreleased picture only if (i) a released image field marks it (HEAD-QA 'image'), or (ii) its question stem "
 "(the part that asks the question: MCQ question text, MedCalc 'Question', MedHallu 'Question', Med-HALT reasoning 'question', a patient's own question in "
 "HealthCareMagic/iCliniq/MEDIQA-RQE) matches, case-insensitively, any of: "
 "(a) shown/seen/depicted/displayed/illustrated/pictured/presented/visualized + in/on/below/above + [the/this] [accompanying/following/attached/adjacent] + figure|image|picture|photo(graph)|(photo)micrograph|exhibit|illustration|diagram|graph; "
 "(b) see/refer to + [the/this/these] [accompanying/following/attached] + a word of (a), or look at + [the/this/these/my] [accompanying/following/attached] + a visual word (the list in (a) plus radiograph|x-ray|ECG|EKG|electrocardiogram|tracing|smear|scan); "
 "(c) 'the following/accompanying/attached/adjacent' + a visual word, unless preceded by 'which of'; "
 "(d) this/these + image|photo(graph)|(photo)micrograph|exhibit|illustration|diagram|graph (not 'figure' or 'picture', which in stems mostly mean numbers or a clinical picture); "
 "(e) figure/fig./image + a number, or + a space and a capital letter A-H (e.g. 'Figure 1', 'Figures A-C', 'image # 6'); "
 "(f) a visual word + shown|attached|enclosed|below; "
 "(g) attached/enclosed/uploaded/sent (or attaching/uploading/sending) + [herewith] [determiner] [one word other than for/to/in/out] + picture|photo(graph)|image|x-ray|radiograph. "
 "Documents the item asks about (case reports, patient notes, news articles, abstracts, radiology reports, conversations, MedS-Bench inputs, MedHallu Knowledge, "
 "MedCaseReasoning case_prompt, Med-HALT IR fields) are not scanned. Regex: " + IMAGE_RE2.pattern)

def image_hit(stem):
    return bool(stem) and bool(IMAGE_RE2.search(stem))
