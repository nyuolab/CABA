"""CABA v1.0 render (docs/protocol.md, section 3) for 15 benchmarks hosted on journal sites, project pages and
other hosts. No LLM calls, no API keys. Writes $CABA_DATA/rendered/<slug>.jsonl."""
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from caba_paths import DATA as _DATA, MANIFESTS as _MAN, RAW as _RAW  # noqa: E402
import json, os, re, sys, random, statistics, tarfile, csv, types, importlib.util, tempfile
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
H = str(_DATA); OUT = os.path.join(H, 'rendered'); os.makedirs(OUT, exist_ok=True)
MAN = str(_MAN)
RAW = str(_RAW)
SEED = 20261004
HELM_C = '63754d05db6f874e41a395880fb573890a13e791'
HELM_RS = f'https://github.com/stanford-crfm/helm/blob/{HELM_C}/src/helm/benchmark/run_specs/medhelm_run_specs.py'
MEDS_RULE = 'instruction-style (MedS-Bench): the task Definition, a blank line, then the instance input (few-shot examples and outputs omitted)'

def norm(s): return str(s).replace('\r\n', '\n').replace('\r', '\n')

def meds(slug, files):
    out = []
    for comp, path in files:
        d = json.load(open(path))
        instr = ' '.join(x.strip() for x in d['Definition']) if isinstance(d['Definition'], list) else str(d['Definition']).strip()
        for i, x in enumerate(d['Instances']):
            out.append(dict(item_id=x.get('id') or f'{os.path.basename(path)}:{i}', component=comp,
                            request=instr + '\n\n' + norm(x['input']).strip()))
    return out, dict(rule=MEDS_RULE, template_source='none (instruction and input as released in the MedS-Bench task files)')

def M(slug, rel, sub='MedS-Bench'): return f'{H}/{slug}/{sub}/{rel}'

def items_ade(): return meds('ade_corpus', [(None, M('ade_corpus', 'task29_drug_dose_extraction.json'))])
def items_bc4(): return meds('bc4chemd', [(None, M('bc4chemd', 'task125_test_bc4chem_named_enetity_recognition.json'))])
def items_bc5(): return meds('bc5cdr', [('task126_bc5chem', M('bc5cdr', 'task126_test_bc5chem_named_enetity_recognition.json')),
                                        ('task127_bc5disease', M('bc5cdr', 'task127_test_bc5disease_named_enetity_recognition.json'))])
def items_pico(): return meds('ebm_nlp_pico_extraction', [(c, M('ebm_nlp_pico_extraction', f'{c}.json')) for c in ['task1_participant_extraction', 'task2_intervention_extraction', 'task3_outcome_extraction']])
def items_hoc(): return meds('hallmarks_of_cancer', [(None, M('hallmarks_of_cancer', 'task106_hoc_text_classification.json'))])
def items_s800(): return meds('species_800', [(None, M('species_800', 'task128_test_species800_named_enetity_recognition.json'))])
def items_rct(): return meds('rct_text', [(None, M('rct_text', 'task110_rct_text_summurization.json', 'MedS-Bench-SPLIT'))])

_DET = None
def lang(text):
    """lingua rule: non-English only if the top language is not ENGLISH with confidence >= 0.80; else 'en'."""
    global _DET
    from lingua import LanguageDetectorBuilder, Language
    if _DET is None:
        _DET = LanguageDetectorBuilder.from_all_languages().with_preloaded_language_models().build()
    vals = _DET.compute_language_confidence_values(text)
    if vals and vals[0].language != Language.ENGLISH and vals[0].value >= 0.80:
        return vals[0].language.name.lower()
    return 'en'

LINGUA_VERSION = '2.1.1'
CONV_RULE = ('conversation: the first user turn only; language identified with lingua-language-detector 2.1.1 '
             '(LanguageDetectorBuilder.from_all_languages().with_preloaded_language_models().build()); an item is non-English only if '
             'compute_language_confidence_values on the first user turn gives a top language other than ENGLISH with confidence >= 0.80, '
             'every other item (including short ones) counts as English')
def items_hb():
    out = []
    for i, l in enumerate(open(f'{H}/healthbench/2025-05-07-06-14-12_oss_eval.jsonl')):
        r = json.loads(l); fu = next(m['content'] for m in r['prompt'] if m['role'] == 'user')
        out.append(dict(item_id=r['prompt_id'], component=None, request=norm(fu).strip(), lang=lang(fu)))
    return out, dict(rule=CONV_RULE, template_source='none')
def items_hbp():
    out = []
    for i, l in enumerate(open(f'{RAW}/HealthBench_Professional/healthbench_professional_eval.jsonl')):
        r = json.loads(l); fu = next(m['content'] for m in r['conversation']['messages'] if m['role'] == 'user')
        out.append(dict(item_id=r['id'], component=None, request=norm(fu).strip(), lang=lang(fu)))
    return out, dict(rule=CONV_RULE, template_source='none')

def items_hsqa():
    import openpyxl
    wb = openpyxl.load_workbook(f'{H}/healthsearchqa/41586_2023_6291_MOESM6_ESM.xlsx', read_only=True)
    ws = wb['All HealthSearchQA Questions']; out = []
    for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
        q = row[0] if row else None
        if q is None or not str(q).strip(): continue
        out.append(dict(item_id=f'All HealthSearchQA Questions:row{i}', component=None, request=norm(q).strip()))
    return out, dict(rule='otherwise: the consumer question as released (sheet "All HealthSearchQA Questions")', template_source='none')

def items_omaq():
    out = [dict(item_id=r['question_id'], component=None, request=norm(r['question_text']).strip())
           for r in csv.DictReader(open(f'{H}/med_palm_2_adversarial_questions/equitymedqa_omaq.csv', encoding='utf-8'))]
    return out, dict(rule='otherwise: the question text as released (EquityMedQA OMAQ question_text)', template_source='none')

CB_RAD = ('You are a helpful radiology assistant. The following are questions about radiology reports. Summarize the findings in the '
          'report into diagnostic statements in a coherent paragraph. Given the findings: {Findings}. Q: Summarize the findings. A:')
def items_iu():
    out = []
    with tarfile.open(f'{H}/iu_x_ray_report_summarization/NLMCXR_reports.tgz') as tf:
        for m in tf.getmembers():
            if not m.isfile() or not m.name.endswith('.xml'): continue
            r = ET.fromstring(tf.extractfile(m).read())
            secs = {a.get('Label'): (a.text or '').strip() for a in r.iter('AbstractText')}
            if not (secs.get('FINDINGS') and secs.get('IMPRESSION')): continue
            f = re.sub(r'\s+', ' ', secs['FINDINGS']).strip()
            out.append(dict(item_id=os.path.basename(m.name), component=None, request=CB_RAD.replace('{Findings}', f)))
    return out, dict(rule='template: ClinicBench radiology report summarization prompt (paper Table 8, adapted from Tu et al. 2023) filled with the report FINDINGS (whitespace collapsed); reports without FINDINGS and IMPRESSION are not items',
                     template_source='https://aclanthology.org/2024.emnlp-main.759.pdf (Table 8, "Radiology Report Summarization")')

MD_INSTR = 'Generate a one sentence summary of this patient-doctor conversation.'
def items_meddialog():
    out = []
    for sub in ['healthcaremagic', 'icliniq']:
        for i, e in enumerate(json.load(open(f'{H}/meddialog/{sub}/test.json'))['data']):
            # HELM generation adapter, max_train_instances=0: instructions + "\n" + instance_prefix "\n" + "Patient-Doctor: " + input + "\n" + "Summary:"
            req = MD_INSTR + '\n' + '\n' + 'Patient-Doctor: ' + e['src'] + '\n' + 'Summary:'
            out.append(dict(item_id=f'{sub}/test.json:{e.get("id", i)}', component=sub, request=req))
    return out, dict(rule='template: MedHELM med_dialog prompt (HELM generation adapter: instruction, blank line, "Patient-Doctor: <dialogue>", then the output cue "Summary:"); healthcaremagic and icliniq pooled',
                     template_source=HELM_RS + ' (get_med_dialog_spec) + src/helm/benchmark/adaptation/common_adapter_specs.py and prompt.py at the same commit')

def items_racebias():
    # load HELM scenario file with stubbed helm imports and use its own parsing and prompt construction
    stubs = {}
    for name in ['helm', 'helm.benchmark', 'helm.benchmark.presentation', 'helm.benchmark.presentation.taxonomy_info',
                 'helm.benchmark.scenarios', 'helm.benchmark.scenarios.scenario', 'helm.common', 'helm.common.general']:
        stubs[name] = types.ModuleType(name)
    class _Any:
        def __init__(self, *a, **k): pass
    stubs['helm.benchmark.presentation.taxonomy_info'].TaxonomyInfo = _Any
    sc = stubs['helm.benchmark.scenarios.scenario']
    for n in ['Input', 'Instance', 'Reference', 'Output', 'ScenarioMetadata']: setattr(sc, n, _Any)
    sc.Scenario = object; sc.TEST_SPLIT = 'test'; sc.CORRECT_TAG = 'correct'
    stubs['helm.common.general'].ensure_file_downloaded = lambda **k: None
    sys.modules.update(stubs)
    spec = importlib.util.spec_from_file_location('rbm', f'{H}/racebias/helm_race_based_med_scenario.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    tmp = tempfile.mkdtemp(); csvp = os.path.join(tmp, 'race_based.csv')
    mod.create_csv_from_word(f'{H}/racebias/41746_2023_939_MOESM1_ESM.docx', csvp)
    data = mod.RaceBasedMedScenario.create_benchmark(None, csvp)
    for k in list(sys.modules):
        if k == 'helm' or k.startswith('helm.'): del sys.modules[k]
    out = []
    instr = 'Answer A for yes, B for no.'
    cue = "Respond with only 'A' for yes or 'B' for no. Do not add any other text, punctuation, or symbols:"
    for i, prompt in enumerate(data):
        # HELM multiple_choice_joint, input_noun=None: instructions + "\n" + "\n" + input + "A. yes\nB. no\n" + output cue
        req = instr + '\n' + '\n' + prompt + 'A. yes\n' + 'B. no\n' + cue
        out.append(dict(item_id=f'helm_race_based_med:{i}', component=None, request=req))
    return out, dict(rule='template: MedHELM race_based_med prompt (scenario text "For the following question-answer pair ... Question: ... Response: ..." inside the HELM multiple-choice-joint adapter with options A. yes / B. no and the output cue)',
                     template_source=f'https://github.com/stanford-crfm/helm/blob/{HELM_C}/src/helm/benchmark/scenarios/race_based_med_scenario.py + {HELM_RS} (get_race_based_med_spec)')

def items_usmle():
    from usmle_parse import parse, BOOKS, IMAGE_RULE
    out = []
    for book, n in BOOKS:
        for it in parse(book, n):
            opts = [re.sub(r'^\(([A-Z])\)\s+', r'\1. ', o) for o in it['options']]
            req = ((it['stimulus'] + '\n\n') if it['stimulus'] else '') + it['stem_text'] + '\n' + '\n'.join(opts)
            out.append(dict(item_id=f'{book}.pdf:{it["num"]}', component=book, request=req, image=bool(it['image_match'])))
    return out, dict(rule='multiple choice: the question stem (preceded by the shared abstract or vignette, then a blank line, for items in a set) then the options one per line as "A. ..." (source letters)',
                     template_source='none', image_rule=IMAGE_RULE)

REG = {'ade_corpus': items_ade, 'bc4chemd': items_bc4, 'bc5cdr': items_bc5, 'ebm_nlp_pico_extraction': items_pico,
       'hallmarks_of_cancer': items_hoc, 'healthbench': items_hb, 'healthbench_professional': items_hbp,
       'healthsearchqa': items_hsqa, 'iu_x_ray_report_summarization': items_iu, 'med_palm_2_adversarial_questions': items_omaq,
       'meddialog': items_meddialog, 'racebias': items_racebias, 'rct_text': items_rct, 'species_800': items_s800,
       'usmle_practice_questions': items_usmle}

def run(slug):
    man_path = os.path.join(MAN, slug + '.json'); man = json.load(open(man_path))
    items, info = REG[slug]()
    excl = {'non_english': 0, 'image': 0, 'duplicate': 0}; seen, usable = set(), []
    for it in items:
        if it.get('lang') not in (None, 'en'): excl['non_english'] += 1; continue
        if it.get('image'): excl['image'] += 1; continue
        if it['request'] in seen: excl['duplicate'] += 1; continue
        seen.add(it['request']); usable.append(it)
    sample = list(usable) if len(usable) <= 200 else random.Random(SEED).sample(usable, 200)
    with open(os.path.join(OUT, slug + '.jsonl'), 'w') as f:
        for it in sample:
            f.write(json.dumps({'benchmark': man['benchmark'], 'slug': slug, 'item_id': it['item_id'], 'component': it.get('component'),
                                'request': it['request'], 'n_chars': len(it['request'])}, ensure_ascii=False) + '\n')
    lens = [len(it['request']) for it in sample]
    rendering = {'rule': info['rule'], 'template_source': info['template_source'], 'n_usable': len(usable), 'n_sampled': len(sample),
                 'seed': SEED, 'excluded': excl}
    if 'image_rule' in info: rendering['image_rule'] = info['image_rule']
    rendering['mean_chars'] = round(statistics.mean(lens), 1); rendering['max_chars'] = max(lens)
    comps = {}
    for it in usable:
        if it.get('component'): comps[it['component']] = comps.get(it['component'], 0) + 1
    if len(comps) > 1:
        rendering['n_usable_by_component'] = comps
        sc = {}
        for it in sample: sc[it['component']] = sc.get(it['component'], 0) + 1
        rendering['n_sampled_by_component'] = sc
    if slug in ('healthbench', 'healthbench_professional'):
        from collections import Counter
        rendering['language_id'] = {'package': 'lingua-language-detector', 'version': LINGUA_VERSION,
                                    'rule': 'non-English iff top language != ENGLISH and confidence >= 0.80 (first user turn)',
                                    'n_excluded_non_english': excl['non_english'],
                                    'non_english_counts': dict(Counter(it['lang'] for it in items if it['lang'] != 'en').most_common())}
    man['rendering'] = rendering
    with open(man_path, 'w') as f: json.dump(man, f, indent=2, ensure_ascii=False); f.write('\n')
    return rendering

if __name__ == '__main__':
    for s in (sys.argv[1:] or list(REG)):
        r = run(s)
        print(f"{s:<36} usable={r['n_usable']:>5} sampled={r['n_sampled']:>4} mean={r['mean_chars']:>8} max={r['max_chars']:>6} excl={r['excluded']}")
