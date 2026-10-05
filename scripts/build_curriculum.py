#!/usr/bin/env python3
"""Build the complete elementary/middle source milestone from pinned, offline inputs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import uuid
from editing_db import ROOT, SwiftValidator, packed

RELEASE = 'curriculum-0.3.0'
NAMESPACE = uuid.UUID('ae5f89b2-756e-43f7-9a12-9d439b345060')
SOURCES = ROOT / 'data/sources/mext'
VERSIONS = (
    ('82V12', 'elementary', '小学校', 3747, '6d9a6dadf1593e15bad7c4e480eeea8dd91866600be2a94965582c8c774d3d7f', '27'),
    ('83V11', 'lowerSecondary', '中学校', 2190, 'b8b5ad6cb52e5cfe5e390312b732b1325fffc5044b20a25e666075c74a569311', '09'),
)
COLLECTIONS = ('taxons', 'sources', 'frameworks', 'contexts', 'entities', 'annotations', 'evidence', 'relations', 'prerequisites', 'readingOutlines', 'changes')


def identifier(key):
    return str(uuid.uuid5(NAMESPACE, key))


def record(key, **fields):
    value = dict(id=identifier(key), **fields)
    value['revisionID'] = identifier('revision:' + hashlib.sha256(packed(value).encode()).hexdigest())
    return value


def ref(value):
    return {k: value[k] for k in ('id', 'revisionID')}


def rows(version):
    entry = next(v for v in VERSIONS if v[0] == version)
    path = SOURCES / (version + '.csv')
    if hashlib.sha256(path.read_bytes()).hexdigest() != entry[4]:
        raise ValueError('Changed pinned source: ' + version)
    values = list(csv.reader(path.read_text(encoding='utf-8-sig').splitlines(keepends=True)))[2:]
    if len(values) != entry[3] or len({r[3] for r in values}) != len(values):
        raise ValueError('Incomplete or duplicate source: ' + version)
    return values


def build():
    metadata = json.loads((SOURCES / 'metadata.json').read_text())
    preambles = json.loads((SOURCES / 'preambles.json').read_text())
    legacy = json.loads((SOURCES / 'legacy-identities.json').read_text())
    data = dict(schemaVersion='0.2.0', release=RELEASE, aliases={}, limitations=[])
    data.update({key: [] for key in COLLECTIONS})
    metadata_sources = []
    for source in metadata['sources']:
        captured = record('source:'+source['url'], kind='webPage', origin='original', title='学習指導要領LOD / '+source['url'].rsplit('/',1)[-1], creators=[source['creator']], publisher=source['creator'], scope='学年・分野、または親子階層の補助メタデータ。本文は文科省CSVを使用。', url=source['url'], identifiers={'license':source['license']}, retrievedOn=source['retrievedOn'], sha256=source['sha256'], verification='82・83で始まる全項目を抽出し、公式コード表と項目集合を照合。章の親関係は公式目次で補正。')
        metadata_sources.append(captured)
        data['sources'].append(captured)
    taxons = {}
    def taxon(label, parent=None):
        key = (label, parent)
        if key not in taxons:
            t = record('taxon:' + packed(key), kind='course' if parent else 'subject', label=label, **({'parentID': parent} if parent else {}))
            old = legacy['taxons'].get(packed(key))
            if old:
                t = old  # Preserve existing subject/course identity and exact revision bytes.
            taxons[key] = t
            data['taxons'].append(t)
        return taxons[key]

    chunks = []
    for version, stage, school, count, sha, suffix in VERSIONS:
        source = record('source:' + version, kind='curriculum', origin='original', title=school+'学習指導要領（平成29年告示）コード表', creators=['文部科学省'], publisher='文部科学省', scope='前文を除く全コード項目。教科、総則、道徳、活動、漢字配当表を含む。', url='https://www.mext.go.jp/content/20230901-mxt_syoto01-000010374_'+suffix+'.csv', promulgatedOn='2017-03-31', edition=version, identifiers={'mext:version':version}, retrievedOn='2026-10-05', sha256=sha, verification='固定した公式CSVの全行・全文字列を照合。')
        data['sources'].append(source)
        preamble = next(p for p in preambles if p['stage'] == stage)
        pdf = record('source:' + stage + ':pdf', kind='curriculum', origin='original', title=school+'学習指導要領（平成29年告示）本文PDF', creators=['文部科学省'], publisher='文部科学省', scope='前文。PDF内の付録法令・他校種・移行措置は収録対象外。', url=preamble['url'], promulgatedOn='2017-03-31', identifiers={}, retrievedOn=preamble['retrievedOn'], sha256=preamble['sha256'], verification=preamble['normalization'])
        data['sources'].append(pdf)
        framework = record('framework:' + stage, label=school+'学習指導要領 全文', issuer='文部科学省', version=version, sourceIDs=[source['id'],pdf['id']], origin='original', education=[])
        data['frameworks'].append(framework)
        outline = record('outline:' + stage, label=school+' / 原文を順に読む', sections=[])
        source_rows = rows(version)
        entities = {}
        # Reuse UUIDs from existing samples; a changed record always gets a distinct revision.
        ids = {c:legacy['entities'].get(c, identifier('mext:' + c)) for _, _, _, c in source_rows}
        groups = {}
        preamble_entity = record('preamble:' + stage, kind='frameworkItem', label='前文', text=preamble['text'], conditions='', education=[dict(stage=stage, gradeStatus='notSpecified', grades=[], subjectID=taxon('前文')['id'])], provenance=dict(origin='original', rationale=preamble['normalization']), frameworkID=framework['id'], externalIDs={}, sourceLocator='前文 / 本文'+ '・'.join(map(str,preamble['printedPages']))+'頁 / PDF '+ '・'.join(map(str,preamble['pdfPages']))+'頁', targetIDs=[], lifecycle='active', successorIDs=[])
        data['entities'].append(preamble_entity)
        def quotation(entity, captured):
            return record('quotation:' + entity['id'], target=ref(entity), field='text', role='quotation', citations=[dict(source=ref(captured), locator=entity['sourceLocator'])], rationale='原典の本文を保持。編集した説明・目標とは別のレコード。')
        data['evidence'].append(quotation(preamble_entity, pdf))
        groups[('前文','preamble')] = [preamble_entity]
        for subject, no, text, code in source_rows:
            m = metadata['items'][code]
            subject_label = '各教科共通' if subject in ('各教科', '各教科（共通）') else '道徳' if subject == '特別の教科　道徳' else subject
            subject_id = taxon(subject_label)['id']
            scope = dict(stage=stage, gradeStatus='specified' if m['grades'] else 'notSpecified', grades=m['grades'], subjectID=subject_id)
            if m.get('course'):
                scope['courseID'] = taxon(m['course'], subject_id)['id']
            # Labels abbreviate display only; full text remains verbatim, including whitespace.
            label = text.splitlines()[0]
            if len(label) > 75: label = label[:75]+'…'
            fields = dict(kind='frameworkItem', label=label, text=text, conditions='', education=[scope], provenance=dict(origin='original', rationale='文部科学省 '+version+' No.'+no+'。階層・学年・分野は固定した補助メタデータ、章の関係は公式目次で補正。'), frameworkID=framework['id'], externalIDs={'mext:course-of-study':code}, sourceLocator=version+' / No.'+no+' / コード '+code, targetIDs=[], lifecycle='active', successorIDs=[])
            if m.get('parentCode'): fields['parentID']=ids[m['parentCode']]
            e = record('mext:' + code, **fields)
            if e['id'] != ids[code]:
                e['id'] = ids[code]
                e['revisionID'] = identifier('revision:' + hashlib.sha256(packed({k:v for k,v in e.items() if k!='revisionID'}).encode()).hexdigest())
            entities[code] = e
            data['aliases'][code] = e['id']
            data['entities'].append(e)
            data['evidence'].append(quotation(e, source))
            data['evidence'].append(record('education:'+e['id'], target=ref(e), field='education', role='supports', citations=[dict(source=ref(source), locator=e['sourceLocator']), dict(source=ref(metadata_sources[0]), locator='項目 '+code+' / cs:grade・cs:subject')], rationale='教科は公式CSVの教科列、学年・分野はLODの同一コードのメタデータを専用属性に変換。学年指定のない項目へ全学年を推測して付けない。'))
            # Grade/course work units, plus the six kanji lists and their shared heading.
            parent = code
            kanji = False
            while parent:
                if parent == '8210000100000000': kanji=True; break
                parent = metadata['items'][parent].get('parentCode')
            part = ('漢字配当表 / ' if kanji else '') + (('・'.join(map(str,m['grades']))+'年') if m['grades'] else '共通・取扱い')
            if m.get('course'):part += ' / '+m['course']
            groups.setdefault((subject,part),[]).append(e)
        for (subject,part), items in groups.items():
            key = stage+':'+subject+':'+part
            label = subject if part=='preamble' else subject+' / '+part
            section = record('section:'+key, label=label, entityIDs=[e['id'] for e in items])
            outline['sections'].append(section)
            # raw status is verified against concrete rows, not manually toggled.
            chunks.append(dict(id=identifier('work:'+key), order=len(chunks)+1, stage=stage, subject=subject, label=school+' '+label, release=RELEASE, outlineID=outline['id'], sectionID=section['id'], entityIDs=section['entityIDs'], original=dict(status='complete', expected=len(items), imported=len(items)), goals=dict(status='pending', reviewedOriginalIDs=[], goalIDs=[], annotationIDs=[])))
        # Outline revision covers the ordered section manifest, too.
        outline = record('outline:'+stage, label=outline['label'], sections=outline['sections'])
        data['readingOutlines'].append(outline)
        data['aliases']['reading.'+stage] = outline['id']
    expected = {r[3] for v in VERSIONS for r in rows(v[0])}
    if expected != set(metadata['items']):raise ValueError('Metadata coverage differs from source')
    ledger = dict(version=1, milestone='原文全範囲収録', updatedOn='2026-10-05', release=RELEASE, scope='平成29年告示の小学校・中学校学習指導要領（82V12・83V11）。前文・総則・各教科・道徳・活動・漢字配当表。', sequence='原文全範囲 → 小学校の各教科を掲載順・学年順 → 中学校の各教科を掲載順・学年順 → 道徳・活動の整理。共通の目標と取扱いも各教科の整理時に確認。', next='小学校 国語 / 1・2年：学ぶ対象・目標・必要な判定注釈を整理。', totals=dict(codedItems=len(expected), preambles=len(preambles), originalItems=len(data['entities']), originalChunks=len(chunks), goalChunksComplete=0), chunks=chunks, metadataSources=metadata['sources'])
    return data, ledger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'data/catalog')
    parser.add_argument('--progress', type=Path, default=ROOT/'data/coverage.json')
    args = parser.parse_args()
    dataset, progress = build()
    result = SwiftValidator().check(dataset, [])
    if result['issues']:raise ValueError(result['issues'])
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/(RELEASE+'.json')).write_text(result['canonical'])
    args.progress.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n')
    print(f'{RELEASE}: {len(dataset["entities"])} 原文項目 / {len(progress["chunks"])} 区切り')


if __name__ == '__main__': main()
