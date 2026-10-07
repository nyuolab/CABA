# Registry

| File | Contents |
|---|---|
| `caba_v1.0.csv` | The 58 benchmarks in CABA v1.0 (Supplementary Data 1 of the paper). See the column list below. |
| `candidates_175.csv`, `candidates_counts.json` | Every benchmark named by the 13 suites or the frontier model reports, with the decision before download and its reason. |
| `download_checked_73.csv`, `download_checked_counts.json` | The 73 benchmarks downloaded and checked, with the decision after download (58 included, 15 excluded) and its reason. |
| `suite_components.csv` | Benchmarks listed by each evaluation suite's paper and code repository, as of 30 September 2026. |
| `manifests/<slug>.json` | One file per downloaded benchmark: source URL, revision, licence, file list with sha256 checksums (paths relative to `$CABA_DATA`), item counts, field names and the rendering rule. No item text. |
| `frontier_reports/` | Selection and provenance of the frontier model reports. See `frontier_reports/ATTRIBUTION.md`. |

The columns of `caba_v1.0.csv` are:

- `benchmark`
- `evaluation_suites`
- `frontier_model_reports_by`
- `in_suite_meant_to_resemble_practice`
- `used_in_frontier_model_reports`
- `items_sampled`, `items_labelled` and `items_usable`
- `split`, `version`, `license` and `source`
- `rendering_rule`
- `share_of_rcq_task_mix`

In `caba_v1.0.csv`, a `source` cell lists at most three URLs. Where a benchmark has more files, the rest are listed in its manifest. Licences are as stated by each benchmark's authors at the recorded revision. Check the source before reusing items.
