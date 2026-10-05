#!/usr/bin/env python3
"""Extract selected facts from the two pinned LOD Turtle serializations, offline.

This is intentionally a parser for these captured files, not a general RDF parser.
URLs, hashes and license are in data/sources/mext/metadata.json.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
from build_curriculum import ROOT, SOURCES, VERSIONS, rows


def extract(items_path, hierarchy_path):
    pinned=json.loads((SOURCES/'metadata.json').read_text())
    for path,source in zip((items_path,hierarchy_path),pinned['sources']):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=source['sha256']:
            raise ValueError('Captured artifact hash differs: '+str(path))
    items=gzip.decompress(items_path.read_bytes()).decode('utf-8')
    hierarchy=hierarchy_path.read_text(encoding='utf-8')
    pairs=re.findall(r'cs:(\w{16}) schema:hasPart cs:(\w{16})\.',hierarchy)
    parents={child:parent for parent,child in pairs}
    if len(parents)!=len(pairs):raise ValueError('Ambiguous parent')
    blocks=dict(re.findall(r'<https://w3id.org/jp-cos/(8[23]\w{14})> a <https://w3id.org/jp-cos/Item>;\n(.*?)(?=\n\n)',items,re.S))
    metadata={};corrections=[]
    for version,*_ in VERSIONS:
        for subject,no,text,code in rows(version):
            block=blocks[code]
            grades=re.findall(r'cs:grade ([^;]+);',block)
            course=re.findall(r'cs:subject <https://w3id.org/jp-cos/[^>]+/([^/>]+)>;',block)
            if len(grades)>1 or len(course)>1:raise ValueError('Ambiguous education scope: '+code)
            m=dict(grades=[int(n) for n in grades[0].split(',')] if grades else [])
            if course:m['course']=course[0]
            parent=parents.get(code)
            if re.match(r'^第[１２３４５６]章',text):
                if parent:corrections.append(dict(code=code,discardedParent=parent,reason='各章は同じ深さ。他章の配下にしない（公式PDF目次）。'))
                parent=None
            if parent:m['parentCode']=parent
            elif not re.match(r'^第[１２３４５６]章',text):raise ValueError('Missing parent: '+code)
            metadata[code]=m
    if any(m.get('parentCode') and m['parentCode'] not in metadata for m in metadata.values()):raise ValueError('Parent outside scope')
    return dict(sources=pinned['sources'],corrections=corrections,items=metadata)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--items',type=Path,required=True)
    parser.add_argument('--hierarchy',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.write_text(json.dumps(extract(args.items,args.hierarchy),ensure_ascii=False,indent=2)+'\n')
