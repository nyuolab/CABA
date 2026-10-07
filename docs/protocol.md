# CABA version 1.0 protocol

This is the protocol used to build CABA version 1.0, as described in the Methods of the paper. Version 1.0 is frozen. Later versions follow the same protocol with a new snapshot date and are recorded in `CHANGELOG.md`.

## 1. Sources

CABA collects the benchmarks used to evaluate large language models in health care from two sources.

**Evaluation suites.** There are 13 public evaluation suites for medical LLMs, selected by the authors:

- MedHELM
- MultiMedQA
- MedS-Bench
- ClinicBench
- MIRAGE
- Medmarks
- BRIDGE
- MEDIC
- MMedBench
- CLUE
- MedBench
- HealthBench
- MAST

Each suite's component benchmarks were taken from its paper and code repository on 30 September 2026. They are listed in `registry/suite_components.csv`.

**Frontier model reports.** These are the technical reports, system cards and model cards of frontier models. They were selected by a fixed rule from Epoch AI's Notable AI Models database, downloaded on 4 October 2026 (`registry/frontier_reports/epoch_notable_ai_models_2026-10-04.csv`, CC BY 4.0). The rule takes every model that:

- has a language domain;
- was published between 1 January 2023 and 30 September 2026;
- was published by one of these 13 developers: OpenAI, Anthropic, Google, Meta, Microsoft, xAI, Alibaba, DeepSeek, Mistral, Moonshot, Zhipu, MiniMax or NVIDIA.

These 209 models link to 174 documents, and 169 of them could be retrieved. The other five links led to a login page, a redirect, a single post or a withdrawn preprint.

Each document was read together with any system card, model card or technical report from the same developer that it linked to. Every health benchmark with reported results was recorded, along with the passage reporting it.

Twenty-three documents, covering 31 models, reported results on 22 health benchmarks. The provenance files are:

- the selection: `frontier_reports_selected.csv`;
- the documents and their retrieval: `frontier_reports_documents.csv`, `frontier_reports_fetch_log.json` and `frontier_reports_browser.jsonl`;
- the benchmarks and passages: `frontier_benchmarks.csv`.

The report text itself is not redistributed; `scripts/registry/frontier_reports.py fetch` downloads it again.

## 2. Merging and eligibility

Benchmark names from both sources were merged into a single list. Alternative names of the same benchmark were combined, and subsets, translations and other variants were merged into their parent benchmark.

A benchmark was included if all five criteria held:

1. **Public.** Its evaluation items could be downloaded without credentialed access, an application, a data use agreement or payment. Free registration was allowed.
2. **English.** Its items, or an English version released by its authors, were in English.
3. **Text.** Its items could be answered from text alone. For mixed-modality benchmarks, the text-only items were used.
4. **Built for health care.** It was not drawn from a general-domain benchmark (MMLU, MMLU-Pro, GPQA, SuperGPQA, Humanity's Last Exam, TruthfulQA, C-Eval or CMMLU).
5. **Single requests.** Its items were questions, instructions, vignettes or conversations to which a model responds. Agent environments and token-level labelling tasks were recorded but not annotated.

Criteria 1 to 3 and 5 were assessed on the downloaded items.

| Stage | Benchmarks |
|---|---|
| Named across the sources | 175 |
| Excluded before download | 102 (42 not public, 40 not in English, 8 not answerable from text, 8 not built for health care, 4 not single requests) |
| Downloaded and checked | 73 |
| Excluded after download | 15 (8 not public, 4 not single requests, 2 versions of MedQA merged into it, 1 drawn from a general-domain benchmark) |
| **Included in CABA v1.0** | **58** |

The registry files for each stage are:

- `registry/candidates_175.csv` holds the named benchmarks and the reason for each exclusion before download.
- `registry/download_checked_73.csv` holds the decisions after download.
- `registry/caba_v1.0.csv` is the final registry (Supplementary Data 1 of the paper).

For each benchmark, `registry/manifests/<slug>.json` records the source, the version (a commit or dataset revision), the file checksums, the license and the number of items.

Both registry stages can be rebuilt from the shipped inputs, and the output is byte-identical to the files above:

```
python scripts/registry/build_candidates.py   # suite components + frontier benchmarks -> candidates_175.csv
python scripts/registry/finalize.py           # manifests + decisions -> download_checked_73.csv
```

## 3. Sampling and rendering

From each benchmark, up to 200 items were sampled uniformly at random without replacement (seed 20261004) from its test or evaluation split. Benchmarks with fewer items were used in full. Three kinds of item were removed before sampling:

- items not in English;
- items that refer to an image that is not released;
- duplicates.

Language was identified with lingua (version 2.1.1). An item was treated as non-English when its top language was not English with a confidence of at least 0.80.

Each item was rendered as a model under evaluation receives it:

- the question with its answer options;
- the vignette with its question;
- the instruction with its input text;
- the benchmark's or suite's published prompt template, where one defines the task;
- for conversations, the first user turn.

The first-turn rule mirrors the RCQ corpus, where the first clinician turn was annotated. The rendering rule used for each benchmark is in the `rendering_rule` column of the registry.

One benchmark's published template leaves its slots unspecified, so it could not be rendered as released. It was excluded as not a single request.

The renderers are in `scripts/render/`. They read the downloaded files under `$CABA_DATA` and write rendered items to `$CABA_DATA/rendered/`, outside the repository.

## 4. Labelling

RCQ-Map was applied to the 10,699 sampled items with the configuration used for the real clinical queries:

- the annotator model GPT-5.6 sol, with reasoning effort none;
- RCQ-Map guidelines version 2.1 (sha256 `f8f0fc98…5394`);
- the strict 24-field schema;
- the same retry rules.

Of these items, 10,659 (99.6%) were labeled. The other 40, all from Med-HALT, failed the schema's consistency rules on every attempt; their ids are listed in `labels/_unlabelled_items.json`.

Labels are in `labels/<slug>.jsonl`. Each record holds the item id, the 24 labels and the run metadata, and no item text. To relabel, run `scripts/annotate.sh`, which uses the `rcqmap` package.

## 5. Comparison with real clinical use

Each benchmark is summarized separately. Medians and interquartile ranges are reported across benchmarks for three groups:

- the 12 benchmarks used in frontier model reports;
- the 29 benchmarks in the four suites whose papers state the aim of reflecting real-world clinical practice (MedHELM, BRIDGE, ClinicBench and HealthBench). MedBench states the same aim but contributed no eligible benchmark;
- all 58 benchmarks.

Agreement with real use is the share of the real task mix that a benchmark covers. It equals one minus the total variation distance between the benchmark's task distribution and that of the RCQ corpus:

```
overlap = sum over the ten task categories of min(benchmark share, RCQ share)
```

A distribution spread evenly across the ten task categories would cover 55%.

The 95% confidence interval for the difference between the two groups' medians comes from a percentile bootstrap that resampled benchmarks within each group (4,000 replicates, seed 20261004).

The RCQ task distribution comes from the paper and is stored as aggregate shares in `reference/rcq_aggregate.json`. That file's release is pending institutional sign-off. `scripts/compare.py` reproduces the paper's figures from the labels:

| | Median share of the real task mix (IQR) |
|---|---|
| All 58 benchmarks | 31.0% (21.1 to 38.5) |
| 12 used in frontier model reports | 40.3% (36.0 to 50.1) |
| 29 in practice-oriented suites | 34.8% (25.8 to 38.7) |

Practice suites minus frontier reports: -5.5 points (95% CI -21.2 to 0.3).

The median benchmark contains no documentation or administrative requests, against 36.2% of real queries. Only 13 of the 58 benchmarks reach 5%.
