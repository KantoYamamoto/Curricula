#!/usr/bin/env python3
"""Explicitly allocate stable UUIDs; builds never generate or replace identities."""
import argparse
import json
from pathlib import Path
from uuid import uuid4

REGISTRY = Path(__file__).resolve().parents[1] / 'Sources/CurriculaPilot/Resources/identity-registry.json'

def allocate(path, key, revision):
    records = json.loads(path.read_text()) if path.exists() else {}
    if key not in records:
        records[key] = {'id': str(uuid4()), 'revisions': {}}
    entry = records[key]
    if revision in entry['revisions']:
        return entry['id'], entry['revisions'][revision]
    entry['revisions'][revision] = str(uuid4())
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2, sort_keys=True) + '\n')
    temporary.replace(path)
    return entry['id'], entry['revisions'][revision]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('key', help='Persistent authoring key, independent of display labels')
    parser.add_argument('--revision', default='1')
    args = parser.parse_args()
    identifier, revision = allocate(REGISTRY, args.key, args.revision)
    print(json.dumps({'id': identifier, 'revisionID': revision}))
