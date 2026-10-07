"""Copy annotator output ($CABA_DATA/annotations/<slug>.jsonl) into labels/<slug>.jsonl, keeping only the item id,
the 24 RCQ-Map labels and run metadata (the latest valid record per item). No item text is written."""
import csv
import json

from caba_paths import DATA, LABELS, REG


def main():
    names = {r['slug']: r['benchmark'] for r in csv.DictReader((REG / 'download_checked_73.csv').open(encoding='utf-8'))
             if r['status'] == 'include'}
    LABELS.mkdir(exist_ok=True)
    for slug, name in sorted(names.items()):
        src = DATA / 'annotations' / f'{slug}.jsonl'
        if not src.exists():
            print(f'missing {src}')
            continue
        latest = {}
        for line in src.open(encoding='utf-8'):
            r = json.loads(line)
            if r.get('status') == 'ok':
                latest[r['query_id']] = r
        with (LABELS / f'{slug}.jsonl').open('w', encoding='utf-8') as fh:
            for qid in sorted(latest):
                r = latest[qid]
                fh.write(json.dumps({'item_id': qid, 'benchmark': name, 'annotation': r['annotation'], 'model': r['model'],
                                     'prompt_sha256': r['prompt_sha256'], 'created_at': r['created_at']},
                                    ensure_ascii=False) + '\n')
        print(f'{slug}: {len(latest)} labeled items')


if __name__ == '__main__':
    main()
