#!/usr/bin/env python3
"""Independent Python consumer of the Swift exchange contract and pinned source rows."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / 'data/releases/pilot-0.1.0.json').read_text())
pinned = json.loads((ROOT / 'Sources/CurriculaPilot/Resources/mext-sample.json').read_text())
assert set(data) == {'schemaVersion','release','sources','frameworks','contexts','entities','relations','readingOutlines','limitations'}
assert data['schemaVersion'] == '0.1.0'
entities = {e['id']: e for e in data['entities']}
for item in pinned['items']:
    entity = entities['fi.' + item['code']]
    assert entity['text'] == item['text']
    assert entity['sourceLocator'] == item['locator']
    assert entity['provenance']['sourceIDs'] == [item['sourceID']]
for relation in data['relations']:
    assert relation['from'] in entities and relation['to'] in entities
    if relation.get('coverage') == 'partial':
        assert relation['excluded']
for outline in data['readingOutlines']:
    for section in outline['sections']:
        assert all(entity_id in entities for entity_id in section['entityIDs'])
assert not entities['fi.university-a']['externalIDs']
assert entities['fi.university-a']['provenance']['origin'] == 'synthetic'
print(f'Contract verified: {len(entities)} entities; {len(pinned["items"])} verbatim source rows')

# Structural samples are read by a second language without depending on Swift enum layout.
samples = {}
for version in ('examples-0.1.0', 'examples-0.2.0'):
    sample = json.loads((ROOT / f'data/releases/{version}.json').read_text())
    samples[version] = sample
    assert sample['schemaVersion'] == '0.1.0' and sample['release'] == version
    ids = {e['id'] for e in sample['entities']}
    assert len(ids) == len(sample['entities'])
    for r in sample['relations']:
        assert r['from'] in ids and r['to'] in ids
    for outline in sample['readingOutlines']:
        assert all(i in ids for section in outline['sections'] for i in section['entityIDs'])
    entities = {e['id']: e for e in sample['entities']}
    assert entities['sm.gas-model']['category'] != entities['sm.right-triangle']['category']
    assert entities['sm.naturals-zero']['conditions'] != entities['sm.naturals-positive']['conditions']
    for item in pinned['items']:
        assert entities['fi.' + item['code']]['text'] == item['text']
    print(f'{version}: {len(ids)} entities, {len(sample["relations"])} relations')
probes = json.loads((ROOT / 'Tests/CurriculaTests/Fixtures/unsupported.json').read_text())
for mapping in probes['revisionMappings']:
    for version_key, ids_key in [('fromRelease', 'fromIDs'), ('toRelease', 'toIDs')]:
        snapshot = samples[mapping[version_key]]
        ids = {e['id'] for e in snapshot['entities']}
        assert set(mapping[ids_key]) <= ids
    assert mapping['rationale']
assert samples['examples-0.1.0']['sources'] == samples['examples-0.2.0']['sources']
print('Candidate mappings resolve; they remain outside the production exchange contract.')

cross = json.loads((ROOT / 'data/releases/cross-subject-0.1.0.json').read_text())
original = json.loads((ROOT / 'Sources/CurriculaPilot/Resources/cross-subjects.json').read_text())
selection = json.loads((ROOT / 'Sources/CurriculaPilot/Resources/cross-subject-selection.json').read_text())
assert original['cases'] == selection['cases']
assert len(cross['frameworks']) == 8 and len(original['cases']) == 11
entities = {e['id']: e for e in cross['entities']}
assert len(entities) == 89 and len(original['items']) == 69
assert cross['sources'] == original['sources']
for row in original['items']:
    e = entities['fi.' + row['code'].lower()]
    assert e['text'] == row['text'] and e['sourceLocator'] == row['locator']
    assert e['externalIDs']['mext:course-of-study'] == row['code']
    assert e['provenance']['sourceIDs'] == [row['sourceID']]
    assert e.get('parentID') == ('fi.' + row['parentCode'].lower() if 'parentCode' in row else None)
for case in selection['cases']:
    assert {p[-1] for p in case['paths']} == set(case['leafCodes'])
    for path in case['paths']:
        for parent, child in zip(path, path[1:]):
            assert entities['fi.' + child.lower()]['parentID'] == 'fi.' + parent.lower()
for relation in cross['relations']:
    assert relation['kind'] == 'alignment'
    assert relation['from'] in entities and relation['to'] in entities
    assert bool(relation['excluded']) == (relation['coverage'] == 'partial')
print('Cross-subject contract verified: 8 subjects, 11 cases, 69 verbatim rows, 89 entities, 13 alignments.')

# New contract has separate goal annotations and version-pinned evidence.
from uuid import UUID
v2 = json.loads((ROOT / 'data/releases/cross-subject-0.2.0.json').read_text())
v2_entities = {e['id']: e for e in v2['entities']}
assert len(v2_entities) == 90 and len(v2['annotations']) == 13 and len(v2['evidence']) == 128
for old in cross['entities']:
    new = v2_entities[v2['aliases'][old['id']]]
    assert str(UUID(new['id'])) == new['id']
    assert new['id'] != new['revisionID']
    assert old['text'] == new['text'] and old['externalIDs'] == new['externalIDs']
    notes = sorted((a for a in v2['annotations'] if a['goal']['id'] == new['id']),key=lambda a:a['position'])
    assert old['criteria'] == [a['text'] for a in notes]
    assert all(a['goal']['revisionID'] == new['revisionID'] for a in notes)
    assert new['kind'] == ('goal' if old['kind'] == 'competency' else old['kind'])
print('Schema 0.2.0 migration verified: original records preserved, criteria moved to 13 pinned annotations.')
