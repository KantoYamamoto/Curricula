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
