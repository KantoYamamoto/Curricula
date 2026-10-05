"""Indexed read operations for schema 0.2.0; UUIDs are primary, aliases are lookup keys."""
COLLECTIONS = ('taxons', 'sources', 'frameworks', 'contexts', 'entities', 'annotations', 'evidence', 'relations', 'prerequisites', 'readingOutlines', 'changes')

class Index:
    def __init__(self, data):
        self.data = data
        self.collections = {key: {r['id']: r for r in data[key]} for key in COLLECTIONS}
        if any(len(data[key]) != len(self.collections[key]) for key in COLLECTIONS):
            raise ValueError("Duplicate IDs in schema 0.2.0 collection")
        self.records = {}
        self.kinds = {}
        for collection, records in self.collections.items():
            for identifier, record in records.items():
                if identifier in self.records:
                    raise ValueError('Duplicate record ID')
                self.records[identifier] = record
                self.kinds[identifier] = collection
        for outline in data['readingOutlines']:
            for section in outline['sections']:
                if section['id'] in self.records:
                    raise ValueError('Duplicate section ID')
                self.records[section['id']] = section
                self.kinds[section['id']] = 'sections'
        self.aliases = data['aliases']
        if not all(identifier in self.records for identifier in self.aliases.values()):
            raise ValueError('Dangling alias')
        self.annotations = {}
        for annotation in data['annotations']:
            self.annotations.setdefault(annotation['goal']['id'], []).append(annotation)
        for annotations in self.annotations.values():
            annotations.sort(key=lambda a: a['position'])
        self.evidence = {}
        for evidence in data['evidence']:
            self.evidence.setdefault(evidence['target']['id'], []).append(evidence)

    def resolve(self, value):
        return self.aliases.get(value, value)

    def details(self, entity):
        annotations = self.annotations.get(entity['id'], [])
        evidence = self.evidence.get(entity['id'], []) + [e for a in annotations for e in self.evidence.get(a['id'], [])]
        return dict(annotations=annotations, evidence=evidence,
                    prerequisites=[p for p in self.data['prerequisites'] if p['targetGoalID'] == entity['id']],
                    changes=[c for c in self.data['changes'] if any(e['record']['id'] == entity['id'] for e in c['before'] + c['after'])])

    def get(self, resource, identifier, query):
        def error(status, code):
            return status, {'error': {'code': code}}
        if resource == 'reading-sections' and identifier and not query:
            resolved = self.resolve(identifier)
            section = self.records.get(resolved)
            if self.kinds.get(resolved) != 'sections':
                return error(404, 'id_not_found')
            return 200, {'data': section, 'entities': [dict(data=self.records[i], **self.details(self.records[i])) for i in section['entityIDs']]}
        if resource == 'resolve' and identifier and not query:
            record_id = self.resolve(identifier)
            record = self.records.get(record_id)
            if record is None:
                return error(404, 'id_not_found')
            return 200, {'data': {'id': record_id, 'revisionID': record['revisionID'], 'collection': self.kinds[record_id]}}
        if resource == 'entities' and identifier is None:
            allowed = {'stage', 'grade', 'subjectId', 'courseId', 'kind'}
            if any(k not in allowed or len(v) != 1 or not v[0] for k, v in query.items()):
                return error(400, 'invalid_query')
            q = {k: v[0] for k, v in query.items()}
            if q.get('stage') and q['stage'] not in ('elementary', 'lowerSecondary', 'upperSecondary', 'higherEducation', 'other'):
                return error(400, 'invalid_stage')
            if q.get('kind') and q['kind'] not in ('goal', 'subjectMatter', 'frameworkItem'):
                return error(400, 'invalid_kind')
            if 'grade' in q:
                if not q['grade'].isascii() or not q['grade'].isdigit() or int(q['grade']) < 1 or 'stage' not in q:
                    return error(400, 'invalid_grade')
                maximum = {'elementary': 6, 'lowerSecondary': 3, 'upperSecondary': 3}.get(q['stage'])
                if maximum and int(q['grade']) > maximum:
                    return error(400, 'invalid_grade')
            for key, kind in [('subjectId', 'subject'), ('courseId', 'course')]:
                if key in q:
                    q[key] = self.resolve(q[key])
                    if self.collections['taxons'].get(q[key], {}).get('kind') != kind:
                        return error(404, 'taxon_not_found')
            def matches(e):
                if e['lifecycle'] != 'active' or ('kind' in q and e['kind'] != q['kind']):
                    return False
                if not any(k in q for k in ('stage', 'grade', 'subjectId', 'courseId')):
                    return True
                return any(('stage' not in q or s['stage'] == q['stage']) and
                           ('grade' not in q or s['gradeStatus'] == 'specified' and int(q['grade']) in s['grades']) and
                           ('subjectId' not in q or s['subjectID'] == q['subjectId']) and
                           ('courseId' not in q or s.get('courseID') == q['courseId']) for s in e['education'])
            return 200, {'entities': [e for e in self.data['entities'] if matches(e)], 'gradePolicy': 'explicit_only'}
        if resource in ('evidence', 'prerequisites', 'changes') and identifier is None:
            key = 'targetId' if resource == 'evidence' else 'entityId'
            allowed = {key, 'contextId'} if resource == 'prerequisites' else {key}
            if any(k not in allowed or len(v) != 1 or not v[0] for k, v in query.items()):
                return error(400, 'invalid_query')
            target = self.resolve(query[key][0]) if key in query else None
            if target and target not in self.records:
                return error(404, 'id_not_found')
            records = self.data[resource]
            if resource == 'prerequisites' and 'contextId' in query:
                context = self.resolve(query['contextId'][0])
                if context not in self.collections['contexts']:
                    return error(404, 'context_not_found')
                records = [p for p in records if p['contextID'] == context]
            if target:
                if resource == 'evidence': records = [e for e in records if e['target']['id'] == target]
                elif resource == 'prerequisites': records = [p for p in records if p['targetGoalID'] == target]
                else: records = [c for c in records if any(r['record']['id'] == target for r in c['before'] + c['after'])]
            return 200, {resource: records}
        names = {'reading-outlines': 'readingOutlines', **{key: key for key in COLLECTIONS}}
        if resource in names and identifier and not query:
            entry = self.collections[names[resource]].get(self.resolve(identifier))
            if entry is None:
                return error(404, 'id_not_found')
            payload = {'data': entry}
            if resource == 'entities': payload.update(self.details(entry))
            elif resource == 'frameworks': payload['items'] = [e for e in self.data['entities'] if e.get('frameworkID') == entry['id']]
            return 200, payload
        return error(400 if query else 404, 'unknown_query' if query else 'route_not_found')
