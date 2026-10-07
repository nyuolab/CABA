"""Turn rendered items ($CABA_DATA/rendered/<slug>.jsonl, written by scripts/render/) into `id,question` CSVs for
`rcqmap annotate`, one per benchmark, in $CABA_DATA/inputs/. Item text stays outside the repository.

Query ids are `<slug>__<item_id>` (with `<component>:` before the item id where a benchmark has components),
the ids used in labels/<slug>.jsonl.
"""
import csv
import json
import re

from caba_paths import INPUTS, RENDERED


def qid(slug, item_id):
    return f"{slug}__{re.sub(r'[^A-Za-z0-9_.:-]+', '_', str(item_id))}"[:200]


def main():
    INPUTS.mkdir(parents=True, exist_ok=True)
    total = 0
    files = sorted(RENDERED.glob('*.jsonl'))
    if not files:
        raise SystemExit(f'No rendered items in {RENDERED}; run the render scripts first (see README).')
    for f in files:
        slug = f.stem
        items = [json.loads(line) for line in f.open(encoding='utf-8')]
        rows = [[qid(slug, f"{x['component']}:{x['item_id']}" if x.get('component') else x['item_id']), x['request']]
                for x in items]
        ids = [r[0] for r in rows]
        assert len(ids) == len(set(ids)), f'duplicate query ids in {slug}'
        with (INPUTS / f'{slug}.csv').open('w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['id', 'question'])
            w.writerows(rows)
        total += len(rows)
    print(f'{len(files)} benchmarks, {total} items -> {INPUTS}')


if __name__ == '__main__':
    main()
