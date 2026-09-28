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
