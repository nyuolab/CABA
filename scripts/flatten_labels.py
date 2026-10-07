"""Write labels/caba_v1.0_labels.csv: one row per labelled item with its id, benchmark and the 24 RCQ-Map fields.

No item text. Run after scripts/export_labels.py. The CI check rebuilds this file and fails if it differs.
"""
import csv
import json

from caba_paths import LABELS


def main():
    out = LABELS / 'caba_v1.0_labels.csv'
    n = 0
    with out.open('w', newline='', encoding='utf-8') as fh:
        w = None
        for p in sorted(LABELS.glob('[!_]*.jsonl')):
            for line in p.open(encoding='utf-8'):
                rec = json.loads(line)
                if w is None:
                    fields = list(rec['annotation'])
                    w = csv.writer(fh)
                    w.writerow(['item_id', 'benchmark'] + fields)
                w.writerow([rec['item_id'], rec['benchmark']] + [rec['annotation'][f] for f in fields])
                n += 1
    print(f'{n} labeled items -> {out}')


if __name__ == '__main__':
    main()
