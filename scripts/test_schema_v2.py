import json
from pathlib import Path
import tempfile
import unittest
from serve import Store, ROOT
from allocate_identity import allocate

class V2Tests(unittest.TestCase):
    def setUp(self):
        self.store = Store(ROOT / 'data/releases')
        self.base = '/api/v1/releases/cross-subject-0.2.0/'

    def get(self, suffix, query=None):
        return self.store.get(self.base + suffix, query or {})

    def test_uuid_and_alias_resolve_same_record(self):
        status, by_alias = self.get('entities/cp.cross-language-write')
        self.assertEqual(status, 200)
        uid = by_alias['data']['id']
        self.assertEqual(len(uid), 36)
        self.assertEqual(self.get('entities/' + uid)[1], by_alias)
        self.assertEqual(self.get('resolve/cp.cross-language-write')[1]['data']['id'], uid)
        self.assertEqual(by_alias['schemaVersion'], '0.2.0')

    def test_grade_bands_and_subject_intersection(self):
        status, body = self.get('entities', {'stage':['elementary'], 'grade':['3'], 'subjectId':['subject.japanese'], 'kind':['goal']})
        self.assertEqual(status, 200)
        self.assertEqual(len(body['entities']), 1)
        middle = self.get('entities/cp.cross-japanese-middle')[1]['data']
        self.assertEqual(body['entities'][0]['id'], middle['id'])
        _, mixed = self.get('entities', {'stage':['upperSecondary'], 'subjectId':['subject.japanese']})
        self.assertEqual(mixed['entities'], [])

    def test_unspecified_grade_not_falsely_assigned_to_highschool_year(self):
        _, all_info = self.get('entities', {'courseId':['course.information'], 'kind':['goal']})
        self.assertEqual(len(all_info['entities']), 2)
        _, grade_info = self.get('entities', {'stage':['upperSecondary'], 'grade':['1'], 'courseId':['course.information']})
        self.assertEqual(grade_info['entities'], [])
        for query in [{'grade':['3']}, {'stage':['elementary'],'grade':['7']}, {'stage':['missing']}, {'grade':['-1'],'stage':['elementary']}, {'stage':['elementary','lowerSecondary']}]:
            self.assertEqual(self.get('entities', query)[0], 400)

    def test_goal_annotations_and_evidence_are_pinned(self):
        _, body = self.get('entities/cp.cross-science-inquiry')
        self.assertTrue(body['annotations'])
        self.assertTrue(all(a['goal']['revisionID'] == body['data']['revisionID'] for a in body['annotations']))
        self.assertTrue(any(e['field'] == 'conditions' for e in body['evidence']))
        for evidence in body['evidence']:
            for citation in evidence['citations']:
                _, source = self.get('sources/' + citation['source']['id'])
                self.assertEqual(citation['source']['revisionID'], source['data']['revisionID'])
        _, moral = self.get('entities/goal.cross-ethics')
        self.assertEqual(moral['annotations'], [])
        self.assertEqual(moral['data']['kind'], 'goal')
        self.assertIn('誰に対しても', moral['data']['text'])

    def test_relations_accept_aliases_and_do_not_mix_releases(self):
        status, body = self.get('relations', {'entityId':['cp.cross-language-write']})
        self.assertEqual(status, 200)
        self.assertEqual(len(body['relations']), 1)
        old = self.store.get('/api/v1/releases/cross-subject-0.1.0/entities/cp.cross-language-write', {})[1]
        self.assertEqual(old['data']['kind'], 'competency')
        self.assertEqual(old['data']['id'], 'cp.cross-language-write')

    def test_edit_split_merge_routes_and_prerequisites(self):
        base = '/api/v1/releases/editing-0.2.3/'
        _, body = self.store.get(base+'entities/goal.editing.combined', {})
        self.assertEqual(body['data']['lifecycle'], 'retired')
        self.assertEqual(len(body['data']['successorIDs']), 2)
        self.assertEqual(body['changes'][0]['kind'], 'split')
        for change in body['changes']:
            for endpoint in change['before']+change['after']:
                path = '/api/v1/releases/'+endpoint['release']+'/entities/'+endpoint['record']['id']
                _, value = self.store.get(path,{})
                self.assertEqual(value['data']['revisionID'],endpoint['record']['revisionID'])
        _, prereq = self.store.get(base+'prerequisites', {'entityId':['goal.editing.target']})
        self.assertEqual(prereq['prerequisites'][0]['expression']['op'], 'anyOf')
        _, sources = self.store.get(base+'sources/src.synthetic-syllabus', {})
        self.assertNotIn('promulgatedOn', sources['data'])

    def test_registry_allocation_is_explicit_and_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'ids.json'
            first = allocate(path,'sample','1')
            self.assertEqual(first,allocate(path,'sample','1'))
            second = allocate(path,'sample','2')
            self.assertEqual(first[0],second[0]); self.assertNotEqual(first[1],second[1])

    def test_duplicate_annotation_is_not_silently_indexed(self):
        from schema_v2_store import Index
        data = json.loads((ROOT/'data/releases/cross-subject-0.2.0.json').read_text())
        data['annotations'].append(data['annotations'][0])
        with self.assertRaises(ValueError):
            Index(data)

    def test_prerequisite_context_filter_is_explicit(self):
        base = '/api/v1/releases/editing-0.2.0/prerequisites'
        status, body = self.store.get(base, {'entityId':['goal.editing.target'],'contextId':['ctx.editing']})
        self.assertEqual(status,200)
        self.assertEqual(len(body['prerequisites']),1)
        self.assertEqual(self.store.get(base, {'contextId':['missing']})[0],404)
