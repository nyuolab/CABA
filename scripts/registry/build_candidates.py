"""CABA v1.0 (docs/protocol.md, sections 1-2): merge the benchmarks named by the 13 evaluation suites and by
frontier lab reports into one list, and apply the criteria that can be decided before download.

Inputs: suite components (registry/suite_components.csv, rows whose sources include one of SUITES;
compiled from each suite's paper, repository or leaderboard page, with an evidence URL per row) and
registry/frontier_reports/frontier_benchmarks.csv (frontier_reports.py benchmarks).

Merging: names are normalized (case, punctuation, parenthetical remarks); ALIAS maps alternative names
and variants or subsets to their parent benchmark.

Criteria decided here, each with the reason recorded:
  public       access recorded as credentialed, private, held out or on request, or unreleased
  english      no English version recorded
  text         image, video or audio items only
  health       drawn from a general-domain benchmark, or no health content (GENERAL)
  single       agent environments and token-labelling tasks (AGENT)
Benchmarks not excluded here go to the download check, which settles criteria 1-3 and 5 on the items.

Output: registry/candidates_175.csv (one row per merged benchmark), registry/candidates_counts.json.
"""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
import sys  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from caba_paths import FRONTIER, MANIFESTS, REG, REPORTS_RAW  # noqa: E402

HERE = REG
SUITES = ['MedHELM', 'MultiMedQA', 'MedS-Bench', 'ClinicBench', 'MIRAGE', 'Medmarks', 'BRIDGE', 'MEDIC', 'MMedBench',
          'CLUE', 'MedBench', 'HealthBench', 'MAST']
# alternative names, variants and subsets -> parent benchmark (normalized form on the left)
ALIAS = {
    'healthbenchhard': 'HealthBench', 'healthbenchconsensus': 'HealthBench',
    'headqav2': 'HEAD-QA', 'medxpertqatext': 'MedXpertQA', 'medxpertqamm': 'MedXpertQA',
    'trec2017liveqamedical': 'LiveQA', 'liveqa': 'LiveQA',
    'bioasqyn': 'BioASQ', 'bioasq': 'BioASQ',
    'mmluanatomy': 'MMLU', 'mmluclinicalknowledge': 'MMLU', 'mmlucollegemedicine': 'MMLU', 'mmlumedicalgenetics': 'MMLU',
    'mmluprofessionalmedicine': 'MMLU', 'mmlucollegebiology': 'MMLU', 'mmlumed': 'MMLU', 'mmlumedicalsubjects': 'MMLU',
    'mmlupro': 'MMLU-Pro', 'supergpqa': 'SuperGPQA',
    'mtsdialogmediqa2023': 'MTS-Dialog', 'mtsamples': 'MTSamples',
    'problemsummaryprobsum': 'ProbSum',
}
GENERAL = {'MMLU', 'MMLU-Pro', 'SuperGPQA', 'GPQA', "Humanity's Last Exam", 'TruthfulQA', 'C-Eval', 'CMMLU',
           'GSM8K', 'IFEval', 'AIME', 'ToxiGen', 'LAB-Bench2'}
AGENT = {'MedAgentBench v2', 'PhysicianBench', 'AgentClinic', 'HealthAdminBench'}
IMAGE = {'SLAKE', 'PathVQA', 'VQA-RAD', 'PMC-VQA', 'CheXpert', 'ReXrank Mini', 'Diverse Dermatology Images', 'MRA-MIDAS'}
UNRELEASED = {'NOHARM-Mind', 'PACT'}


def norm(s):
    s = re.sub(r'\(.*?\)', ' ', s or '')
    return re.sub(r'[^a-z0-9]+', '', s.lower())


def canon(name):
    n = norm(name)
    if n in ALIAS:
        return ALIAS[n]
    for k, v in ALIAS.items():                     # prefix aliases, e.g. "MMLU Clinical Knowledge (…)"
        if n.startswith(k) and len(k) >= 6:
            return v
    if n.startswith('aime'):
        return 'AIME'
    return re.sub(r'\s*\(.*?\)\s*', ' ', name).strip()


def main():
    rows = defaultdict(lambda: {'suites': set(), 'labs': set(), 'documents': set(), 'names': set(), 'meta': {}})
    for r in csv.DictReader((REG / 'suite_components.csv').open(encoding='utf-8')):
        ss = {s[3:] for s in r['sources'].split(';') if s.startswith('S1:')} & set(SUITES)
        if not ss:
            continue
        c = canon(r['name'])
        rows[c]['suites'] |= ss
        rows[c]['names'].add(r['name'])
        for k in ('access', 'language', 'modality', 'item_format', 'url_data', 'url_paper', 'license', 'n_items_eval'):
            if r.get(k) and not rows[c]['meta'].get(k):
                rows[c]['meta'][k] = r[k]
    for r in csv.DictReader((FRONTIER / 'frontier_benchmarks.csv').open(encoding='utf-8')):
        name = {'MMLU (medical subjects)': 'MMLU', 'LAB-Bench2 (clinical-trial questions)': 'LAB-Bench2'}.get(r['benchmark'], r['benchmark'])
        c = canon(name)
        rows[c]['labs'].add(r['lab'])
        rows[c]['documents'].add(r['doc_id'])
        rows[c]['names'].add(r['benchmark'])
    out = []
    for c, v in sorted(rows.items()):
        m = v['meta']
        acc, lang, mod = (m.get('access') or '').lower(), (m.get('language') or '').lower(), (m.get('modality') or '').lower()
        reason = ''
        if c in GENERAL:
            reason = 'health: general-domain or no health content'
        elif c in AGENT:
            reason = 'single: agent environment'
        elif c in IMAGE or (mod and 'text' not in mod):
            reason = 'text: image or non-text items'
        elif c in UNRELEASED:
            reason = 'public: not released'
        elif acc in ('credentialed', 'private', 'held_out', 'request'):
            reason = f'public: {acc}'
        elif lang and not re.search(r'\ben\b|english|multil', lang):
            reason = f'english: {m.get("language")}'
        out.append({'benchmark': c, 'suites': '; '.join(sorted(v['suites'])), 'n_suites': len(v['suites']),
                    'labs': '; '.join(sorted(v['labs'])), 'n_labs': len(v['labs']), 'n_frontier_documents': len(v['documents']),
                    'names_in_sources': ' | '.join(sorted(v['names'])), 'access': m.get('access', ''), 'language': m.get('language', ''),
                    'modality': m.get('modality', ''), 'item_format': m.get('item_format', ''), 'url_data': m.get('url_data', ''),
                    'url_paper': m.get('url_paper', ''), 'excluded_before_download': reason})
    with (REG / 'candidates_175.csv').open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    from collections import Counter
    counts = {'benchmarks_named': len(out),
              'from_suites_only': sum(1 for o in out if o['n_suites'] and not o['n_labs']),
              'from_frontier_only': sum(1 for o in out if o['n_labs'] and not o['n_suites']),
              'from_both': sum(1 for o in out if o['n_labs'] and o['n_suites']),
              'excluded_before_download': dict(Counter(o['excluded_before_download'].split(':')[0] for o in out if o['excluded_before_download'])),
              'to_download_check': sum(1 for o in out if not o['excluded_before_download'])}
    (REG / 'candidates_counts.json').write_text(json.dumps(counts, indent=1))
    print(json.dumps(counts, indent=1))


if __name__ == '__main__':
    main()
