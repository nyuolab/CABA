"""CABA v1.0: sample and render items (docs/protocol.md, section 3) for benchmarks hosted on GitHub and similar.

No LLM calls, no API keys. Reads local downloads, writes $CABA_DATA/rendered/<slug>.jsonl and adds a
"rendering" block to registry/manifests/<slug>.json.
"""
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from caba_paths import DATA as _DATA, MANIFESTS as _MAN, RAW as _RAW  # noqa: E402
import glob
import json
import os
import random
import re
import statistics
import warnings
import xml.etree.ElementTree as ET

warnings.filterwarnings('ignore')
import pandas as pd

HOME = os.path.expanduser('~')
D = str(_DATA)
RAW = str(_RAW)
MAN = str(_MAN)
OUT = os.path.join(D, 'rendered')
SEED = 20261004
os.makedirs(OUT, exist_ok=True)


def norm(s):
    return str(s).replace('\r\n', '\n').replace('\r', '\n')


def mcq(question, options):
    """options: list of (letter, text)."""
    return norm(question).strip() + '\n' + '\n'.join(f'{k}. {norm(v).strip()}' for k, v in options)


# --------------------------------------------------------------------------- templates (verbatim)
HELM = 'https://github.com/stanford-crfm/helm/blob/63754d05db6f874e41a395880fb573890a13e791/src/helm/benchmark/run_specs/medhelm_run_specs.py'
HELM_ACI_INSTR = ("Summarize the conversation to generate a clinical note with four sections:\n"
                  "1. HISTORY OF PRESENT ILLNESS\n2. PHYSICAL EXAM\n3. RESULTS\n4. ASSESSMENT AND PLAN\n\n"
                  "The conversation is:")
HELM_MEDEC_INSTR = ("The following is a medical narrative about a patient. "
                    "You are a skilled medical doctor reviewing the clinical text. "
                    "The text is either correct or contains one error. "
                    "The text has a sentence per line. Each line starts with the "
                    "sentence ID, followed by a space character then the sentence to check. "
                    "Check every sentence of the text. "
                    "If the text is correct return the following output: CORRECT. "
                    "If the text has a medical error, return the sentence ID of the "
                    "sentence containing the error, followed by a space, "
                    "and a corrected version of the sentence.")
HELM_MTS_INSTR = "Given various information about a patient, return a reasonable treatment plan for the patient."

CLUE_MEQSUM_SRC = 'https://github.com/TIO-IKIM/CLUE/blob/2de4314cfaf2651a362a2df2ac8336ca0937ea52/eval/eval_meqsum.py'
CLUE_SYS = ("You are a highly skilled assistant, specifically trained to assist patients. Your primary responsibility "
            "will be to summarize patient inquiries as concise question. You will be given such a patient inquiry. "
            "You will be expected to summarize and rewrite the inquiry as a concise question. Only write out the "
            "question. Do not add any other text.")
CLUE_USER = """--------------PATIENT INQUIRY--------------
{CHQ}
--------------END PATIENT INQUIRY--------------"""

CB_TR = ('"task": "Your task is to list the medications based on the provided content related to the symptom or '
         'disease mentioned in the question. Understand the question, extract relevant information, analyze it, and '
         'provide a concise and accurate answer.",\n'
         '"answer format": Analysis: Provide an analysis that logically leads to the answer based on the relevant '
         'content. Final Answer: Provide the final answer, which should be a list of medications related to the '
         'symptom or disease.\n'
         '"not to dos": "Do not make assumptions not supported by the content. Avoid providing personal opinions or '
         'interpretations. Summarize and interpret the information as objectively and accurately as possible. You are '
         'providing an analysis, not diagnosing or treating medical conditions."')

MEDR_SRC = 'https://github.com/MAGIC-AI4Med/MedRBench/tree/ff60ab440afd2f2bc0c603b3a65d715ec83138a7/src/Inference/instructions'
SCT_SRC = 'https://github.com/SCT-Bench/sctpublic/blob/c2843137b36218eac3f47e76eaa559c9fe7973e9/modeling.py (data/templates/guideline.md + testcase.md)'
LH_SEP = '\n\n--------------\n\n'

MEDBULLETS_IMAGE_RULE = r'question text matches \bFigures?\s+[A-Z]\b (a lettered figure such as "Figure A" or "Figures A-E"; Medbullets releases no images)'


def helm_prompt(instructions, input_noun, input_text, output_noun, newline_after_input_noun=False):
    """HELM GenerationAdapter prompt with max_train_instances=0, exactly as HELM builds it:
    instructions_block = instructions + "\n" (format_instructions); eval block = input_prefix + input + "\n"
    + output_prefix.rstrip(); blocks joined by instance_prefix "\n"; no global prefix/suffix."""
    instr = instructions + "\n" if instructions else ""
    input_prefix = (f"{input_noun}:" + ("\n" if newline_after_input_noun else " ")) if input_noun else ""
    output_prefix = f"{output_noun}: " if output_noun else ""
    eval_block = input_prefix + input_text + "\n" + output_prefix.rstrip()
    return "\n".join(([instr] if instr else []) + [eval_block])


# --------------------------------------------------------------------------- loaders: list of dicts
def items_aci():
    out = []
    for t in ['clinicalnlp_taskB_test1', 'clinicalnlp_taskC_test2', 'clef_taskC_test3']:
        df = pd.read_csv(f'{D}/aci_bench/data/challenge_data/{t}.csv')
        for _, r in df.iterrows():
            req = helm_prompt(HELM_ACI_INSTR, 'Conversation', f'Doctor-patient dialogue:\n\n{norm(r.dialogue)}', 'Clinical Note')
            out.append(dict(item_id=r.encounter_id, component=t, request=req))
    return out, dict(rule='Full MedHELM prompt exactly as HELM builds it (generation adapter, zero-shot): instructions, blank line, "Conversation: Doctor-patient dialogue:" + dialogue, newline, final cue "Clinical Note:" (dialogues verified identical to HELM-pinned challenge_data_json at e75b383).',
                     template_source=HELM + ' (get_aci_bench_run_spec) and src/helm/benchmark/scenarios/aci_bench_scenario.py')


def items_bioasq():
    b = json.load(open(f'{D}/bioasq/benchmark.json'))['bioasq']
    out = [dict(item_id=k, component=None, request=mcq(v['question'], list(v['options'].items()))) for k, v in b.items()]
    return out, dict(rule='Multiple choice: question, then options one per line with their source letters (A. yes / B. no).', template_source='none')


def items_drug():
    df = pd.read_csv(f'{D}/drug_interaction_for_emerging_drugs/Drug-Interaction-for-Emerging-Drugs.csv')
    out = [dict(item_id=f'Drug-Interaction-for-Emerging-Drugs.csv:{i}', component=None, request=norm(r.question).strip()) for i, r in df.iterrows()]
    return out, dict(rule='Item text as released (the yes/no question); the ClinicBench Table 8 prompt was not applied because it contains an unpublished placeholder "(introduce what each Moderna COVID-19 Vaccine is ...)".', template_source='none')


def items_ehrsql():
    out = []
    for db in ['mimic_iii', 'eicu']:
        for x in json.load(open(f'{D}/ehrsql/dataset/ehrsql/{db}/test.json')):
            out.append(dict(item_id=x['id'], component=db, request=norm(x['question']).strip()))
    return out, dict(rule='Item text as released: the natural-language question only (no schema, no SQL).', template_source='none')


def items_noharm():
    out = []
    for l in open(f'{RAW}/MAST/donoharm/dataset/items.jsonl'):
        x = json.loads(l)
        out.append(dict(item_id=x['id'], component=None, request=norm(x['prompt']).strip()))
    return out, dict(rule='Item text as released: the case prompt (MAST NOHARM protocol is unprompted, empty template).', template_source='none')


def items_liveqa():
    root = ET.parse(f'{D}/liveqa/TestDataset/TREC-2017-LiveQA-Medical-Test-Questions-w-summaries.xml').getroot()
    out = []
    for q in root.findall('.//NLM-QUESTION'):
        subj = norm(q.findtext('.//Original-Question/SUBJECT') or '').strip()
        msg = norm(q.findtext('.//Original-Question/MESSAGE') or '').strip()
        req = (subj + '\n' + msg) if subj else msg
        out.append(dict(item_id=q.attrib.get('qid'), component=None, request=req))
    return out, dict(rule='Item text as released: the original consumer question, SUBJECT line then MESSAGE (SUBJECT omitted when empty).', template_source='none')


def items_longhealth():
    d = json.load(open(f'{D}/longhealth/data/benchmark_v5.json'))
    out = []
    for pid, p in d.items():
        docs = LH_SEP.join(norm(p['texts'][k]).strip() for k in sorted(p['texts'], key=lambda s: int(s.split('_')[1])))
        for i, q in enumerate(p['questions']):
            req = docs + '\n\n' + mcq(q['question'], [(c.upper(), q[f'answer_{c}']) for c in 'abcde'])
            out.append(dict(item_id=f'{pid}:q{i}', component=None, request=req))
    return out, dict(rule='Vignette + question: all of the patient\'s documents in text_0..text_n order joined by the repo separator ("--------------"), a blank line, then the question and options A-E (no shuffling or truncation, unlike the repo runner).', template_source='none')


def items_medbullets():
    df = pd.read_csv(f'{D}/medbullets/medbullets/medbullets_op5.csv')
    out = []
    for i, r in df.iterrows():
        img = bool(re.search(r'\bFigures?\s+[A-Z]\b', str(r.question)))
        out.append(dict(item_id=f'medbullets_op5.csv:{i}', component=None, image=img,
                        request=mcq(r.question, [(k, r[f'op{k.lower()}']) for k in 'ABCDE'])))
    return out, dict(rule='Multiple choice (op5 file, as MedHELM uses): question, then options A-E one per line.', template_source='none',
                     image_rule=MEDBULLETS_IMAGE_RULE)


def items_medec():
    df = pd.read_csv(f'{D}/medec/MEDEC-MS/MEDEC-MS-TestSet-with-GroundTruth-and-ErrorType.csv').dropna(subset=['Text ID'])
    out = [dict(item_id=r['Text ID'], component=None,
                request=helm_prompt(HELM_MEDEC_INSTR, 'Clinical Note', norm(r.Sentences).strip(), 'Answer')) for _, r in df.iterrows()]
    return out, dict(rule='Full MedHELM prompt exactly as HELM builds it (generation adapter, zero-shot): instructions, blank line, "Clinical Note: " + sentence-numbered text, newline, final cue "Answer:" (test CSV identical to HELM-pinned commit 49c59dc).',
                     template_source=HELM + ' (get_medec_run_spec) and src/helm/benchmark/scenarios/medec_scenario.py')


def items_medicationqa():
    df = pd.read_excel(f'{D}/medicationqa/MedInfo2019-QA-Medications.xlsx')
    out = [dict(item_id=f'MedInfo2019-QA-Medications.xlsx:{i}', component=None, request=norm(r.Question).strip()) for i, r in df.iterrows()]
    return out, dict(rule='Item text as released: the consumer question.', template_source='none')


def items_mediqa():
    root = ET.parse(f'{D}/mediqa_qa/MEDIQA_Task3_QA/MEDIQA2019-Task3-QA-TestSet-wLabels.xml').getroot()
    out = [dict(item_id=q.attrib['QID'], component=None, request=norm(q.findtext('QuestionText')).strip()) for q in root.findall('.//Question')]
    return out, dict(rule='Item text as released: the consumer question alone (candidate answers omitted).', template_source='none')


def items_medqa():
    out = []
    for i, l in enumerate(open(f'{RAW}/MedQA/GBaker_phrases_no_exclude_test.jsonl')):
        x = json.loads(l)
        out.append(dict(item_id=f'GBaker_phrases_no_exclude_test.jsonl:{i}', component=None, request=mcq(x['question'], list(x['options'].items()))))
    return out, dict(rule='Multiple choice: question, then options A-D one per line.', template_source='none')


def items_medr():
    tdiag = open(f'{D}/medr_bench/src/Inference/instructions/oracle_diagnose.txt').read()
    ttx = open(f'{D}/medr_bench/src/Inference/instructions/treatment_plan_prompt.txt').read()
    out = []
    for comp, f, tpl in [('diagnosis', 'diagnosis_957_cases_with_rare_disease_491.json', tdiag),
                         ('treatment', 'treatment_496_cases_with_rare_disease_165.json', ttx)]:
        d = json.load(open(f'{D}/medr_bench/data/MedRBench/{f}'))
        for k, v in d.items():
            out.append(dict(item_id=k, component=comp, request=norm(tpl.replace('{case}', v['generate_case']['case_summary'])).strip()))
    return out, dict(rule='Repository prompt template filled exactly: oracle_diagnose.txt (diagnosis cases) or treatment_plan_prompt.txt (treatment cases) with {case} = generate_case.case_summary.',
                     template_source=MEDR_SRC + '/oracle_diagnose.txt and /treatment_plan_prompt.txt')


def items_medsafety():
    out = []
    for m in ['gpt4', 'llama2']:
        for c in range(1, 10):
            f = f'datasets/test/{m}/med_safety_demonstrations_category_{c}.csv'
            df = pd.read_csv(f'{D}/medsafetybench/{f}')
            for i, r in df.iterrows():
                out.append(dict(item_id=f'{f}:{i}', component=f'{m}/category_{c}', request=norm(r.harmful_medical_request).strip()))
    return out, dict(rule='Item text as released: the harmful medical request.', template_source='none')


def items_meqsum():
    df = pd.read_excel(f'{D}/meqsum/MeQSum_ACL2019_BenAbacha_Demner-Fushman.xlsx')
    out = [dict(item_id=str(r.File), component=None, request=CLUE_SYS + '\n\n' + CLUE_USER.format(CHQ=norm(r.CHQ).strip())) for _, r in df.iterrows()]
    return out, dict(rule='Instruction-style via the CLUE suite template (zero-shot): CLUE system prompt, blank line, then the user turn wrapping the consumer health question (CHQ).',
                     template_source=CLUE_MEQSUM_SRC)


def helm_mts(text):
    """MedHELM mtsamples_replicate: returns cleaned input or None if the note has no usable reference."""
    tu = text.upper()
    try:
        vals = [text.split(s)[1].split('\n', 1)[0].strip() if s in tu else None for s in ('PLAN:', 'SUMMARY:', 'FINDINGS:')]
    except IndexError:
        return None
    if not (vals[0] or vals[1] or vals[2]):
        return None
    return text.split('PLAN:')[0].strip() if 'PLAN:' in text else text


def items_mtsamples():
    out = []
    for p in sorted(glob.glob(f'{D}/mtsamples/mtsamples_processed/*.txt')):
        t = open(p, encoding='utf-8').read().strip()
        c = helm_mts(t)
        if c is None:
            continue
        out.append(dict(item_id='mtsamples_processed/' + os.path.basename(p), component='MedHELM mtsamples_replicate',
                         request=helm_prompt(HELM_MTS_INSTR, None, norm(c), 'Answer')))
    for comp in ['MTS.SFT.json', 'MTS-Temporal.SFT.json']:
        for x in json.load(open(f'{D}/bridge_open/Dataset/{comp}')):
            out.append(dict(item_id=f'{comp}:{x["id"]}', component=f'BRIDGE {comp}', lang=x.get('language'),
                            request=norm(x['instruction']).strip() + '\n\n' + norm(x['input']).strip()))
    return out, dict(rule='Pooled components. MedHELM items: full mtsamples_replicate prompt exactly as HELM builds it (instruction, blank line, note with PLAN section removed, newline, final cue "Answer:"; notes without a PLAN/SUMMARY/FINDINGS line skipped as in HELM). BRIDGE MTS and MTS-Temporal: instruction, blank line, input.',
                     template_source=HELM + ' (get_mtsamples_spec) and src/helm/benchmark/scenarios/mtsamples_replicate_scenario.py; BRIDGE items carry their own instruction')


def items_pharm():
    df = pd.read_excel(f'{D}/pharmacology_qa_for_emerging_drugs/Pharmacology-QA.xlsx')
    out = [dict(item_id=f'Pharmacology-QA.xlsx:{i}', component=None,
                request=mcq(r.question, [(k, r[f'option_{k}']) for k in 'ABCD'])) for i, r in df.iterrows()]
    return out, dict(rule='Multiple choice: question, then options A-D one per line.', template_source='none')


def items_pubmedqa():
    pq = json.load(open(f'{D}/pubmedqa/data/ori_pqal.json'))
    test = set(json.load(open(f'{D}/pubmedqa/data/test_ground_truth.json')))
    out = []
    for pmid, x in pq.items():
        if pmid not in test:
            continue
        ctx = '\n'.join(f'{lab.title()}. {norm(c).strip()}' for lab, c in zip(x['LABELS'], x['CONTEXTS']))
        out.append(dict(item_id=pmid, component=None, request=ctx + '\n\n' + norm(x['QUESTION']).strip()))
    return out, dict(rule='Vignette + question: abstract contexts (one "Label. text" line each, as in Lievin et al./MedHELM), a blank line, then the question; no options are released (answers are yes/no/maybe).', template_source='none')


def items_sct():
    guideline = open(f'{D}/sct_bench/data/templates/guideline.md').read()
    testcase = open(f'{D}/sct_bench/data/templates/testcase.md').read()
    tpl = guideline + testcase  # generate_prompt_template(reason=True, few_shot=False)
    df = pd.read_csv(f'{D}/sct_bench/data/sct_cleaned_full.csv')
    out = []
    for _, r in df.iterrows():
        req = tpl.replace('{{ scenario }}', str(r.sct_stem)).replace('{{ hypothesis }}', str(r.question)).replace('{{ additional information }}', str(r.additional_info))
        out.append(dict(item_id=str(r.question_id), component=r.source, request=norm(req).strip()))
    return out, dict(rule='Repository prompt template filled exactly (zero-shot, with-reason variant): guideline.md + testcase.md with scenario, hypothesis and additional information.',
                     template_source=SCT_SRC)


def items_treatment():
    import ast
    df = pd.read_csv(f'{D}/treatment_recommendation/Treatment-Recommendation.csv')
    out = []
    for _, r in df.iterrows():
        sym = ', '.join(ast.literal_eval(r.Symptom))
        content = norm(r.reason).strip()
        question = f'Which medications should be used to treat a patient with {r.disease} presenting with: {sym}?'
        req = CB_TR + f'\n"content": "{content}"\n"question": "{question}"'
        out.append(dict(item_id=str(r.idx), component=None, request=req))
    return out, dict(rule='ClinicBench published template (paper Table 8: "task", "answer format", "not to dos") filled verbatim; its "content" and "question" slots are not published, so content = the release\'s disease description (reason) and question = a sentence built from disease + Symptom list following the paper\'s task description.',
                     template_source='https://aclanthology.org/2024.emnlp-main.759.pdf (Table 8, Treatment Recommendation; Section 3 "ii) Treatment Recommendation")')


REG = {
    'aci_bench': items_aci, 'bioasq': items_bioasq, 'drug_interaction_for_emerging_drugs': items_drug,
    'ehrsql': items_ehrsql, 'first_do_noharm': items_noharm, 'liveqa': items_liveqa, 'longhealth': items_longhealth,
    'medbullets': items_medbullets, 'medec': items_medec, 'medicationqa': items_medicationqa, 'mediqa_qa': items_mediqa,
    'medqa': items_medqa, 'medr_bench': items_medr, 'medsafetybench': items_medsafety, 'meqsum': items_meqsum,
    'mtsamples': items_mtsamples, 'pharmacology_qa_for_emerging_drugs': items_pharm, 'pubmedqa': items_pubmedqa,
    'sct_bench': items_sct,
}


def run(slug):
    man_path = os.path.join(MAN, slug + '.json')
    man = json.load(open(man_path))
    items, info = REG[slug]()
    excl = {'non_english': 0, 'image': 0, 'duplicate': 0}
    seen, usable = set(), []
    for it in items:
        if it.get('lang') not in (None, 'en'):
            excl['non_english'] += 1
            continue
        if it.get('image'):
            excl['image'] += 1
            continue
        if it['request'] in seen:
            excl['duplicate'] += 1
            continue
        seen.add(it['request'])
        usable.append(it)
    if len(usable) <= 200:
        sample = list(usable)
    else:
        sample = random.Random(SEED).sample(usable, 200)
    with open(os.path.join(OUT, slug + '.jsonl'), 'w') as f:
        for it in sample:
            f.write(json.dumps({'benchmark': man['benchmark'], 'slug': slug, 'item_id': it['item_id'],
                                'component': it.get('component'), 'request': it['request'],
                                'n_chars': len(it['request'])}, ensure_ascii=False) + '\n')
    lens = [len(it['request']) for it in sample]
    rendering = {'rule': info['rule'], 'template_source': info['template_source'], 'n_usable': len(usable),
                 'n_sampled': len(sample), 'seed': SEED, 'excluded': excl}
    if 'image_rule' in info:
        rendering['image_rule'] = info['image_rule']
    rendering['mean_chars'] = round(statistics.mean(lens), 1)
    rendering['max_chars'] = max(lens)
    if slug == 'mtsamples':
        comp = {}
        for it in usable:
            comp[it['component']] = comp.get(it['component'], 0) + 1
        rendering['n_usable_by_component'] = comp
        scomp = {}
        for it in sample:
            scomp[it['component']] = scomp.get(it['component'], 0) + 1
        rendering['n_sampled_by_component'] = scomp
    man['rendering'] = rendering
    with open(man_path, 'w') as f:
        json.dump(man, f, indent=2, ensure_ascii=False)
    return rendering


if __name__ == '__main__':
    import sys
    slugs = sys.argv[1:] or list(REG)
    for s in slugs:
        r = run(s)
        print(f"{s:<38} usable={r['n_usable']:>5} sampled={r['n_sampled']:>4} mean={r['mean_chars']:>9} max={r['max_chars']:>6} excl={r['excluded']}")
