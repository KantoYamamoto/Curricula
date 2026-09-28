#!/usr/bin/env python3
"""Extract exact official rows along reviewed, explicit paths; never infer parents from code prefixes."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / 'Sources/CurriculaPilot/Resources/cross-subject-selection.json'

def extract(retrieved_on, cache=None):
    config = json.loads(SELECTION.read_text(encoding='utf-8'))
    tables, sources = {}, []
    for spec in config['sources']:
        if cache:
            raw = (cache / f'curricula-{spec["version"]}.csv').read_bytes()
        else:
            with urlopen(spec['url'], timeout=30) as response:
                raw = response.read()
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = raw.decode('cp932')
        records = list(csv.reader(io.StringIO(text)))
        if spec['version'] not in records[0][0]:
            raise ValueError('Unexpected distribution version')
        table = {}
        for number, row in enumerate(records, 1):
            if len(row) != 4 or len(row[3]) != 16:
                continue
            if row[3] in table:
                raise ValueError('Duplicate official code: ' + row[3])
            table[row[3]] = (number, row)
        tables[spec['version']] = table
        sources.append(dict(id='src.mext-'+spec['version'].lower(), title=spec['title'], publisher='文部科学省',
                            url=spec['url'], promulgated=spec['promulgated'], distributionVersion=spec['version'],
                            retrievedOn=retrieved_on, sha256=hashlib.sha256(raw).hexdigest(),
                            verification='公式配布CSVのコードと原文を保持。選定した階層は原典の見出し・配列に基づき明示。'))
    items = {}
    for case in config['cases']:
        for path in case['paths']:
            parent = None
            for code in path:
                number, row = tables[case['version']][code]
                item = dict(code=code, text=row[2], subject=row[0], sourceID='src.mext-'+case['version'].lower(),
                            locator=f'CSV record {number}; No {row[1]}', frameworkID=case['frameworkID'])
                if parent:
                    item['parentCode'] = parent
                if code in items and items[code] != item:
                    raise ValueError('Conflicting hierarchy for ' + code)
                items[code] = item
                parent = code
    return dict(sources=sources, frameworks=config['frameworks'], items=sorted(items.values(), key=lambda x:x['code']), cases=config['cases'])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retrieved-on', required=True)
    parser.add_argument('--cache', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = extract(args.retrieved_on, args.cache)
    with args.output.open('x', encoding='utf-8') as file:
        json.dump(result, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write('\n')
    print(f'{len(result["cases"])} cases, {len(result["items"])} original records')
