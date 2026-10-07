"""Item loaders for benchmarks hosted on Hugging Face (first set)."""
from render_lib import *

def meds_loader(slug):
    items = []
    files = item_files(slug)
    multi = len(files) > 1
    for p in files:
        j = json.load(open(p))
        d = j["Definition"]; d = d[0] if isinstance(d, list) else d
        comp = os.path.basename(p).rsplit(".", 1)[0]
        for i, ins in enumerate(j["Instances"]):
            iid = ins.get("id") or f"{os.path.basename(p)}:{i}"
            items.append(dict(item_id=str(iid), component=comp if multi else None,
                              request=d.strip() + "\n\n" + ins["input"].strip()))
    return items, dict(rule="instruction-style: the MedS-Bench task Definition (instruction), a blank line, then the instance input.",
                       template_source="none")

def bridge_loader(slug):
    items = []
    files = item_files(slug)
    multi = len(files) > 1
    for p in files:
        for r in json.load(open(p)):
            items.append(dict(item_id=f"{r['task']}:{r['id']}", component=r["task"] if multi else None,
                              request=r["instruction"].strip() + "\n\n" + r["input"].strip()))
    return items, dict(rule="instruction-style: the BRIDGE instruction, a blank line, then the input.", template_source="none")

def careqa(slug):
    d = json.load(open(H + "careqa/CareQA_en.json"))
    items = [dict(item_id=r["unique_id"], component=None,
                  request=mcq(r["question"], [(L[k], r[f"op{k+1}"]) for k in range(4) if not isnan(r.get(f"op{k+1}"))])) for r in d]
    return items, dict(rule="multiple choice: question, then options op1-op4 one per line lettered A-D (source has no letters).", template_source="none")

def head_qa(slug):
    j = json.load(open(H + "head_qa/HEAD_EN/test_HEAD_EN.json"))
    items = []
    for ex, v in j["exams"].items():
        for q in v["data"]:
            ans = q["answers"]; ans = json.loads(ans) if isinstance(ans, str) else ans
            ans = sorted(ans, key=lambda a: int(a["aid"]))
            items.append(dict(item_id=f"{ex}:{q['qid']}", component=None,
                              request=mcq(q["qtext"], [(L[k], a["atext"]) for k, a in enumerate(ans)]),
                              image=bool(str(q.get("image", "")).strip())))
    return items, dict(rule="multiple choice: qtext, then answers one per line in aid order lettered A-E (source numbers them 1-5); questions with a non-empty 'image' field are excluded as image items in addition to the regex.", template_source="none")

def m_arc(slug):
    df = pd.read_parquet(H + "m_arc/data/test-00000-of-00001.parquet")
    items = []
    for r in df.itertuples():
        o = r.options if isinstance(r.options, dict) else json.loads(r.options)
        items.append(dict(item_id=r.question_id, component=None,
                          request=mcq(r.question, [(k, v) for k, v in sorted(o.items()) if not isnan(v) and str(v).strip()])))
    return items, dict(rule="multiple choice: question, then the source's lettered options (A-G) one per line.", template_source="none")

def med_halt(slug):
    items = []
    order = [os.path.basename(os.path.dirname(p)) for p in item_files(slug)]
    inp = {"IR_abstract2pubmedlink": "Abstract", "IR_pmid2title": "PMID", "IR_pubmedlink2title": "url", "IR_title2pubmedlink": "Title"}
    for p in item_files(slug):
        cfg = os.path.basename(os.path.dirname(p))
        df = pd.read_csv(p)
        for i, r in enumerate(df.to_dict("records")):
            if cfg.startswith("reasoning"):
                o = ast.literal_eval(r["options"]) if isinstance(r["options"], str) else r["options"]
                opts = [(L[k], v) for k, (_, v) in enumerate(sorted(((kk, vv) for kk, vv in o.items() if str(kk).isdigit()), key=lambda kv: int(kv[0]))) if not isnan(v)]  # drops the FCT "correct answer" key
                req = mcq(r["question"], opts)
                if cfg == "reasoning_FCT":
                    req += "\n\nstudent_answer: " + str(r["student_answer"]).strip()
            else:
                f = inp[cfg]; req = f"{f}: {str(r[f]).strip()}"
            items.append(dict(item_id=str(r["id"]), component=cfg, request=req))
    return items, dict(rule=("template-defined, template not available offline: reasoning configs rendered as multiple choice (question, then the numbered options '0','1',... lettered A.. in key order, dropping FCT's 'correct answer' key; FCT adds the released student_answer line); "
                             "memory (IR_*) configs rendered as the single released input field with its column name (Abstract, PMID, url or Title)."),
                       template_source="none used (published Med-HALT prompt templates are in https://github.com/medhalt/medhalt; not fetched because this task was restricted to local files)")

def medcalc(slug):
    df = pd.read_csv(H + "medcalc_bench/test_data_11_18_final.csv")
    items = [dict(item_id=str(r["Row Number"]), component=None, request=str(r["Patient Note"]).strip() + "\n\n" + str(r["Question"]).strip())
             for r in df.to_dict("records")]
    return items, dict(rule="vignette + question: Patient Note, a blank line, then Question.", template_source="none")

def medcasereasoning(slug):
    df = pd.read_parquet(H + "medcasereasoning/data/test-00000-of-00001.parquet")
    items = [dict(item_id=r["pmcid"], component=None, request=str(r["case_prompt"]).strip()) for r in df.to_dict("records")]
    return items, dict(rule="item text as released: case_prompt only (the diagnosis question is added by the authors' evaluation prompt, not available offline).",
                       template_source="none used (authors' evaluation prompt in the MedCaseReasoning paper/repository, arXiv:2505.11733; not fetched because this task was restricted to local files)")

def medconceptsqa(slug):
    items = []
    for p in sorted(glob.glob(H + "medconceptsqa/all/test-*.parquet")):
        t = pq.read_table(p, columns=["question_id", "question", "vocab", "level"]).to_pandas()
        items += [dict(item_id=str(a), component=None, request=str(q).strip()) for a, q in zip(t.question_id, t.question)]
    return items, dict(rule="multiple choice as released: the question field already holds the stem and the four options one per line lettered A-D.", template_source="none")

def medexqa(slug):
    items = []
    for p in sorted(glob.glob(H + "medexqa/test/*.tsv")):
        t = pd.read_csv(p, sep="\t", header=None)
        comp = os.path.basename(p)[:-9]
        for i, r in enumerate(t.itertuples(index=False)):
            items.append(dict(item_id=f"{os.path.basename(p)}:{i}", component=comp,
                              request=mcq(r[0], [(L[k], r[k+1]) for k in range(4) if not isnan(r[k+1])])))
    return items, dict(rule="multiple choice: question (column 0), then options (columns 1-4) one per line lettered A-D.", template_source="none")

def medhallu(slug):
    items = []
    for cfg in ["pqa_labeled", "pqa_artificial"]:
        df = pd.read_parquet(H + f"medhallu/{cfg}/train-00000-of-00001.parquet")
        for i, r in enumerate(df.to_dict("records")):
            k = r["Knowledge"]; k = " ".join(map(str, k)) if not isinstance(k, str) and hasattr(k, "__iter__") else str(k)
            items.append(dict(item_id=f"{cfg}:{i}", component=cfg, request=k.strip() + "\n\n" + str(r["Question"]).strip()))
    return items, dict(rule="template-defined, template not available offline: rendered as vignette + question (Knowledge, a blank line, then Question); the candidate answer to be judged (Ground Truth or Hallucinated Answer) is omitted.",
                       template_source="none used (authors' detection prompt in the MedHallu repository, arXiv:2502.14302; not fetched because this task was restricted to local files)")

def medmcqa(slug):
    df = pd.read_parquet(H + "medmcqa/data/validation-00000-of-00001.parquet")
    items = [dict(item_id=r["id"], component=None, request=mcq(r["question"], [("A", r["opa"]), ("B", r["opb"]), ("C", r["opc"]), ("D", r["opd"])]))
             for r in df.to_dict("records")]
    return items, dict(rule="multiple choice: question, then opa-opd one per line lettered A-D.", template_source="none")

def medxpertqa(slug):
    items = []
    for l in open(H + "medxpertqa/Text/test.jsonl"):
        r = json.loads(l)
        stem = r["question"][: r["question"].index("Answer Choices:")].strip()
        items.append(dict(item_id=r["id"], component=None, request=mcq(stem, sorted(r["options"].items()))))
    return items, dict(rule="multiple choice: question stem (inline 'Answer Choices:' block removed), then the source's lettered options A-J one per line.", template_source="none")

def pubhealthbench(slug):
    df = pd.read_parquet(H + "pubhealthbench/data/test-00000-of-00001.parquet")
    items = [dict(item_id=r["question_id"], component=None,
                  request=str(r["question"]).strip() + "\n" + "\n".join(str(o).strip() for o in r["bench_options_list_formatted"]))
             for r in df.to_dict("records")]
    return items, dict(rule="multiple choice: question, then the seven source-lettered options (bench_options_list_formatted, 'A. ...') one per line.", template_source="none")

LOADERS = {
 "biolord_concept_explanation": meds_loader, "ddxplus": meds_loader, "ebmsummariser_justification_verification": meds_loader,
 "human_disease_ontology_entity_explanation": meds_loader, "pmc_patients_basic_information_extraction": meds_loader, "pubhealth": meds_loader,
 "brainmri_ais": bridge_loader, "clinicalnotes_upmc": bridge_loader, "healthcaremagic_100k": bridge_loader, "icliniq_10k": bridge_loader,
 "mediqa_2019_task2_rqe": bridge_loader, "mts_dialog": bridge_loader,
 "careqa": careqa, "head_qa": head_qa, "m_arc": m_arc, "med_halt": med_halt, "medcalc_bench": medcalc, "medcasereasoning": medcasereasoning,
 "medconceptsqa": medconceptsqa, "medexqa": medexqa, "medhallu": medhallu, "medmcqa": medmcqa, "medxpertqa": medxpertqa, "pubhealthbench": pubhealthbench,
}
