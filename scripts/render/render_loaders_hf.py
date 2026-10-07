"""Item loaders for benchmarks hosted on Hugging Face (second set), including the published prompt templates of
Med-HALT, MedHallu and MedCaseReasoning (fetch the first two with fetch_templates.sh)."""
import random, ast
import render_loaders as R
from render_lib_hf import *
import pandas as pd, pyarrow.parquet as pq, glob

TPL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
MEDHALT_COMMIT = "2fed21ed696a1949b1fd6dfdbd7a08d792e0e05f"
MEDHALLU_COMMIT = "3c49c8ba80e47720333e508821967167ba048d49"
MCR_COMMIT = "a64ec5ff1cb1fde7914a7bab3b1d9ab2b0546794"

# ---------- stems for the image rule (None = item is a document; not scanned) ----------
def add_stems(slug, items):
    if slug == "careqa":
        d = {r["unique_id"]: r["question"] for r in json.load(open(H + "careqa/CareQA_en.json"))}
        for it in items: it["stem"] = d[it["item_id"]]
    elif slug == "head_qa":
        j = json.load(open(H + "head_qa/HEAD_EN/test_HEAD_EN.json"))
        d = {f"{ex}:{q['qid']}": q["qtext"] for ex, v in j["exams"].items() for q in v["data"]}
        for it in items: it["stem"] = d[it["item_id"]]
    elif slug == "m_arc":
        df = pd.read_parquet(H + "m_arc/data/test-00000-of-00001.parquet"); d = dict(zip(df.question_id, df.question))
        for it in items: it["stem"] = d[it["item_id"]]
    elif slug in ("medconceptsqa", "medmcqa", "pubhealthbench", "medexqa"):
        for it in items: it["stem"] = it["request"].split("\n")[0] if slug != "medconceptsqa" else it["request"]
        if slug == "medexqa":
            for it in items: it["stem"] = it["request"].rsplit("\nA. ", 1)[0]
        if slug in ("medmcqa", "pubhealthbench"):
            for it in items: it["stem"] = it["request"].rsplit("\nA. ", 1)[0]
    elif slug == "medxpertqa":
        for it in items: it["stem"] = it["request"].rsplit("\nA. ", 1)[0]
    elif slug == "medcalc_bench":
        df = pd.read_csv(H + "medcalc_bench/test_data_11_18_final.csv"); d = dict(zip(df["Row Number"].astype(str), df["Question"]))
        for it in items: it["stem"] = d[it["item_id"]]
    elif slug in ("healthcaremagic_100k", "icliniq_10k", "mediqa_2019_task2_rqe"):
        for it in items: it["stem"] = it["input"]
    # medhallu, med_halt set their own stems; everything else: documents -> no stem
    for it in items: it.setdefault("stem", None)
    return items

# ---------- BRIDGE loader keeping the raw input (for patient-question stems) ----------
def bridge_loader(slug):
    items = []
    files = item_files(slug); multi = len(files) > 1
    for p in files:
        for r in json.load(open(p)):
            items.append(dict(item_id=f"{r['task']}:{r['id']}", component=r["task"] if multi else None,
                              request=r["instruction"].strip() + "\n\n" + r["input"].strip(), input=r["input"]))
    return items, dict(rule="instruction-style: the BRIDGE instruction, a blank line, then the input.", template_source="none")

# ---------- Med-HALT: published zero-shot template (prompt v0, as in the repo's inference) ----------
MH_DIR = {"reasoning_FCT": "reasoning_FCT", "reasoning_nota": "Reasoning_Nota", "reasoning_fake": "reasoning_Fake",
          "IR_abstract2pubmedlink": "IR_abstract2pubmedlink", "IR_pmid2title": "IR_pmid2title",
          "IR_pubmedlink2title": "IR_pubmedlink2title", "IR_title2pubmedlink": "IR_title2pubmedlink"}
def mh_header(cfg):
    p = json.load(open(f"{TPL}/medhalt/medhalt/prompts/{MH_DIR[cfg]}/prompts.json"))["prompts"]
    p = [x for x in p if x["id"] == "v0"][0]
    # get_full_prompt(..., n_shots=0): prompt + '\n' + output_format + '\n'
    return p["prompt"] + "\n" + p["output_format"] + "\n"
def med_halt(slug):
    items = []
    for p in item_files(slug):
        cfg = os.path.basename(os.path.dirname(p)); head = mh_header(cfg)
        df = pd.read_csv(p)
        for r in df.to_dict("records"):
            stem = None
            if cfg.startswith("reasoning"):
                # Nota_format: "Input: " + str({"Question": q, "Options": eval(options)}) + "\nOutput: "
                body = "Input: " + str({"Question": r["question"], "Options": ast.literal_eval(r["options"])}) + "\nOutput: "
                stem = r["question"]
            elif cfg == "IR_pmid2title":
                body = "Input: " + str({"Pmid": str(int(r["PMID"]))}) + "\n" + "Output: "
            elif cfg == "IR_abstract2pubmedlink":
                body = "Input: " + str({"paper_abstract": str(r["Abstract"])}) + "\n" + "Output: "
            elif cfg == "IR_pubmedlink2title":
                body = "Input: " + str({"url": str(r["url"])}) + "\n" + "Output: "
            elif cfg == "IR_title2pubmedlink":
                body = "Input: " + str({"paper_title": str(r["Title"])}) + "\n" + "Output: "
            items.append(dict(item_id=str(r["id"]), component=cfg, request=head + body, stem=stem))
    src = (f"https://github.com/medhalt/medhalt/tree/{MEDHALT_COMMIT}/medhalt/prompts (prompts.json of each test, id 'v0'); "
           f"assembly per https://github.com/medhalt/medhalt/blob/{MEDHALT_COMMIT}/medhalt/prompts/utils.py "
           "(get_full_prompt with n_shots=0, then the *_format functions); commit " + MEDHALT_COMMIT)
    return items, dict(rule=("template-defined: Med-HALT's published prompt for the item's test (version v0, the version used by the repository's inference), "
                             "zero-shot (the repository's 2 few-shot examples are drawn with an unseeded random.sample and are omitted), filled exactly as the repository's "
                             "prompt utilities do: instruction + '\\n' + output format + '\\n' + 'Input: ' + Python dict of the item fields + '\\nOutput: '."),
                       template_source=src)

# ---------- MedHallu: published detection prompt with knowledge ----------
MEDHALLU_SYSTEM = None
def medhallu(slug):
    src = open(f"{TPL}/medhallu/detection_vllm_notsurecase.py").read()
    ns = {}
    # take the system prompt and the with-knowledge prompt function verbatim from the published script
    sp = src[src.index('system_prompt = """'): src.index('def create_prompt(')]
    fn = src[src.index('def create_prompt_withknowledge('): src.index('# ---------------------\n# GPU MEMORY')]
    exec(sp + "\n" + fn, ns)
    rng = random.Random(SEED)  # mirrors the script's random.randint(0, 1) choice of candidate, seeded
    items = []
    for cfg in ["pqa_labeled", "pqa_artificial"]:
        df = pd.read_parquet(H + f"medhallu/{cfg}/train-00000-of-00001.parquet")
        for i, r in enumerate(df.to_dict("records")):
            k = r["Knowledge"]; k = [str(x) for x in k] if not isinstance(k, str) else k
            pick = rng.randint(0, 1)
            chosen = [r["Ground Truth"], r["Hallucinated Answer"]][pick]
            user = ns["create_prompt_withknowledge"](r["Question"], chosen, k)
            items.append(dict(item_id=f"{cfg}:{i}", component=cfg, request=f"{ns['system_prompt']} {user}",
                              stem=str(r["Question"]), candidate=("ground_truth" if pick == 0 else "hallucinated")))
    s = (f"https://github.com/MedHallu/MedHallu/blob/{MEDHALLU_COMMIT}/Detection/detection_vllm_notsurecase.py "
         "(system_prompt + create_prompt_withknowledge, sent as one user message f'{system_prompt} {user_prompt}'); commit " + MEDHALLU_COMMIT)
    return items, dict(rule=("template-defined: MedHallu's published detection prompt with world knowledge, filled exactly as in the script "
                             "(system prompt, a space, then 'World Knowledge: <Knowledge list>', 'Question:', 'Answer: <candidate>' and the judgement cue). "
                             "The candidate answer is the Ground Truth or the Hallucinated Answer, chosen per item by random.Random(20261004).randint(0, 1) "
                             "in file order (the script uses an unseeded random.randint(0, 1))."),
                       template_source=s)

# ---------- MedCaseReasoning: published diagnostic question template (Prompt 6) ----------
MCR_TEMPLATE = ("Read the following case presentation and give the most likely diagnosis.\n"
                "First, provide your internal reasoning for the diagnosis within the tags <think> ... </think>.\n"
                "Then, output the final diagnosis (just the name of the disease/entity) within the tags <answer> ... </answer>.\n"
                "\n"
                "---------------------------\n"
                "CASE PRESENTATION\n"
                "---------------------------\n"
                "{case_presentation}\n"
                "\n"
                "---------------------------\n"
                "OUTPUT TEMPLATE\n"
                "---------------------------\n"
                "<think>\n"
                "...your internal reasoning for the diagnosis...\n"
                "</think>\n"
                "<answer>\n"
                "...the name of the disease/entity...\n"
                "</answer>")
def medcasereasoning(slug):
    df = pd.read_parquet(H + "medcasereasoning/data/test-00000-of-00001.parquet")
    items = [dict(item_id=r["pmcid"], component=None, request=MCR_TEMPLATE.replace("{case_presentation}", str(r["case_prompt"]).strip()), stem=None)
             for r in df.to_dict("records")]
    s = (f"https://github.com/kevinwu23/Stanford-MedCaseReasoning/blob/{MCR_COMMIT}/Supplemental_Material.pdf "
         "(Prompt 6: Diagnostic Question Template, pp. 9-10; transcribed from the PDF text layer: blank lines from the PDF layout, indentation removed); commit "
         + MCR_COMMIT + ". The repository's prompts.py is listed in its README but not present at this commit.")
    return items, dict(rule="template-defined: MedCaseReasoning's published Diagnostic Question Template (zero-shot) with case_prompt as {case_presentation}.",
                       template_source=s)

LOADERS = dict(R.LOADERS)
for s in ("brainmri_ais", "clinicalnotes_upmc", "healthcaremagic_100k", "icliniq_10k", "mediqa_2019_task2_rqe", "mts_dialog"):
    LOADERS[s] = bridge_loader
LOADERS["med_halt"] = med_halt; LOADERS["medhallu"] = medhallu; LOADERS["medcasereasoning"] = medcasereasoning
