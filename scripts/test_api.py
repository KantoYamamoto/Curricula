import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen, Request
from http.server import ThreadingHTTPServer
from serve import Store, handler_for, ROOT

class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(Store(ROOT / 'data/releases')))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def get(self, path, method='GET'):
        try:
            response = urlopen(Request(self.base + path, method=method), timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read())

    def test_entity_and_release_envelope(self):
        status, body = self.get('/api/v1/releases/pilot-0.1.0/entities/sm.proportion')
        self.assertEqual(status, 200)
        self.assertEqual(body['release'], 'pilot-0.1.0')
        self.assertEqual(body['schemaVersion'], '0.1.0')
        self.assertEqual(body['data']['id'], 'sm.proportion')

    def test_unknown_release_entity_and_context_are_distinct(self):
        for path, code in [('missing/entities/sm.proportion','release_not_found'),
                           ('pilot-0.1.0/entities/missing','id_not_found'),
                           ('pilot-0.1.0/relations?entityId=missing','entity_not_found'),
                           ('pilot-0.1.0/relations?contextId=missing','context_not_found')]:
            status, body = self.get('/api/v1/releases/' + path)
            self.assertEqual(status, 404)
            self.assertEqual(body['error']['code'], code)

    def test_context_filter_preserves_semantics(self):
        status, body = self.get('/api/v1/releases/pilot-0.1.0/relations?entityId=cp.make-table&contextId=ctx.positive')
        self.assertEqual(status, 200)
        self.assertEqual(len(body['relations']), 1)
        self.assertEqual(body['relations'][0]['from'], 'cp.multiply')
        _, empty = self.get('/api/v1/releases/pilot-0.1.0/relations?entityId=cp.make-table&contextId=ctx.signed')
        self.assertEqual(empty['relations'], [])

    def test_empty_does_not_mean_investigated(self):
        _, entity = self.get('/api/v1/releases/pilot-0.1.0/entities/cp.apply')
        _, relations = self.get('/api/v1/releases/pilot-0.1.0/relations?entityId=cp.apply')
        self.assertEqual(entity['data']['prerequisiteStatus'], 'uninvestigated')
        self.assertEqual(relations['relations'], [])

    def test_partial_coverage_survives(self):
        _, body = self.get('/api/v1/releases/pilot-0.1.0/relations?entityId=cp.link-positive')
        alignment = next(r for r in body['relations'] if r['kind'] == 'alignment')
        self.assertEqual(alignment['coverage'], 'partial')
        self.assertIn('反比例', alignment['excluded'])

    def test_unrecognized_queries_fail(self):
        for suffix in ['?contextId=', '?contextId=ctx.positive&contextId=ctx.signed', '?unexpected=x']:
            status, _ = self.get('/api/v1/releases/pilot-0.1.0/relations' + suffix)
            self.assertEqual(status, 400)

    def test_read_only_and_no_filesystem_exposure(self):
        self.assertEqual(self.get('/api/v1/releases', 'POST')[0], 405)
        self.assertFalse(self.get('/api/v1/capabilities')[1]['localEditing'])
        self.assertEqual(self.get('/api/edit/session')[0], 404)
        for path in ['/Package.swift', '/.env', '/%2e%2e/README.md', '/data/releases/pilot-0.1.0.json']:
            self.assertEqual(self.get(path)[0], 404)

    def test_two_release_snapshots_do_not_mix(self):
        original = json.loads((ROOT / 'data/releases/pilot-0.1.0.json').read_text())
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'pilot-0.1.0.json').write_text(json.dumps(original))
            original['release'] = 'pilot-test'
            original['entities'][0]['label'] = '別版のラベル'
            Path(folder, 'pilot-test.json').write_text(json.dumps(original))
            store = Store(folder)
            _, old = store.get('/api/v1/releases/pilot-0.1.0/entities/' + original['entities'][0]['id'], {})
            _, new = store.get('/api/v1/releases/pilot-test/entities/' + original['entities'][0]['id'], {})
            self.assertNotEqual(old['data']['label'], new['data']['label'])

    def test_mislabeled_release_is_rejected(self):
        original = json.loads((ROOT / 'data/releases/pilot-0.1.0.json').read_text())
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'wrong.json').write_text(json.dumps(original))
            with self.assertRaises(ValueError):
                Store(folder)

    def test_structural_outlines_and_source_versions(self):
        _, overview = self.get('/api/v1/releases/examples-0.1.0/overview')
        self.assertEqual(overview['readingOutlines'][0]['id'], 'reading.structure')
        self.assertEqual(len(overview['readingOutlines'][0]['sections']), 6)
        _, body = self.get('/api/v1/releases/examples-0.1.0/frameworks/fw.university-b')
        child = next(e for e in body['items'] if e['id'] == 'fi.university-b-map')
        self.assertEqual(child['parentID'], 'fi.university-b-root')
        _, a = self.get('/api/v1/releases/examples-0.1.0/sources/src.mext-82v12')
        _, b = self.get('/api/v1/releases/examples-0.2.0/sources/src.mext-82v12')
        self.assertEqual(a['data'], b['data'])

    def test_split_snapshots_are_available_independently(self):
        self.assertEqual(self.get('/api/v1/releases/examples-0.1.0/entities/fi.high-school-functions')[0], 200)
        self.assertEqual(self.get('/api/v1/releases/examples-0.2.0/entities/fi.high-school-functions')[0], 404)
        for identifier in ('fi.high-school-formula', 'fi.high-school-properties'):
            self.assertEqual(self.get('/api/v1/releases/examples-0.2.0/entities/' + identifier)[0], 200)
        _, old = self.get('/api/v1/releases/examples-0.1.0/entities/sm.affine')
        _, new = self.get('/api/v1/releases/examples-0.2.0/entities/sm.affine')
        self.assertEqual(old['data'], new['data'])

    def test_opposite_paths_keep_their_context(self):
        _, a = self.get('/api/v1/releases/examples-0.1.0/relations?entityId=cp.map-definition&contextId=ctx.university-a')
        _, b = self.get('/api/v1/releases/examples-0.1.0/relations?entityId=cp.map-definition&contextId=ctx.university-b')
        self.assertEqual({r['kind'] for r in a['relations']}, {'dependency', 'enrollment'})
        self.assertEqual({r['contextID'] for r in a['relations']}, {'ctx.university-a'})
        self.assertEqual({r['contextID'] for r in b['relations']}, {'ctx.university-b'})
        self.assertEqual(b['relations'][0]['from'], 'cp.map-example')

    def test_cross_subject_overview_and_original_hierarchy(self):
        base = '/api/v1/releases/cross-subject-0.1.0/'
        _, overview = self.get(base + 'overview')
        self.assertEqual(len(overview['frameworks']), 8)
        self.assertEqual(len(overview['readingOutlines'][0]['sections']), 11)
        _, moral = self.get(base + 'frameworks/fw.cross-ethics')
        leaf = next(e for e in moral['items'] if e['id'] == 'fi.82k04d0213000000')
        self.assertEqual(leaf['parentID'], 'fi.82k0400210000000')
        self.assertEqual(leaf['externalIDs']['mext:course-of-study'], '82K04D0213000000')
        self.assertIn('誰に対しても', leaf['text'])
        _, source = self.get(base + 'sources/src.mext-84v10')
        self.assertEqual(source['data']['distributionVersion'], '84V10')
        self.assertEqual(len(source['data']['sha256']), 64)

    def test_cross_subject_conditions_partial_coverage_and_release_isolation(self):
        base = '/api/v1/releases/cross-subject-0.1.0/'
        _, write = self.get(base + 'entities/cp.cross-language-write')
        self.assertIn('音声で十分に慣れ親しんだ', write['data']['conditions'])
        _, relation = self.get(base + 'relations?entityId=fi.84i1503322000000')
        self.assertEqual(len(relation['relations']), 2)
        self.assertTrue(all(r['coverage'] == 'partial' and r['excluded'] for r in relation['relations']))
        self.assertEqual(self.get(base + 'entities/sm.proportion')[0], 404)
        self.assertEqual(self.get('/api/v1/releases/pilot-0.1.0/entities/sm.proportion')[0], 200)
        _, releases = self.get('/api/v1/releases')
        self.assertIn('cross-subject-0.1.0', {r['release'] for r in releases['releases']})

    def test_schema_v2_over_http_with_grade_search(self):
        status, body = self.get('/api/v1/releases/cross-subject-0.2.0/entities?stage=elementary&grade=3&subjectId=subject.japanese&kind=goal')
        self.assertEqual(status, 200)
        self.assertEqual(body['schemaVersion'], '0.2.0')
        self.assertEqual(len(body['entities']), 1)
        self.assertEqual(body['entities'][0]['education'][0]['grades'], [3, 4])
        _, details = self.get('/api/v1/releases/cross-subject-0.2.0/entities/' + body['entities'][0]['id'])
        self.assertTrue(details['annotations'] and details['evidence'])

    def test_schema_v2_rejects_bad_queries_and_keeps_read_only_routes(self):
        base = '/api/v1/releases/cross-subject-0.2.0/'
        self.assertEqual(self.get(base+'entities?grade=3')[0], 400)
        self.assertEqual(self.get(base+'entities?subjectId=absent')[0], 404)
        self.assertEqual(self.get(base+'entities/cp.cross-language-write','PATCH')[0], 405)
        self.assertEqual(self.get(base+'resolve/cp.cross-language-write')[0], 200)
