"""Frontier developer reports (docs/protocol.md, section 1), selected mechanically from Epoch AI's Notable AI
Models database.

Rule: models in the database snapshot (epoch_notable_ai_models_2026-10-04.csv, downloaded from
https://epoch.ai/data/notable_ai_models.csv on 4 October 2026) whose domain includes Language, whose
publication date is 1 January 2023 to 30 September 2026, and whose organization is one of the labs
in LABS. The document at each model's first link is fetched; if it is a launch page that links a
system card, model card or technical report, that document is fetched too. Each document's text is
scanned for health terms to find the passages that report health-benchmark results.

    python frontier_reports.py select     # frontier_reports_selected.csv
    python frontier_reports.py fetch      # $CABA_DATA/reports_raw/<id>.txt, fetch log
    python frontier_reports.py scan       # frontier_reports_health.csv: documents with health results
    python frontier_reports.py benchmarks # frontier_benchmarks.csv: each health benchmark with a quoted line

Pages that need a browser (JavaScript-rendered or blocking scripts) were read in Chrome on 4 October
2026; their health paragraphs, length and checksum are in frontier_reports_browser.jsonl, and linked
system-card PDFs are in $CABA_DATA/reports_raw/<doc_id>__card<n>.txt. Linked documents count only if they come
from the same developer (DOM).
"""
import csv
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from caba_paths import FRONTIER, MANIFESTS, REG, REPORTS_RAW  # noqa: E402

import requests

HERE = FRONTIER
SNAPSHOT = HERE / 'epoch_notable_ai_models_2026-10-04.csv'
SEL = HERE / 'frontier_reports_selected.csv'
RAW = REPORTS_RAW
UA = {'User-Agent': 'Mozilla/5.0 (research; CABA benchmark atlas)'}
START, END = '2023-01-01', '2026-09-30'
LABS = {'OpenAI': r'\bopenai\b', 'Anthropic': r'\banthropic\b', 'Google': r'\bgoogle\b|deepmind',
        'Meta': r'\bmeta\b', 'Microsoft': r'\bmicrosoft\b', 'xAI': r'\bxai\b', 'Alibaba': r'\balibaba\b|\bqwen\b',
        'DeepSeek': r'deepseek', 'Mistral': r'\bmistral\b', 'Moonshot': r'moonshot', 'Zhipu': r'zhipu|z\.ai',
        'MiniMax': r'minimax', 'NVIDIA': r'\bnvidia\b'}
CARD = re.compile(r'href="([^"]+?(?:system[-_ ]?card|model[-_ ]?card|technical[-_ ]?report|tech[-_ ]?report)[^"]*?)"', re.I)
HEALTH = re.compile(r'\b(HealthBench|MedQA|MedMCQA|PubMedQA|USMLE|MedXpertQA|Med-?HALT|MedCalc|AfriMed|'
                    r'medical|clinical|health ?care|patient|physician|anatomy|college medicine|professional medicine|'
                    r'medical genetics|clinical knowledge)\b', re.I)


def lab(org):
    return next((k for k, p in LABS.items() if re.search(p, org, re.I)), None)


def select():
    rows = list(csv.DictReader(SNAPSHOT.open(encoding='utf-8')))
    out = []
    for r in rows:
        if START <= r['Publication date'][:10] <= END and 'Language' in r['Domain'] and lab(r['Organization']):
            link = re.split(r'[\s,;]+', r['Link'].strip())[0] if r['Link'].strip() else ''
            out.append({'model': r['Model'], 'lab': lab(r['Organization']), 'organization': r['Organization'],
                        'date': r['Publication date'][:10], 'link': link,
                        'doc_id': hashlib.sha1(link.encode()).hexdigest()[:12] if link else ''})
    with SEL.open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f'{len(out)} models; {len({o["link"] for o in out if o["link"]})} distinct documents')


def to_text(content, ctype):
    if content[:4] == b'%PDF' or 'pdf' in ctype:
        tmp = RAW / '_tmp.pdf'
        tmp.write_bytes(content)
        return subprocess.run(['pdftotext', str(tmp), '-'], capture_output=True, text=True, timeout=120).stdout
    html = content.decode('utf-8', 'ignore')
    html = re.sub(r'(?is)<(script|style)\b.*?</\1>', ' ', html)
    return re.sub(r'\s+', ' ', re.sub(r'(?s)<[^>]+>', ' ', html))


def get(url):
    if 'arxiv.org/abs/' in url:
        url = url.replace('/abs/', '/pdf/')
    try:
        r = requests.get(url, headers=UA, timeout=60, allow_redirects=True)
        if r.ok and len(r.content) > 2000:
            return r, 'direct'
    except Exception:
        pass
    try:                                    # Internet Archive copy when the site blocks automated access
        r = requests.get(f'https://web.archive.org/web/2026id_/{url}', headers=UA, timeout=90)
        if r.ok and len(r.content) > 2000:
            return r, 'archive'
    except Exception:
        pass
    return None, 'failed'


def fetch():
    RAW.mkdir(exist_ok=True)
    docs = {}
    for r in csv.DictReader(SEL.open(encoding='utf-8')):
        if r['link']:
            docs[r['doc_id']] = r['link']
    log = []
    for i, (did, url) in enumerate(docs.items()):
        out = RAW / f'{did}.txt'
        if out.exists():
            log.append({'doc_id': did, 'url': url, 'status': 'cached'})
            continue
        r, how = get(url)
        entry = {'doc_id': did, 'url': url, 'status': how}
        if r is not None:
            text = to_text(r.content, r.headers.get('content-type', ''))
            linked = []
            is_html = r.content[:4] != b'%PDF' and '<html' in r.text[:2000].lower()
            if is_html:
                for m in CARD.findall(r.text)[:3]:              # system card or technical report linked from a launch page
                    u = requests.compat.urljoin(r.url, m)
                    r2, how2 = get(u)
                    if r2 is not None:
                        text += f'\n\n[linked document: {u}]\n' + to_text(r2.content, r2.headers.get('content-type', ''))
                        linked.append(u)
            out.write_text(f'[source: {url}; {how}]\n' + text)
            entry.update({'chars': len(text), 'linked_documents': linked})
        log.append(entry)
        print(i + 1, len(docs), how, url[:80], flush=True)
        time.sleep(1)
    (HERE / 'frontier_reports_fetch_log.json').write_text(json.dumps(log, indent=1))
    print('fetch:', {s: sum(1 for e in log if e['status'] == s) for s in ('direct', 'archive', 'cached', 'failed')})


def scan():
    sel = list(csv.DictReader(SEL.open(encoding='utf-8')))
    rows = []
    for did in sorted({r['doc_id'] for r in sel if r['doc_id']}):
        p = RAW / f'{did}.txt'
        if not p.exists():
            rows.append({'doc_id': did, 'fetched': False, 'health_terms': ''})
            continue
        text = p.read_text()
        terms = sorted({m.group(0).lower() for m in HEALTH.finditer(text)})
        rows.append({'doc_id': did, 'fetched': True, 'chars': len(text), 'health_terms': '; '.join(terms)})
    with (HERE / 'frontier_reports_health.csv').open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=['doc_id', 'fetched', 'chars', 'health_terms'])
        w.writeheader()
        w.writerows(rows)
    bench = re.compile(r'healthbench|medqa|medmcqa|pubmedqa|usmle|medxpertqa|med-?halt|medcalc|afrimed|clinical knowledge|college medicine|professional medicine|medical genetics', re.I)
    print(f"documents: {len(rows)}; fetched {sum(r['fetched'] for r in rows)}; mentioning any health term "
          f"{sum(bool(r['health_terms']) for r in rows)}; naming a health benchmark {sum(bool(bench.search(r['health_terms'])) for r in rows)}")


DOM = {'OpenAI': r'openai\.com', 'Anthropic': r'anthropic\.com', 'Google': r'google|deepmind|googleapis',
       'Meta': r'meta\.com|llama\.com|facebook', 'Alibaba': r'qwen|alibaba|aliyun', 'NVIDIA': r'nvidia|Efficient-Large-Model',
       'xAI': r'x\.ai', 'DeepSeek': r'deepseek', 'Mistral': r'mistral', 'Moonshot': r'moonshot|kimi',
       'Zhipu': r'z\.ai|zhipu|bigmodel', 'MiniMax': r'minimax', 'Microsoft': r'microsoft'}
CANON = [('HealthBench Professional', r'HealthBench Professional'), ('HealthBench', r'HealthBench(?! Professional)'),
         ('PhysicianBench', r'PhysicianBench'), ('HealthAdminBench', r'HealthAdminBench'), ('MedXpertQA', r'MedXpertQA'),
         ('MedQA', r'MedQA'), ('MedMCQA', r'MedMCQA'), ('PubMedQA', r'PubMedQA|PubmedQA'), ('BioASQ', r'BioASQ'),
         ('LiveQA', r'LiveQA'), ('MedicationQA', r'MedicationQA'), ('HealthSearchQA', r'HealthSearchQA'),
         ('MMLU (medical subjects)', r'MMLU[ -]?(?:Clinical|Medical|Anatomy|Professional|College)|[Cc]linical [Kk]nowledge|'
                                     r'[Cc]ollege [Mm]edicine|[Pp]rofessional [Mm]edicine|[Mm]edical [Gg]enetics'),
         ('Med-PaLM 2 adversarial questions', r'[Aa]dversarial questions'),
         ('USMLE practice questions', r'USMLE multiple-choice practice questions|USMLE \[70\]'),
         ('MKSAP', r'Medical Knowledge Self-Assessment Program'), ('SLAKE', r'SLAKE'), ('PMC-VQA', r'PMC-VQA'),
         ('PathVQA', r'PathVQA'), ('VQA-RAD', r'VQA-RAD'), ('CheXpert', r'CheXpert'),
         ('LAB-Bench2 (clinical-trial questions)', r'clinical-trial questions')]
BIBLIO = re.compile(r'^\[\d+\]\s+\S|et al\.|Proceedings|arXiv preprint|https?://|^[A-Z][a-z]+, [A-Z]\.')


def sections(did, lab, log, browser):
    out = []
    p = RAW / f'{did}.txt'
    if p.exists() and log.get(did, {}).get('status') != 'failed':
        t = p.read_text()
        if len(t) >= 3000:
            parts = re.split(r'\n\n\[linked document: ([^\]]+)\]\n', t)
            out.append((t.split('\n', 1)[0], parts[0]))
            for i in range(1, len(parts), 2):
                if re.search(DOM[lab], parts[i], re.I) or 'arxiv' in parts[i]:
                    out.append((parts[i], parts[i + 1]))
    for f in sorted(RAW.glob(f'{did}__card*.txt')):
        t = f.read_text()
        out.append((t.split('\n', 1)[0], t))
    for x in browser.get(did, []):
        if x.get('health'):
            out.append((x.get('url') or x.get('linked_card'), '\n'.join(x['health'])))
    return out


def benchmarks():
    from collections import defaultdict
    sel = list(csv.DictReader(SEL.open(encoding='utf-8')))
    models, labs = defaultdict(list), {}
    for r in sel:
        if r['doc_id']:
            models[r['doc_id']].append(r['model'])
            labs[r['doc_id']] = r['lab']
    log = {e['doc_id']: e for e in json.loads((HERE / 'frontier_reports_fetch_log.json').read_text())}
    browser = defaultdict(list)
    for line in (HERE / 'frontier_reports_browser.jsonl').open():
        x = json.loads(line)
        browser[x['doc_id']].append(x)
    docs = list(csv.DictReader((HERE / 'frontier_reports_documents.csv').open(encoding='utf-8')))
    recs = []
    for d in docs:
        if d['retrieved'] != 'True':
            continue
        did, found = d['doc_id'], {}
        for src, txt in sections(did, labs[did], log, browser):
            lines = [re.sub(r'\s+', ' ', l).strip() for l in re.split(r'\n+', txt)]
            for name, pat in CANON:
                if name == 'Med-PaLM 2 adversarial questions' and 'Med-PaLM 2' not in ' '.join(models[did]):
                    continue
                hits = [l for l in lines if re.search(pat, l)]
                good = [l for l in hits if not BIBLIO.search(l)]
                if not good:
                    continue
                best = max(good, key=lambda l: (bool(re.search(r'\d', l)), bool(re.search(r'evaluat|score|accura|result|use', l, re.I))))
                found.setdefault(name, (best[:300], (src or '')[:120]))
        for name, (q, src) in found.items():
            recs.append({'doc_id': did, 'lab': labs[did], 'models': '; '.join(models[did]), 'benchmark': name, 'quote': q,
                         'section_source': src})
    with (HERE / 'frontier_benchmarks.csv').open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(recs[0]))
        w.writeheader()
        w.writerows(recs)
    agg = defaultdict(lambda: [set(), set()])
    for r in recs:
        agg[r['benchmark']][0].add(r['doc_id'])
        agg[r['benchmark']][1].add(r['lab'])
    dids = {r['doc_id'] for r in recs}
    print(f'{len(recs)} benchmark records in {len(dids)} documents ({sum(len(models[d]) for d in dids)} models)')
    for k, (ds, ls) in sorted(agg.items(), key=lambda kv: (-len(kv[1][1]), -len(kv[1][0]))):
        print(f'  {k:38s} documents {len(ds):2d} | labs {len(ls)}: {", ".join(sorted(ls))}')


if __name__ == '__main__':
    {'select': select, 'fetch': fetch, 'scan': scan, 'benchmarks': benchmarks}[sys.argv[1]]()
