# Labels

`<slug>.jsonl` holds one line per labeled item:

- `item_id`: `<slug>__<item id in the source>`; where a benchmark has components, `<slug>__<component>:<item id>`.
- `benchmark`
- `annotation`: the 24 RCQ-Map fields.
- `model`
- `prompt_sha256`: checksum of the RCQ-Map guidelines used.
- `created_at`

`caba_v1.0_labels.csv` is the same content as one flat table (`scripts/flatten_labels.py`).

The labels cover 10,659 items from 58 benchmarks. The 40 sampled Med-HALT items that could not be labeled are listed in `_unlabelled_items.json`.

No item text is included. To see the item a label belongs to, rebuild the items from the original source with `scripts/` (see the top-level README). The paper reports 20 fields derived from these 24, such as kind of work and intent group; `rcqmap derive` in [RCQ-Map](https://github.com/nyuolab/RCQ-Map) computes them, and `rcqmap compare` compares any label file with the real clinical queries.
