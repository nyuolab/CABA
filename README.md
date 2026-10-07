# Clinical AI Benchmark Atlas (CABA)

CABA is a registry of the public benchmarks used to evaluate large language models in health care: the 58 benchmarks
named by 13 evaluation suites and by frontier model reports, checked against five criteria on their downloaded
items. Up to 200 items from each carry [RCQ-Map](https://github.com/nyuolab/RCQ-Map) labels, and every benchmark is
compared with the task mix of real clinical queries that clinicians sent to an institutional AI assistant.

Version 1.0 is the version described in the paper. The median benchmark shares 31% of the real task mix, against
55% for an even spread over the ten task categories, and contains no documentation or administrative requests,
against 36.2% of real queries.

## Use the data

Three plain files hold everything most readers need. No installation.

| File | Contents |
|---|---|
| `registry/caba_v1.0.csv` | One row per benchmark: suites, frontier model reports, items sampled and labeled, split, version, license, source, rendering rule |
| `summary/per_benchmark.csv` | Task and kind-of-work shares per benchmark, and overlap with real use |
| `labels/caba_v1.0_labels.csv` | Item ids and the 24 RCQ-Map labels for all 10,659 labeled items |

```python
import pandas as pd
labels = pd.read_csv("labels/caba_v1.0_labels.csv")
labels.groupby("benchmark")["task_category"].value_counts(normalize=True)
```

The same three files are mirrored as a Hugging Face dataset, [NYU-OLAB/CABA](https://huggingface.co/datasets/NYU-OLAB/CABA), for `datasets.load_dataset`.

**Benchmark items are not redistributed.** Each benchmark keeps its own license, and some ask that their items not
be posted online. CABA releases item ids and labels, plus scripts that rebuild the items from each benchmark's own
release.

## Reproduce the paper's numbers

```bash
pip install numpy pandas
python scripts/compare.py
```

This prints the medians and the bootstrap interval reported in the paper: 31.0% overlap across all 58
benchmarks (IQR 21.1 to 38.5), 40.3% for the benchmarks used in frontier model reports (36.0 to 50.1), 34.8% for
the suites meant to resemble practice (25.8 to 38.7), and a practice-minus-frontier difference of -5.5 points
(95% CI -21.2 to 0.3). The two registry stages also rebuild byte for byte:

```bash
python scripts/registry/build_candidates.py   # -> registry/candidates_175.csv
python scripts/registry/finalize.py           # -> registry/download_checked_73.csv
```

## Requirements and a quick check

Reading the data files needs nothing beyond a CSV reader. The comparison and the registry rebuild need Python 3.10
or newer with `numpy` and `pandas`. They are tested on macOS 26.5 (Apple silicon) with Python 3.10 (numpy 2.2.6,
pandas 2.3.3) and Python 3.14 (numpy 2.5.3, pandas 3.0.6), and on Ubuntu with Python 3.11 in the repository's
continuous check, which also confirms that the registry and summary files rebuild byte for byte. With pandas 3.0,
three quartiles in `summary/medians.json` differ from the committed file in the last floating-point digit; the
printed numbers are the same. Rebuilding the items from the sources needs the rest of `requirements.txt`, about 1 GB
of downloads, and an OpenAI key for relabeling.

No special hardware is needed; everything runs on a laptop CPU. Installing `numpy` and `pandas` took 8 s. The demo
is the reproduction itself:

```bash
pip install numpy pandas
python scripts/compare.py
```

It prints these four lines, in about five seconds on Python 3.10 and under a second on 3.14, and rewrites
`summary/per_benchmark.csv` and `summary/medians.json` with the same contents:

```
frontier  n=12 median overlap 40.3% (IQR 36.0-50.1) | median doc/admin 0.0% | n doc>=5% 2
practice  n=29 median overlap 34.8% (IQR 25.8-38.7) | median doc/admin 0.0% | n doc>=5% 9
all       n=58 median overlap 31.0% (IQR 21.1-38.5) | median doc/admin 0.0% | n doc>=5% 13
practice - frontier: -5.5 points (95% CI -21.2 to 0.3)
```

The registry rebuild (`scripts/registry/build_candidates.py`, then `finalize.py`) takes a further five seconds.

## Rebuild the items and labels from the sources

Downloaded data lives outside the repository, in `$CABA_DATA` (default `~/caba_data`).

```bash
pip install -r requirements.txt
python scripts/fetch_data.py list          # source, revision and license of each benchmark
python scripts/fetch_data.py download      # every file with a direct URL, pinned to a commit or revision
# fetch the files it lists as missing by hand from the listed source, then:
python scripts/fetch_data.py verify        # sha256 of every file against the manifests
scripts/render/fetch_templates.sh          # Med-HALT and MedHallu prompt templates, at pinned commits
python scripts/render/run_render_hf.py
python scripts/render/render_github_hosts.py
python scripts/render/render_other_hosts.py
python scripts/prepare_inputs.py           # -> $CABA_DATA/inputs/<slug>.csv
scripts/annotate.sh                        # rcqmap annotate on each benchmark -> labels/<slug>.jsonl
python scripts/flatten_labels.py           # -> labels/caba_v1.0_labels.csv
```

Annotation calls the OpenAI API with the paper's configuration and costs about US$0.01 per item. Run
`rcqmap annotate --dry-run` first.

## Repository layout

```
registry/      the registry, its two build stages, per-benchmark manifests, frontier report provenance
labels/        RCQ-Map labels per benchmark (no item text) and the flat label table
reference/     aggregate RCQ shares from the paper
summary/       per-benchmark comparison and medians (scripts/compare.py)
scripts/       registry, fetch, render, annotate, compare and label scripts
docs/          protocol.md, the protocol as in the paper's Methods
```

## Contribute

To propose a benchmark for the next version, open an issue with the **Propose a benchmark** template; see
`CONTRIBUTING.md`. Version 1.0 is frozen as described in the paper; later versions follow the same protocol and
are listed in `CHANGELOG.md`.

## Citation

If you use CABA, cite the paper:

Vishwanath, K. *et al.* Clinician use of language models diverges from how the models are evaluated. arXiv:2610.11069 (2026).
https://arxiv.org/abs/2610.11069

```bibtex
@misc{vishwanath2026clinician,
  title         = {Clinician use of language models diverges from how the models are evaluated},
  author        = {Vishwanath, Krithik and Lin, Haitong and Alyakin, Anton and Lee, Jin Vivian and Hewitt, D. Brock and
                   Yao, Jie J. and Small, William Robert and Khan, Hammad A. and Orillac, Cordelia and Varma, Aakaash and
                   Ye, Brandon and Alber, Daniel Alexander and Stolovitzky, Gustavo and Wiesenfeld, Batia and Nov, Oded and
                   Wu, Wei and Zhang, Kang and Aphinyanaphongs, Yindalon and Requarth, Tim and Oermann, Eric Karl and
                   {The International Digital Twin Consortium in Healthcare and Medicine}},
  year          = {2026},
  eprint        = {2610.11069},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CL},
  doi           = {10.48550/arXiv.2610.11069},
  url           = {https://arxiv.org/abs/2610.11069}
}
```

The same reference is in `CITATION.cff`, so GitHub's **Cite this repository** button exports it as BibTeX or APA. To
cite this release of the dataset itself, use the archived version: https://doi.org/10.5281/zenodo.23223809.

## License

Code: Apache License 2.0 (`LICENSE`). Registry, labels, summaries and reference shares: CC BY 4.0
(`LICENSE-data`). The Epoch AI snapshot is CC BY 4.0 (`registry/frontier_reports/ATTRIBUTION.md`). The
benchmarks themselves keep their own licenses.
