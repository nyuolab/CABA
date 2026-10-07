"""Get the benchmark files CABA v1.0 was built from, and check that you have the same bytes.

    python scripts/fetch_data.py list               # source, revision, license and file count for each benchmark
    python scripts/fetch_data.py download [slug ...] # fetch every file that has a direct, pinned URL in its manifest
    python scripts/fetch_data.py verify              # sha256 of every expected file under $CABA_DATA

Files are listed in registry/manifests/<slug>.json with sha256 checksums and paths relative to $CABA_DATA. Most
have a direct URL pinned to a commit or dataset revision; `download` saves those to the recorded path. The rest
(archives that were extracted, dataset cards, journal supplements, pages that need registration or terms
acceptance) are listed for fetching by hand from the manifest's source. For gated Hugging Face datasets, accept the
terms on the dataset page and set HF_TOKEN. Respect each benchmark's license and any request not to post items online.
"""
import hashlib
import json
import os
import sys
import urllib.request
from urllib.parse import unquote, urlparse

from caba_paths import DATA, MANIFESTS


def manifests(only=None):
    for f in sorted(MANIFESTS.glob('*.json')):
        m = json.loads(f.read_text(encoding='utf-8'))
        if m.get('in_caba_v1_0') and (not only or f.stem in only):
            yield f.stem, m


def local(path):
    return DATA / path.replace('$CABA_DATA/', '')


def plan(m):
    """Pair each direct source URL with the manifest file of the same name (closest folder match if several)."""
    urls = m.get('source_url')
    urls = urls if isinstance(urls, list) else [urls]
    files = m.get('files') or []
    pairs, used = [], set()
    for u in map(str, urls):
        if not u.startswith('http'):
            continue
        path = unquote(urlparse(u).path)
        base = os.path.basename(path)
        cands = [f for f in files if os.path.basename(f['path']) == base and f['path'] not in used]
        if len(cands) > 1:
            segs = [s for s in path.split('/') if s]
            cands.sort(key=lambda f: -sum(1 for s in segs if f'/{s}/' in f['path'] + '/'))
        if cands:
            pairs.append((u, cands[0]))
            used.add(cands[0]['path'])
    unmatched = [f for f in files if f['path'] not in used]
    return pairs, unmatched


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def cmd_list(_):
    for slug, m in manifests():
        pairs, _rest = plan(m)
        src = m.get('source_url')
        print(f"{slug}\n  source: {src[0] if isinstance(src, list) else src}\n  revision: {m.get('revision')}\n"
              f"  licence: {m.get('license')}\n  files: {len(m.get('files') or [])} ({len(pairs)} with a direct URL)")


def cmd_download(slugs):
    token = os.environ.get('HF_TOKEN')
    got = skipped = failed = 0
    by_hand = []
    for slug, m in manifests(slugs):
        pairs, rest = plan(m)
        by_hand += [(slug, f['path']) for f in rest]
        for url, f in pairs:
            dest = local(f['path'])
            if dest.exists() and sha256(dest) == f.get('sha256'):
                skipped += 1
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(url, headers={'User-Agent': 'caba-fetch/1.0'})
            if token and 'huggingface.co' in url:
                req.add_header('Authorization', f'Bearer {token}')
            try:
                with urllib.request.urlopen(req, timeout=120) as r, open(dest, 'wb') as out:
                    out.write(r.read())
                got += 1
            except Exception as error:  # gated, moved or removed files are reported, not fatal
                failed += 1
                print(f'{slug}: could not fetch {url} ({type(error).__name__})')
    print(f'downloaded {got}, already present {skipped}, failed {failed} (under {DATA})')
    if by_hand:
        print(f'{len(by_hand)} files have no direct URL in their manifest; fetch them from the listed source:')
        for slug, p in by_hand:
            print(f'  {slug}: {p}')


def cmd_verify(_):
    ok = bad = missing = 0
    for slug, m in manifests():
        for f in m.get('files') or []:
            p = local(f['path'])
            if not p.exists():
                missing += 1
            elif sha256(p) == f.get('sha256'):
                ok += 1
            else:
                bad += 1
                print(f'checksum differs: {slug} {f["path"]}')
    print(f'{ok} files match, {bad} differ, {missing} missing (under {DATA})')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'list'
    {'list': cmd_list, 'download': cmd_download, 'verify': cmd_verify}[cmd](sys.argv[2:])
