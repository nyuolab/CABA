# Contributing

## Propose a benchmark

Open an issue with the **Propose a benchmark** template. Include where the items can be downloaded and their license. Do not paste benchmark items into issues or pull requests.

Proposals are checked against the five criteria in `docs/protocol.md`. A benchmark must be:

- public;
- in English;
- answerable from text;
- built for health care;
- made of single requests.

Accepted benchmarks go into the next version, never into version 1.0. Each version uses the same sampling, rendering and labelling, and gets a changelog entry and a new Zenodo version.

## Add a benchmark yourself

1. Download the items into `$CABA_DATA/<slug>/`. Write `registry/manifests/<slug>.json` with the source URL, revision, license, file list with sha256 checksums (paths as `$CABA_DATA/...`) and item counts. Copy an existing manifest of the same kind as a starting point.
2. Add a loader for the benchmark to the matching renderer in `scripts/render/`. The renderer must apply the protocol's rules: test or evaluation split, the English filter, the image rule, de-duplication, up to 200 items with seed 20261004, and rendering as the model receives the item. Run the renderer for that slug only.
3. Run `python scripts/prepare_inputs.py` and then `rcqmap annotate` on `$CABA_DATA/inputs/<slug>.csv` (see `scripts/annotate.sh`). Run `python scripts/export_labels.py` to write `labels/<slug>.jsonl`. Annotation is a paid API call (about US$0.01 per item).
4. Add the decision to `scripts/registry/finalize.py` and the row to `registry/caba_v1.0.csv`. Rerun `scripts/compare.py` and `scripts/build_site_data.py`.
5. Open a pull request. Commit no item text, rendered items or API keys. The `Check` workflow verifies that the registry and summaries rebuild.

## Corrections

If a license, version or count in the registry is wrong, open an issue with the evidence (a link to the source at a specific revision).
