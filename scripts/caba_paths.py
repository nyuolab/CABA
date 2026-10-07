"""Where things live. Repository files are found relative to this file; downloaded benchmark data, rendered items
and fetched frontier reports live outside the repository under $CABA_DATA (default ~/caba_data), because item text
and report text are not redistributed."""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REG = REPO / 'registry'
FRONTIER = REG / 'frontier_reports'
MANIFESTS = REG / 'manifests'
LABELS = REPO / 'labels'
REFERENCE = REPO / 'reference'
SUMMARY = REPO / 'summary'
DATA = Path(os.environ.get('CABA_DATA', '~/caba_data')).expanduser()
RAW = DATA / 'raw'
RENDERED = DATA / 'rendered'
REPORTS_RAW = DATA / 'reports_raw'
INPUTS = DATA / 'inputs'
SEED = 20261004
CAP = 200
REF_FILE = REFERENCE / 'rcq_aggregate.json'
