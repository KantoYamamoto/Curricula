from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from editing_db import Database, EditError, ROOT
from editing_api import EditingAPI
from test_editing_db import DatabaseFixture
from authoring_work import offline_coverage, work_records
from schema_v2_store import Index
from serve import Store


class CreationTests(DatabaseFixture):
    def new(self,detail=None,kind='goal'):
        d=detail or self.detail
        source=next(e for e in d['dataset']['entities'] if e['kind']=='frameworkItem' and e['education']==self.entity['education'])
        return dict(expectedHead=d['draft']['head_id'],kind=kind,label='文章の内容を捉える',text='文章の内容を捉え、自分の言葉で説明できる。',educationFrom=source['id'],sourceItemIDs=[source['id']],targetIDs=self.entity['targetIDs'] if kind=='goal' else [],annotations=['文章のどの内容を捉えたかを確認する。'] if kind=='goal' else [],reason='原文の内容を対象と目標に分けて整理')

    def test_create_goal_keeps_originals_and_pins_targets_annotations_sources(self):
        before=deepcopy(self.detail['dataset'])
        created=self.db.add_entity(self.draft_id,self.new())
        entity=next(e for e in created['dataset']['entities'] if e['id']==created['createdEntityID'])
        self.assertEqual(created['issues'],[])
        self.assertEqual(entity['kind'],'goal')
        self.assertEqual(entity['provenance']['origin'],'editorial')
        self.assertEqual(entity['education'],self.entity['education'])
        source=self.new()['sourceItemIDs'][0]
        quotes=[e for e in created['dataset']['evidence'] if e['target']['id']==entity['id']]
        self.assertEqual({e['field'] for e in quotes},{'text','education'})
        self.assertTrue(all(e['citations'][0]['item']['id']==source for e in quotes))
        annotation=next(a for a in created['dataset']['annotations'] if a['goal']['id']==entity['id'])
        self.assertEqual(annotation['goal']['revisionID'],entity['revisionID'])
        self.assertEqual(annotation['evaluationMode'],'unspecified')
        self.assertEqual([e for e in created['dataset']['entities'] if e['kind']=='frameworkItem'],[e for e in before['entities'] if e['kind']=='frameworkItem'])
        outline=next(o for o in created['dataset']['readingOutlines'] if o['id']==created['dataset']['aliases']['reading.authored'])
        self.assertEqual(outline['sections'][0]['entityIDs'],[entity['id']])
        self.assertIn(entity['id'],[e['id'] for e in Index(created['dataset']).derived[source].values()])

    def test_creation_rejects_forged_identity_bad_source_and_scope_atomically(self):
        for patch in ({'id':self.entity['id']},{'kind':'frameworkItem'},{'educationFrom':{}},{'sourceItemIDs':[self.entity['id']]},{'sourceItemIDs':[self.new()['sourceItemIDs'][0]]*2},{'annotations':['x'],'kind':'subjectMatter'}):
            payload={**self.new(),**patch}
            with self.assertRaises(EditError):self.db.add_entity(self.draft_id,payload)
            self.assertEqual(self.db.detail(self.draft_id)['draft']['head_id'],self.detail['draft']['head_id'])

    def test_source_links_are_explicit_and_go_stale_after_an_edit(self):
        created=self.db.add_entity(self.draft_id,self.new())
        entity=created['createdEntityID'];source=self.new()['sourceItemIDs'][0]
        linked=self.db.add_evidence(self.draft_id,dict(expectedHead=created['draft']['head_id'],entityID=entity,field='text',sourceItemIDs=[source],reason='参照する原文を追加確認'))
        saved=self.db.save(self.draft_id,dict(expectedHead=linked['draft']['head_id'],entityID=entity,entity={'text':'文章の内容を自分の言葉で説明する。'},reason='目標の表現を調整'))
        self.assertTrue(saved['issues'])
        self.assertTrue(all(i['code']=='staleRevision' for i in saved['issues']))
        self.assert_error('validation_failed',lambda:self.db.review(self.draft_id,saved['draft']['head_id'],'確認'))

    def test_creation_conflicts_and_publication_supports_new_identity(self):
        created=self.db.add_entity(self.draft_id,self.new(kind='subjectMatter'))
        self.assert_error('edit_conflict',lambda:self.db.add_entity(self.draft_id,self.new()))
        reviewed=self.db.review(self.draft_id,created['draft']['head_id'],'原文と新しい対象を確認')
        self.db.publish(self.draft_id,reviewed['draft']['head_id'],'creation-test')
        published=self.db.published('creation-test')[0]
        self.assertIn(created['createdEntityID'],[e['id'] for e in published['entities']])
        self.assertEqual(self.db.validator.check(published,self.db.published())['issues'],[])
        exports=Path(self.folder.name)/'exported'
        exports.mkdir()
        (exports/'creation-test.json').write_bytes(self.db.export('creation-test'))
        self.db.seed(exports)

    def test_new_endpoints_use_the_same_api_and_strict_payloads(self):
        api=EditingAPI(self.db,'test')
        response=api.post('/api/edit/drafts/'+self.draft_id+'/entities',self.new())
        self.assertIn('createdEntityID',response)
        self.assert_error('invalid_source_link',lambda:api.post('/api/edit/drafts/'+self.draft_id+'/evidence',{}))

    def test_schema_one_migration_keeps_publications_and_drafts(self):
        with self.db.connection(write=True) as db:
            db.execute('DROP TABLE work_reviews');db.execute('PRAGMA user_version=1')
        reopened=Database(self.path)
        self.assertEqual(reopened.detail(self.draft_id),self.detail)
        with reopened.connection() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],2)

    def test_legacy_top_level_order_does_not_change_immutable_publication(self):
        with self.db.connection(write=True) as db:
            snapshot=db.execute('SELECT id FROM snapshots WHERE release=?',('cross-subject-0.2.0',)).fetchone()[0]
            db.execute('DROP TRIGGER immutable_manifest_update')
            db.execute("UPDATE snapshot_records SET position=9999 WHERE snapshot_id=? AND collection='entities' AND position=0",(snapshot,))
            db.execute("UPDATE snapshot_records SET position=0 WHERE snapshot_id=? AND collection='entities' AND position=1",(snapshot,))
            db.execute("UPDATE snapshot_records SET position=1 WHERE snapshot_id=? AND collection='entities' AND position=9999",(snapshot,))
        reopened=Database(self.path)
        reopened.seed(ROOT/'data/releases')
        self.assertEqual(reopened.export('cross-subject-0.2.0'),(ROOT/'data/releases/cross-subject-0.2.0.json').read_bytes())


class ReadingWorkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=tempfile.TemporaryDirectory()
        cls.seed=Database(Path(cls.folder.name)/'seed.sqlite3')
        cls.seed.seed(ROOT/'data/catalog');cls.seed.seed(ROOT/'data/authoring')
        cls.seed.seed_work(ROOT/'data/work-reviews')
        cls.manifest=json.loads((ROOT/'data/coverage.json').read_text())
        cls.work=work_records(cls.seed)[0]
        cls.raw=cls.seed.published('curriculum-0.3.0')[0]
        cls.authored=cls.seed.published('reading-0.3.1')[0]

    @classmethod
    def tearDownClass(cls):cls.folder.cleanup()

    def setUp(self):
        self.folder_case=tempfile.TemporaryDirectory()
        self.path=Path(self.folder_case.name)/'work.sqlite3';self.seed.backup(self.path);self.db=Database(self.path)
    def tearDown(self):self.folder_case.cleanup()

    def payload(self):
        return {k:v for k,v in self.work.items() if k not in ('id','createdAt')} | {'expectedWorkID':self.work['id']}

    def test_six_subjects_goals_and_notes_cover_reading_without_mutating_raw(self):
        original=[e for e in self.authored['entities'] if e['kind']=='frameworkItem']
        self.assertEqual(original,self.raw['entities'])
        self.assertEqual(len([e for e in self.authored['entities'] if e['kind']=='subjectMatter']),6)
        self.assertEqual(len([e for e in self.authored['entities'] if e['kind']=='goal']),6)
        self.assertEqual(len(self.authored['annotations']),6)
        for goal in (e for e in self.authored['entities'] if e['kind']=='goal'):
            self.assertEqual(goal['education'][0]['grades'],[1,2])
            self.assertEqual(len(goal['targetIDs']),1)
            text=[e for e in self.authored['evidence'] if e['target']['id']==goal['id'] and e['field']=='text']
            self.assertEqual(len(text),1)
            self.assertIn(text[0]['citations'][0]['item']['id'],self.work['reviewedOriginalIDs'])
        self.assertEqual(self.db.export('reading-0.3.1'),(ROOT/'data/authoring/reading-0.3.1.json').read_bytes())

    def test_partial_progress_matches_offline_snapshot_and_can_be_reseeded(self):
        coverage=self.db.coverage(self.manifest)
        self.assertEqual(coverage,offline_coverage(self.manifest,ROOT/'data/work-reviews'))
        totals=coverage['totals']
        self.assertEqual(totals['reviewedOriginalItems'],12)
        self.assertEqual(totals['goalChunksComplete'],0)
        self.assertEqual(totals['goalChunksInProgress'],1)
        self.assertEqual(totals['goals'],6)
        self.assertEqual(totals['annotations'],6)
        chunk=next(c for c in coverage['chunks'] if c['id']==self.work['chunkID'])
        self.assertEqual(chunk['goals']['status'],'inProgress')
        self.assertEqual(chunk['original']['expected'],62)
        self.db.seed_work(ROOT/'data/work-reviews')
        self.assertEqual(len(work_records(self.db)),1)
        store=Store(ROOT/'data/catalog',self.db,coverage_path=ROOT/'data/coverage.json')
        self.assertEqual(store.get('/api/v1/coverage',{})[1],coverage)

    def test_work_rejects_scope_goal_annotation_errors_and_competing_update(self):
        for patch,code in [({'reviewedOriginalIDs':['unknown']},'invalid_work_scope'),({'goalIDs':['unknown']},'invalid_work_goal'),({'annotationIDs':['unknown']},'invalid_work_annotation'),({'release':'unknown'},'published_release_required'),({'expectedWorkID':None},'work_conflict')]:
            with self.assertRaises(EditError) as context:self.db.record_work(self.payload()|patch)
            self.assertEqual(context.exception.code,code)
            self.assertEqual(len(work_records(self.db)),1)
        saved=self.db.record_work(self.payload()|{'note':'同じ範囲を再確認'})
        self.assertNotEqual(saved['work']['id'],self.work['id'])
        with self.assertRaises(EditError) as context:self.db.record_work(self.payload())
        self.assertEqual(context.exception.code,'work_conflict')
        with self.db.connection(write=True) as db:
            with self.assertRaises(sqlite3.IntegrityError):db.execute('DELETE FROM work_reviews')


if __name__=='__main__':unittest.main()
