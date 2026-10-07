"""Apply the download check (docs/protocol.md, section 2) to the per-benchmark manifests in registry/manifests/
and write the final CABA list.

Each decision that is not read directly from a manifest is listed in DECISIONS with its reason, so every
inclusion and exclusion is traceable. Usable items exclude, where stated, non-English items, items that
need an image, and items not released.

Output: registry/download_checked_73.csv, registry/download_checked_counts.json.
"""
import csv
import json
from collections import Counter
from pathlib import Path
import sys  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from caba_paths import FRONTIER, MANIFESTS, REG, REPORTS_RAW  # noqa: E402

HERE = REG
DL = MANIFESTS
CAP = 200

# slug -> (status, reason). status: include | exclude:<criterion> | merge:<parent slug> | pending
DECISIONS = {
    'clinical_trial_protocol_summarization': ('exclude:public', 'items not released by MEDIC'),
    'referral_qa': ('exclude:public', 'items not released by ClinicBench (built from MIMIC-IV)'),
    'mksap': ('exclude:public', 'paid subscription (American College of Physicians)'),
    'gout_cc': ('exclude:public', 'restricted access with a signed data use agreement (PhysioNet)'),
    'soap_note': ('exclude:public', "MEDIC's 250-item test split is not released; a substitute cannot be verified"),
    'hospitalization_summarization': ('exclude:public', "built from MIMIC notes; the data's licence requires credentialed access, although ClinicBench reposts them"),
    'patient_education': ('exclude:public', "built from MIMIC notes; the data's licence requires credentialed access, although ClinicBench reposts them"),
    'seer_breast_cancer_treatment_planning': ('exclude:public', "SEER data require a data use agreement, although MedS-Bench redistributes them"),
    'expertqa': ('exclude:health', 'general-domain benchmark (32 fields); MEDIC uses its health subset'),
    'ddi_corpus': ('exclude:single', 'relation-labelling corpus; ClinicBench gives a prompt template but does not release instructions'),
    'gad_re': ('exclude:single', 'relation-labelling corpus; ClinicBench gives a prompt template but does not release instructions'),
    'ncbi_disease_corpus': ('exclude:single', 'entity-labelling corpus; ClinicBench gives a prompt template but does not release instructions'),
    'treatment_recommendation': ('exclude:single', "ClinicBench's prompt template leaves its slots unpublished, so items cannot be rendered as released"),
    'mmedbench': ('merge:medqa', 'English test set is the MedQA (US) test set, question for question'),
    'metamedqa': ('merge:medqa', '1,259 of 1,373 questions are MedQA questions (a modified MedQA)'),
}
# usable items where only part of the released set qualifies (approximate until the item-level pass)
USABLE = {
    'medbullets': (194, 'questions that do not refer to an unreleased figure'),
    'head_qa': (2675, 'English test questions without images'),
    'usmle_practice_questions': (322, 'questions without images (about 54 image items removed)'),
    'healthbench': (4250, 'English conversations (about 85%; language identification to confirm)'),
    'healthbench_professional': (470, 'English tasks (about 90%; language identification to confirm)'),
}


def main():
    rows = []
    for f in sorted(DL.glob('*.json')):
        m = json.loads(f.read_text())
        slug = f.stem
        status, reason = DECISIONS.get(slug, ('include', ''))
        if status == 'include':
            pub = str(m.get('public', '')).lower()
            if pub.startswith('no'):
                status, reason = 'exclude:public', m.get('public')
        n = m.get('n_items')
        try:
            n = int(str(n).replace(',', '').split()[0]) if n not in (None, '') else None
        except ValueError:
            n = None
        usable, note = USABLE.get(slug, (n, ''))
        rows.append({'slug': slug, 'benchmark': m.get('benchmark', slug), 'status': status, 'reason': reason,
                     'n_items_released': n, 'n_items_usable': usable if status == 'include' else '',
                     'n_items_sampled': min(CAP, usable) if status == 'include' and usable else '',
                     'usable_note': note, 'split': m.get('split', ''), 'source_type': m.get('source_type', ''),
                     'license': m.get('license', '')})
    with (REG / 'download_checked_73.csv').open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    inc = [r for r in rows if r['status'] == 'include']
    counts = {'download_check': len(rows),
              'status': dict(Counter(r['status'].split(':')[0] + (':' + r['status'].split(':')[1] if r['status'].startswith('exclude') else '') for r in rows)),
              'included': len(inc), 'items_to_annotate': sum(r['n_items_sampled'] or 0 for r in inc)}
    (REG / 'download_checked_counts.json').write_text(json.dumps(counts, indent=1))
    print(json.dumps(counts, indent=1))
    print('included:', ', '.join(f"{r['benchmark']} ({r['n_items_sampled']})" for r in inc))


if __name__ == '__main__':
    main()
