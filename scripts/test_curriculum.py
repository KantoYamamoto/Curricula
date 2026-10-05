import collections
import json
from pathlib import Path
import tempfile
import unittest
from build_curriculum import RELEASE, ROOT, VERSIONS, rows
from editing_db import Database
from schema_v2_store import Index
from serve import Store


class CurriculumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT/'data/catalog'/f'{RELEASE}.json').read_text())
        cls.progress = json.loads((ROOT/'data/coverage.json').read_text())
        cls.by_code = {e['externalIDs']['mext:course-of-study']:e for e in cls.data['entities'] if e['externalIDs']}
        cls.index = Index(cls.data)

    def test_every_official_row_is_preserved_verbatim_once(self):
        codes = set()
        for version,stage,*_ in VERSIONS:
            original = rows(version)
            for subject,no,text,code in original:
                self.assertNotIn(code,codes)
                codes.add(code)
                e = self.by_code[code]
                self.assertEqual(e['text'],text)
                self.assertEqual(e['education'][0]['stage'],stage)
                self.assertIn('No.'+no+' /',e['sourceLocator'])
                self.assertEqual(e['provenance']['origin'],'original')
        self.assertEqual(set(self.by_code),codes)
        self.assertEqual(len(codes),5937)

    def test_preambles_supplement_csv_without_invented_codes(self):
        uncoded = [e for e in self.data['entities'] if not e['externalIDs']]
        self.assertEqual(len(uncoded),2)
        for e in uncoded:
            self.assertEqual(e['label'],'前文')
            self.assertTrue(e['text'].startswith('　教育は，'))
            self.assertTrue(e['text'].endswith('学習指導要領を定める。'))
            self.assertIn('PDF ',e['sourceLocator'])
            self.assertNotIn('\nひら\n',e['text'])
            self.assertNotIn('幼稚園\n教育要領',e['text'])

    def test_chapters_are_siblings_and_subjects_attach_to_common_chapter(self):
        for code in ['8200000000000000','82n0000000000000','82K0000000000000','82L00C0000000000','82M00L0000000000','82N0000000000000','8300000000000000','83n0000000000000','83K0000000000000','83M0000000000000','83N0000000000000']:
            self.assertNotIn('parentID',self.by_code[code])
        self.assertEqual(self.by_code['8210000000000000']['parentID'],self.by_code['82n0000000000000']['id'])
        self.assertEqual(self.by_code['8310000000000000']['parentID'],self.by_code['83n0000000000000']['id'])

    def test_nonprefix_parents_and_grade_bands(self):
        morality=self.by_code['82K04D0213000000']
        self.assertEqual(morality['parentID'],self.by_code['82K0400210000000']['id'])
        self.assertEqual(morality['education'][0]['grades'],[5,6])
        self.assertEqual(self.by_code['82600L0000000000']['education'][0]['grades'],[3,4,5,6])
        self.assertEqual(self.by_code['82102A0000000000']['education'][0]['grades'],[1,2])
        self.assertEqual(self.by_code['8210000000000000']['education'][0]['gradeStatus'],'notSpecified')
        self.assertEqual(self.by_code['83802B0000000000']['education'][0]['grades'],[2,3])

    def test_kanji_annex_has_all_six_grade_lists(self):
        for grade,count in enumerate([80,160,200,202,193,191],1):
            items=[e for c,e in self.by_code.items() if c.startswith('82100') and e['education'][0]['grades']==[grade] and len(e['text'])==1]
            self.assertEqual(len(items),count)

    def test_work_units_cover_once_with_source_order_and_truthful_phase(self):
        all_ids=[]
        outlines={o['id']:o for o in self.data['readingOutlines']}
        for chunk in self.progress['chunks']:
            section=next(s for s in outlines[chunk['outlineID']]['sections'] if s['id']==chunk['sectionID'])
            self.assertEqual(section['entityIDs'],chunk['entityIDs'])
            self.assertEqual(chunk['original']['expected'],len(section['entityIDs']))
            self.assertEqual(chunk['original']['imported'],len(section['entityIDs']))
            self.assertEqual(chunk['original']['status'],'complete')
            self.assertEqual(chunk['goals']['status'],'pending')
            self.assertEqual(chunk['goals']['goalIDs'],[])
            all_ids.extend(section['entityIDs'])
            numbers=[int(self.index.records[i]['sourceLocator'].split('No.')[1].split(' /')[0]) for i in section['entityIDs'] if 'No.' in self.index.records[i]['sourceLocator']]
            self.assertEqual(numbers,sorted(numbers))
        self.assertEqual(len(all_ids),5939)
        self.assertEqual(collections.Counter(all_ids),collections.Counter(e['id'] for e in self.data['entities']))
        self.assertEqual(len(self.progress['chunks']),138)
        self.assertEqual(self.progress['totals']['goalChunksComplete'],0)

    def test_sources_and_sample_identities_remain_traceable(self):
        old=json.loads((ROOT/'data/releases/cross-subject-0.2.0.json').read_text())
        for e in old['entities']:
            code=e['externalIDs'].get('mext:course-of-study')
            if code in self.by_code:self.assertEqual(self.by_code[code]['id'],e['id'])
        for e in self.data['entities']:
            quotes=[q for q in self.index.evidence[e['id']] if q['role']=='quotation']
            self.assertEqual(len(quotes),1)
            self.assertEqual(quotes[0]['target']['revisionID'],e['revisionID'])
            source=self.index.records[quotes[0]['citations'][0]['source']['id']]
            self.assertIn('mext.go.jp',source['url'])
            self.assertEqual(len(source['sha256']),64)

    def test_section_api_is_ordered_batched_and_read_only(self):
        section=self.data['readingOutlines'][0]['sections'][0]
        status,body=self.index.get('reading-sections',section['id'],{})
        self.assertEqual(status,200)
        self.assertEqual([e['data']['id'] for e in body['entities']],section['entityIDs'])
        self.assertTrue(all(e['evidence'] for e in body['entities']))
        self.assertEqual(self.index.get('reading-sections',section['id'],{'unknown':['x']})[0],400)
        self.assertEqual(self.index.get('reading-sections','missing',{})[0],404)
        store=Store(ROOT/'data/releases',catalog_directory=ROOT/'data/catalog',coverage_path=ROOT/'data/coverage.json')
        self.assertEqual(store.get('/api/v1/coverage',{})[1],self.progress)
        self.assertEqual(store.get('/api/v1/releases/'+RELEASE+'/entities/82102A0000000000',{})[0],200)

    def test_full_catalog_roundtrips_sqlite_and_coexists_with_old_data(self):
        with tempfile.TemporaryDirectory() as directory:
            db=Database(Path(directory)/'catalog.sqlite3')
            db.seed(ROOT/'data/releases')
            db.seed(ROOT/'data/catalog')
            self.assertEqual(db.export(RELEASE),(ROOT/'data/catalog'/f'{RELEASE}.json').read_bytes())
            db.seed(ROOT/'data/catalog')
            self.assertEqual(len(db.published(RELEASE)),1)
            self.assertEqual(len(db.published_manifest()),6)
            store=Store(ROOT/'data/releases',db,catalog_directory=ROOT/'data/catalog',coverage_path=ROOT/'data/coverage.json')
            # The reader never loads all graphs for a request to a single entity.
            db.published=lambda *args: (_ for _ in ()).throw(AssertionError('unexpected graph reload'))
            self.assertEqual(store.get('/api/v1/releases/'+RELEASE+'/entities/82102A0000000000',{})[0],200)


if __name__=='__main__':unittest.main()
