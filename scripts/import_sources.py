#!/usr/bin/env python3
"""Explicit network-only import. Never runs during build/export; never edits authored data."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SPECS = [
    ('82V12', '73', '小学校学習指導要領（平成29年告示）コード表', ['8250263311100000']),
    ('83V11', '37', '中学校学習指導要領（平成29年告示）コード表', ['8350213311200000', '8350213311400000', '8350213312100000']),
]

def extract(retrieved_on, cache=None):
    sources, items = [], []
    for version, suffix, title, codes in SPECS:
        url = f'https://www.mext.go.jp/content/20230901-mxt_syoto01-000013115_{suffix}.csv'
        if cache:
            raw = (cache / f'curricula-{version}.csv').read_bytes()
        else:
            with urlopen(url, timeout=30) as response:
                raw = response.read()
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = raw.decode('cp932')
        rows = list(csv.reader(io.StringIO(text)))
        if version not in rows[0][0]:
            raise ValueError(f'Unexpected source version: {version}')
        source_id = f'src.mext-{version.lower()}'
        sources.append(dict(id=source_id, title=title, publisher='文部科学省', url=url,
                            promulgated='2017', distributionVersion=version, retrievedOn=retrieved_on,
                            sha256=hashlib.sha256(raw).hexdigest(),
                            verification='公式配布CSVから抽出。本文PDF・訂正票・LODとの全文照合は未完了。'))
        for code in codes:
            matches = [(line, row) for line, row in enumerate(rows, 1) if row and row[-1] == code]
            if len(matches) != 1:
                raise ValueError(f'Expected exactly one row for {code}')
            line, row = matches[0]
            items.append(dict(code=code, text=row[2], sourceID=source_id,
                              locator=f'CSV record {line}; No {row[1]}',
                              frameworkID='fw.elementary-2017' if version == '82V12' else 'fw.secondary-2017'))
    return dict(sources=sources, items=items)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retrieved-on', required=True, help='Actual acquisition date, YYYY-MM-DD')
    parser.add_argument('--cache', type=Path)
    parser.add_argument('--output', type=Path, required=True, help='Write a NEW candidate; review before replacing pinned input')
    args = parser.parse_args()
    result = extract(args.retrieved_on, args.cache)
    with args.output.open('x', encoding='utf-8') as out:
        json.dump(result, out, ensure_ascii=False, indent=2, sort_keys=True)
        out.write('\n')
