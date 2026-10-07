#!/usr/bin/env bash
# Apply RCQ-Map to every prepared benchmark with the paper's annotator configuration (RCQ-Map's defaults:
# gpt-5.6-sol, reasoning effort none, the paper's guidelines, strict schema). Resumable: completed items are skipped.
# Needs `pip install git+https://github.com/nyuolab/RCQ-Map.git` and OPENAI_API_KEY. Costs money: about
# US$0.01 per item at October 2026 list prices; run `rcqmap annotate ... --dry-run` first.
set -euo pipefail
DATA=${CABA_DATA:-$HOME/caba_data}
mkdir -p "$DATA/annotations"
for f in "$DATA"/inputs/*.csv; do
  slug=$(basename "$f" .csv)
  echo "=== $slug"
  rcqmap annotate --input "$f" --output "$DATA/annotations/${slug}.jsonl" --max-concurrency 12
done
python "$(dirname "$0")/export_labels.py"
