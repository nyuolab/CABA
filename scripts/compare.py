"""Compare each CABA benchmark with real clinical use, as reported in the paper.

Reads labels/<slug>.jsonl and reference/rcq_aggregate.json; writes summary/per_benchmark.csv and
summary/medians.json. Overlap with real use = one minus the total variation distance between a benchmark's
task-category distribution and the RCQ distribution. Medians and interquartile ranges are across benchmarks; the
95% CI for the difference between group medians is a percentile bootstrap over benchmarks within each group
(4,000 replicates, seed 20261004).
"""
import csv
import json
from collections import Counter

import numpy as np
import pandas as pd

from caba_paths import LABELS, REF_FILE, REG, SEED, SUMMARY

TASK_GROUP = {
    'Documentation & workflow': 'Documentation & administration', 'Coding & administrative': 'Documentation & administration',
    'Foundational knowledge': 'Knowledge retrieval', 'Drug information & pharmacotherapy': 'Knowledge retrieval',
    'Treatment & management': 'Clinical reasoning', 'Diagnosis & differential': 'Clinical reasoning',
    'Test & result interpretation': 'Clinical reasoning', 'Procedural guidance': 'Clinical reasoning',
    'Patient education & communication': 'Clinical reasoning', 'Other': 'Other'}
KINDS = ['Documentation & administration', 'Knowledge retrieval', 'Clinical reasoning', 'Other']
TASKS = list(TASK_GROUP)


def main():
    ref = json.loads(REF_FILE.read_text())
    rcq = ref['task_category']
    reg = {r['benchmark']: r for r in csv.DictReader((REG / 'caba_v1.0.csv').open(encoding='utf-8'))}
    names = {r['slug']: r['benchmark'] for r in csv.DictReader((REG / 'download_checked_73.csv').open(encoding='utf-8'))
             if r['status'] == 'include'}
    rows = []
    for slug, name in sorted(names.items()):
        labs = [json.loads(l)['annotation'] for l in (LABELS / f'{slug}.jsonl').open(encoding='utf-8')]
        n = len(labs)
        task = Counter(a['task_category'] for a in labs)
        share = {t: task.get(t, 0) / n for t in TASKS}
        kind = {k: sum(share[t] for t in TASKS if TASK_GROUP[t] == k) for k in KINDS}
        r = reg[name]
        frontier = r['used_in_frontier_model_reports'] == 'True'
        practice = r['in_suite_meant_to_resemble_practice'] == 'True'
        rows.append({'slug': slug, 'benchmark': name, 'n_labelled': n,
                     'group': 'both' if frontier and practice else 'frontier' if frontier else 'practice' if practice else 'other',
                     'frontier_model_reports': frontier, 'practice_suite': practice,
                     'evaluation_suites': r['evaluation_suites'], 'frontier_model_reports_by': r['frontier_model_reports_by'],
                     'overlap_with_rcq_task_mix': sum(min(share[t], rcq[t]) for t in TASKS),
                     **{f'kind:{k}': kind[k] for k in KINDS},
                     'doc_admin': kind['Documentation & administration'], 'diagnosis': share['Diagnosis & differential'],
                     **{f'task:{t}': share[t] for t in TASKS}})
    df = pd.DataFrame(rows)
    SUMMARY.mkdir(exist_ok=True)
    df.to_csv(SUMMARY / 'per_benchmark.csv', index=False, float_format='%.6f')

    def q(s):
        return {'median': float(s.median()), 'q1': float(s.quantile(.25)), 'q3': float(s.quantile(.75))}
    groups = {'frontier': df['frontier_model_reports'], 'practice': df['practice_suite'], 'all': df['n_labelled'] > 0}
    out = {'even_spread_overlap': ref['even_spread_overlap'], 'rcq_doc_admin': ref['documentation_and_administration'],
           'rcq_diagnosis': ref['diagnosis'], 'groups': {}}
    for g, m in groups.items():
        s = df[m]
        out['groups'][g] = {'n': int(len(s)), 'overlap': q(s['overlap_with_rcq_task_mix']), 'doc_admin': q(s['doc_admin']),
                            'diagnosis': q(s['diagnosis']), 'n_doc_ge_5pct': int((s['doc_admin'] >= .05).sum()),
                            'n_diag_above_rcq': int((s['diagnosis'] > ref['diagnosis']).sum())}
    rng = np.random.default_rng(SEED)
    df = df.sort_values('overlap_with_rcq_task_mix', ascending=False)   # the paper's table order (fixes bootstrap draws)
    f = df.loc[df['frontier_model_reports'], 'overlap_with_rcq_task_mix'].values
    p = df.loc[df['practice_suite'], 'overlap_with_rcq_task_mix'].values
    d = [np.median(rng.choice(p, len(p))) - np.median(rng.choice(f, len(f))) for _ in range(4000)]
    out['practice_minus_frontier_median_overlap'] = {'diff': float(np.median(p) - np.median(f)),
                                                     'lo': float(np.percentile(d, 2.5)), 'hi': float(np.percentile(d, 97.5))}
    (SUMMARY / 'medians.json').write_text(json.dumps(out, indent=1))
    for g, v in out['groups'].items():
        print(f"{g:9s} n={v['n']:2d} median overlap {100 * v['overlap']['median']:.1f}% "
              f"(IQR {100 * v['overlap']['q1']:.1f}-{100 * v['overlap']['q3']:.1f}) | median doc/admin "
              f"{100 * v['doc_admin']['median']:.1f}% | n doc>=5% {v['n_doc_ge_5pct']}")
    dd = out['practice_minus_frontier_median_overlap']
    print(f"practice - frontier: {100 * dd['diff']:.1f} points (95% CI {100 * dd['lo']:.1f} to {100 * dd['hi']:.1f})")


if __name__ == '__main__':
    main()
