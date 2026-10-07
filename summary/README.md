# Summary

Written by `scripts/compare.py` from `labels/` and `reference/rcq_aggregate.json`.

- `per_benchmark.csv` has one row per benchmark. It gives the share of each task category and each kind of work, the documentation and diagnosis shares, the group (frontier model reports, practice suite, both or other) and the overlap with the RCQ task mix.
- `medians.json` holds the medians and interquartile ranges across benchmarks for each group, and the bootstrap interval for the difference between the practice-suite and frontier-report medians. These are the numbers reported in the paper.
