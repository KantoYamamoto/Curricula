from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from editing_api import EditingAPI
from editing_db import Database, EditError, ROOT
from serve import Store, handler_for


class DatabaseFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed_folder = tempfile.TemporaryDirectory()
        cls.seed = Database(Path(cls.seed_folder.name) / 'seed.sqlite3')
        cls.seed.seed(ROOT / 'data/releases')

    @classmethod
    def tearDownClass(cls):
        cls.seed_folder.cleanup()

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / 'authoring.sqlite3'
        self.seed.backup(self.path)
        self.db = Database(self.path)
        self.detail = self.db.create('cross-subject-0.2.0', '国語の編集')
        data = self.detail['dataset']
        self.entity = next(e for e in data['entities'] if e['id'] == data['aliases']['cp.cross-japanese-middle'])
        self.draft_id = self.detail['draft']['id']

    def tearDown(self):
        self.folder.cleanup()

    def payload(self, detail=None, confirm=True):
        d = detail or self.detail
        data = d['dataset']
        entity = next(e for e in data['entities'] if e['id']==self.entity['id'])
        notes = [a for a in data['annotations'] if a['goal']['id']==entity['id']]
        evidence = [e for e in data['evidence'] if e['target']['id'] in [entity['id']]+[a['id'] for a in notes]]
        return dict(expectedHead=d['draft']['head_id'], entityID=entity['id'], entity={'text':entity['text']+'（編集例）'},
                    confirmAnnotationIDs=[a['id'] for a in notes] if confirm else [],
                    confirmEvidenceIDs=[e['id'] for e in evidence] if confirm else [], reason='記述を明確にする')

    def assert_error(self, code, operation):
        with self.assertRaises(EditError) as context:
            operation()
        self.assertEqual(context.exception.code,code)

class DatabaseTests(DatabaseFixture):
    def test_all_seed_snapshots_roundtrip_exactly_and_keep_indexes(self):
        for dataset in self.db.published():
            self.assertEqual(self.db.export(dataset['release']), (ROOT / 'data/releases' / (dataset['release']+'.json')).read_bytes())
        with self.db.connection() as db:
            self.assertGreater(db.execute('SELECT count(*) FROM education_scopes').fetchone()[0],0)
            self.assertGreater(db.execute('SELECT count(*) FROM scope_grades WHERE grade=3').fetchone()[0],0)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_restart_seed_is_idempotent_and_retains_draft(self):
        saved=self.db.save(self.draft_id,self.payload())
        reopened=Database(self.path)
        reopened.seed(ROOT / 'data/releases')
        self.assertEqual(reopened.detail(self.draft_id),saved)

    def test_goal_edit_keeps_identity_changes_revision_and_explicit_pins(self):
        saved=self.db.save(self.draft_id,self.payload())
        new=next(e for e in saved['dataset']['entities'] if e['id']==self.entity['id'])
        self.assertNotEqual(new['revisionID'],self.entity['revisionID'])
        self.assertEqual(saved['issues'],[])
        self.assertEqual(len(saved['events']),1)
        self.assertTrue(saved['events'][0]['details']['confirmedEvidence'])
        self.assertEqual(self.db.export(self.detail['base']['release']), (ROOT / 'data/releases/cross-subject-0.2.0.json').read_bytes())

    def test_unconfirmed_pins_save_as_draft_but_block_review(self):
        saved=self.db.save(self.draft_id,self.payload(confirm=False))
        self.assertTrue(saved['issues'])
        self.assertEqual({i['code'] for i in saved['issues']},{'staleRevision'})
        self.assert_error('validation_failed',lambda:self.db.review(self.draft_id,saved['draft']['head_id'],'確認した'))
        confirm=self.payload(saved)
        confirm['entity']={}
        complete=self.db.save(self.draft_id,confirm)
        self.assertEqual(complete['issues'],[])

    def test_annotation_only_edit_revises_its_evidence_without_changing_goal(self):
        payload=self.payload()
        payload['entity']={}
        note=next(a for a in self.detail['dataset']['annotations'] if a['goal']['id']==self.entity['id'])
        payload['annotations']={note['id']:note['text']+'（確認例）'}
        saved=self.db.save(self.draft_id,payload)
        self.assertEqual(saved['issues'],[])
        new=next(e for e in saved['dataset']['entities'] if e['id']==self.entity['id'])
        self.assertEqual(new,self.entity)
        revised=next(a for a in saved['dataset']['annotations'] if a['id']==note['id'])
        self.assertNotEqual(note['revisionID'],revised['revisionID'])

    def test_new_optional_annotation_is_preserved_without_assessor(self):
        p=self.payload();p['entity']={};p['newAnnotation']='説明の中で資料に触れているかを見る'
        saved=self.db.save(self.draft_id,p)
        new=saved['dataset']['annotations'][-1]
        self.assertEqual(new['evaluationMode'],'unspecified')
        self.assertEqual(saved['issues'],[])
        self.assertNotIn('evaluatorID',new)

    def test_original_edit_and_identity_injection_are_rejected_without_partial_save(self):
        original=next(e for e in self.detail['dataset']['entities'] if e['kind']=='frameworkItem')
        p=self.payload();p['entityID']=original['id']
        self.assert_error('original_or_retired_read_only',lambda:self.db.save(self.draft_id,p))
        p=self.payload();p['entity']['revisionID']='forged'
        self.assert_error('invalid_edit',lambda:self.db.save(self.draft_id,p))
        p=self.payload();p['entity']['text']=''
        self.assert_error('validation_failed',lambda:self.db.save(self.draft_id,p))
        self.assertEqual(self.db.detail(self.draft_id)['draft']['head_id'],self.detail['draft']['head_id'])
        self.assertEqual(self.db.detail(self.draft_id)['events'],[])

    def test_simultaneous_saves_accept_one_and_report_conflict(self):
        payload=self.payload()
        barrier=threading.Barrier(2)
        def save(_):
            barrier.wait()
            try:
                Database(self.path).save(self.draft_id,payload)
                return 'saved'
            except EditError as error:
                return error.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(save,range(2))),['edit_conflict','saved'])
        self.assertEqual(len(self.db.detail(self.draft_id)['events']),1)

    def test_review_is_bound_to_head_and_publication_is_immutable(self):
        saved=self.db.save(self.draft_id,self.payload())
        head=saved['draft']['head_id']
        self.assert_error('review_required',lambda:self.db.publish(self.draft_id,head,'local-0.3.0'))
        self.db.review(self.draft_id,head,'文言・観点と引用箇所を確認')
        edited=self.db.save(self.draft_id,self.payload(saved))
        self.assertIsNone(edited['review'])
        self.assert_error('edit_conflict',lambda:self.db.publish(self.draft_id,head,'local-0.3.0'))
        head=edited['draft']['head_id']
        self.assert_error('review_required',lambda:self.db.publish(self.draft_id,head,'local-0.3.0'))
        self.db.review(self.draft_id,head,'改訂後の差分を確認')
        self.db.publish(self.draft_id,head,'local-0.3.0')
        data=json.loads(self.db.export('local-0.3.0'))
        self.assertEqual(data['release'],'local-0.3.0')
        self.assertEqual(len(data['changes']),1)
        self.assertEqual(data['changes'][0]['before'][0]['release'],'cross-subject-0.2.0')
        self.assertEqual(data['changes'][0]['after'][0]['release'],'local-0.3.0')
        self.assert_error('draft_already_published',lambda:self.db.save(self.draft_id,self.payload(edited)))
        new=self.db.create('local-0.3.0','次の編集')
        self.assertEqual(new['dataset'],data)

    def test_backup_restores_all_history_and_identical_exports(self):
        saved=self.db.save(self.draft_id,self.payload())
        backup=Path(self.folder.name)/'backup.sqlite3'
        self.db.backup(backup)
        restored=Database(backup)
        restored.verify()
        self.assertEqual(restored.detail(self.draft_id),saved)
        for d in self.db.published():
            self.assertEqual(self.db.export(d['release']),restored.export(d['release']))
        self.assert_error('backup_destination_exists',lambda:self.db.backup(backup))

    def test_publication_reasons_follow_each_changed_entity(self):
        first_id = self.entity['id']
        saved = self.db.save(self.draft_id,self.payload())
        self.entity = next(e for e in saved['dataset']['entities'] if e['id'] == saved['dataset']['aliases']['cp.cross-science-knowledge'])
        second = self.payload(saved)
        second['reason'] = '理科の記述を整える'
        saved = self.db.save(self.draft_id,second)
        head = saved['draft']['head_id']
        self.db.review(self.draft_id,head,'二つの目標の差分を確認')
        self.db.publish(self.draft_id,head,'local-two-0.3.0')
        changes = json.loads(self.db.export('local-two-0.3.0'))['changes']
        reasons = {c['after'][0]['record']['id']: c['rationale'] for c in changes}
        self.assertEqual(reasons[first_id],'記述を明確にする')
        self.assertEqual(reasons[self.entity['id']],'理科の記述を整える')

    def test_database_refuses_mutation_of_immutable_revision(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with self.db.connection(write=True) as db:
                db.execute('UPDATE revisions SET payload=? WHERE record_id=?', ('{}',self.entity['id']))

    def test_lossy_exchange_conversion_fails_explicitly(self):
        data=deepcopy(self.detail['dataset']);data['unexpectedField']='do not discard'
        self.assert_error('lossy_exchange_conversion',lambda:self.db.validator.check(data,[]))


class EditingHTTPTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(Store(ROOT/'data/releases',self.db),EditingAPI(self.db,'test-token')))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
        super().tearDown()

    def request(self,path,payload=None,headers=None):
        headers=headers if headers is not None else {'Content-Type':'application/json','Origin':self.base,'X-Curricula-Token':'test-token'}
        request=Request(self.base+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers)
        try: response=urlopen(request,timeout=5)
        except HTTPError as error: response=error
        with response:
            raw=response.read()
            return response.status,json.loads(raw)

    def test_http_local_session_and_origin_are_required_for_writes(self):
        path=f'/api/edit/drafts/{self.draft_id}/save'
        payload=self.payload()
        for headers in [{},{'Content-Type':'application/json','Origin':'https://example.org','X-Curricula-Token':'test-token'},
                        {'Content-Type':'application/json','Origin':self.base,'X-Curricula-Token':'wrong'}]:
            self.assertEqual(self.request(path,payload,headers)[0],403)
        self.assertEqual(self.request(path,payload)[0],200)
        self.assertEqual(self.request(path,payload)[0],409)
        self.assertEqual(self.request('/api/v1/releases/cross-subject-0.2.0/entities/x',payload)[0],405)
        self.assertEqual(self.request('/api/edit/session',headers={'Host':'example.org'})[0],403)

    def test_http_published_release_is_readable_draft_is_not(self):
        saved=self.db.save(self.draft_id,self.payload())
        self.assertEqual(self.request('/api/v1/releases/'+saved['dataset']['release']+'/overview')[0],404)
        head=saved['draft']['head_id']
        self.assertEqual(self.request(f'/api/edit/drafts/{self.draft_id}/review',dict(expectedHead=head,note='差分・出典を確認'))[0],200)
        self.assertEqual(self.request(f'/api/edit/drafts/{self.draft_id}/publish',dict(expectedHead=head,release='local-http-0.3.0'))[0],200)
        status,body=self.request('/api/v1/releases/local-http-0.3.0/entities/'+self.entity['id'])
        self.assertEqual(status,200)
        self.assertIn('編集例',body['data']['text'])
        self.assertEqual(self.request('/api/edit/releases/local-http-0.3.0/export')[0],200)
        self.assertTrue(self.request('/api/v1/capabilities')[1]['localEditing'])
        self.assertEqual(self.request(f'/api/edit/drafts/{self.draft_id}/history/'+saved['draft']['head_id'])[0],200)
