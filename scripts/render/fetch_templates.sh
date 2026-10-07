#!/usr/bin/env bash
# Fetch the third-party prompt templates that two benchmarks' renderers need, at the commits used for CABA v1.0.
# They are not redistributed in this repository.
set -euo pipefail
T="$(cd "$(dirname "$0")" && pwd)/templates"
mkdir -p "$T"
git clone -q https://github.com/medhalt/medhalt "$T/medhalt" && git -C "$T/medhalt" checkout -q 2fed21ed696a1949b1fd6dfdbd7a08d792e0e05f
git clone -q https://github.com/MedHallu/MedHallu "$T/medhallu_repo" && git -C "$T/medhallu_repo" checkout -q 3c49c8ba80e47720333e508821967167ba048d49
mkdir -p "$T/medhallu" && cp "$T/medhallu_repo/Detection/detection_vllm_notsurecase.py" "$T/medhallu/"
echo "templates in $T"
