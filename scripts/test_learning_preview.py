import json
from pathlib import Path
from collections import Counter
from uuid import UUID
import threading
import unittest
from urllib.request import urlopen
from http.server import ThreadingHTTPServer
from serve import Store, handler_for, ROOT


class LearningPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preview=json.loads((ROOT/'data/learning-preview/lessons.json').read_text())
        cls.datasets={json.loads(p.read_text())['release']:json.loads(p.read_text()) for folder in ['data/authoring','data/releases'] for p in (ROOT/folder).glob('*.json')}

    def test_every_goal_and_source_resolves_to_the_pinned_revision_and_scope(self):
        self.assertEqual(len(self.preview['lessons']),4)
        self.assertEqual({l['subjectLabel'] for l in self.preview['lessons']},{'国語','算数','理科'})
        ids=[]
        for lesson in self.preview['lessons']:
            ids.append(lesson['id']);UUID(lesson['id'])
            self.assertEqual(lesson['provenance']['origin'],'editorial')
            for ref in lesson['goals']+lesson['sourceItems']:
                dataset=self.datasets[ref['release']]
                entity=next(e for e in dataset['entities'] if e['id']==ref['id'])
                self.assertEqual(entity['revisionID'],ref['revisionID'])
                if ref in lesson['goals']:
                    self.assertEqual(entity['kind'],'goal')
                    self.assertEqual(entity['education'][0],lesson['education'])
                    self.assertEqual(entity['label'],ref['label'])
                else:
                    self.assertEqual(entity['provenance']['origin'],'original')
                    self.assertEqual(entity['text'],ref['text'])
        self.assertEqual(len(ids),len(set(ids)))

    def test_answers_match_materials_and_free_responses_keep_observation_criteria(self):
        ids=[];lessons={l['slug']:l for l in self.preview['lessons']}
        count=Counter(row[0] for row in lessons['sorting-data']['material']['rows'])
        math_questions=lessons['sorting-data']['questions']
        self.assertEqual(math_questions[0]['answer'],count['校庭'])
        self.assertEqual(math_questions[1]['answer'],count['室内'])
        science=lessons['pendulum'];self.assertEqual(science['questions'][1]['answer'],11.0/10)
        for lesson in self.preview['lessons']:
            for q in lesson['questions']:
                ids.append(q['id']);UUID(q['id'])
                self.assertTrue(q['explanation'])
                if q['kind']=='choice':self.assertIn(q['answer'],[o['value'] for o in q['options']])
                elif q['kind']=='order':self.assertEqual(sorted(q['answer']),list(range(1,len(q['items'])+1)))
                elif q['kind']=='text':self.assertTrue(q['criteria'])
        self.assertEqual(len(ids),14);self.assertEqual(len(set(ids)),14)

    def test_preview_and_assets_are_served_through_the_local_read_only_boundary(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(Store(ROOT/'data/releases')))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            base=f'http://127.0.0.1:{server.server_port}'
            with urlopen(base+'/api/preview/lessons') as response:
                self.assertEqual(json.loads(response.read()),self.preview)
                self.assertIn("script-src 'self'",response.headers['Content-Security-Policy'])
            for path,content_type in [('/learn','text/html'),('/learn.js','text/javascript'),('/learn.css','text/css')]:
                with urlopen(base+path) as response:
                    self.assertEqual(response.status,200)
                    self.assertTrue(response.headers['Content-Type'].startswith(content_type))
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
