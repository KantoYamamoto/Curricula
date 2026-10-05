"""Immutable progress reviews pinned to a published release, with optimistic concurrency."""
from copy import deepcopy
import json
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime
from editing_db import ROOT, EditError, new_id, packed
from authoring import strings
from schema_v2_store import Index

FIELDS={'chunkID','release','label','note','next','reviewedOriginalIDs','goalIDs','annotationIDs'}


def work_records(database):
    with database.connection() as db:
        return [json.loads(r['payload']) for r in db.execute('SELECT payload FROM work_reviews ORDER BY rowid')]


def latest(db,chunk):
    row=db.execute('SELECT payload FROM work_reviews WHERE chunk_id=? ORDER BY created_at DESC,id DESC LIMIT 1',(chunk,)).fetchone()
    return json.loads(row['payload']) if row else None


def validate(database,db,payload):
    if set(payload)!=FIELDS:raise EditError(400,'invalid_work_review')
    if not isinstance(payload['release'],str) or not isinstance(payload['chunkID'],str):raise EditError(400,'invalid_work_review')
    for key in ('label','note','next'):database.reason(payload[key])
    manifest=json.loads((ROOT/'data/coverage.json').read_text())
    chunk=next((c for c in manifest['chunks'] if c['id']==payload['chunkID']),None)
    if not chunk:raise EditError(400,'unknown_work_chunk')
    row=db.execute("SELECT id FROM snapshots WHERE release=? AND kind IN ('seed','published')",(payload['release'],)).fetchone()
    if not row:raise EditError(400,'published_release_required')
    data=database._dataset(db,row['id']);index=Index(data)
    reviewed=strings(payload['reviewedOriginalIDs'],1000)
    if not reviewed or not set(reviewed)<=set(chunk['entityIDs']):raise EditError(400,'invalid_work_scope')
    # All original records of the work unit must still exist in this release.
    for i in chunk['entityIDs']:
        e=index.collections['entities'].get(i)
        if not e or e['kind']!='frameworkItem' or e['provenance']['origin']!='original':raise EditError(400,'invalid_work_scope')
    goals=strings(payload['goalIDs'],1000);notes=strings(payload['annotationIDs'],1000)
    for i in goals:
        e=index.collections['entities'].get(i)
        if not e or e['kind']!='goal' or e['lifecycle']!='active':raise EditError(400,'invalid_work_goal')
        grounded=any(ev['target']==dict(id=i,revisionID=e['revisionID']) and ev['field']=='text' and any(c.get('item',{}).get('id') in reviewed for c in ev['citations']) for ev in index.evidence.get(i,[]))
        if not grounded:raise EditError(400,'work_goal_without_source')
    for i in notes:
        a=index.collections['annotations'].get(i)
        if not a or a['goal']['id'] not in goals or a['goal']['revisionID']!=index.records[a['goal']['id']]['revisionID']:
            raise EditError(400,'invalid_work_annotation')
    return row['id']


def insert(database,db,record):
    if set(record)!=(FIELDS|{'id','createdAt'}):raise EditError(400,'invalid_work_review')
    snapshot=validate(database,db,{k:record[k] for k in FIELDS})
    db.execute('INSERT INTO work_reviews VALUES(?,?,?,?,?)',(record['id'],record['chunkID'],snapshot,packed(record),record['createdAt']))


def record_work(database,payload):
    if set(payload)!=(FIELDS|{'expectedWorkID'}):raise EditError(400,'invalid_work_review')
    with database.connection(write=True) as db:
        if not isinstance(payload['chunkID'],str):raise EditError(400,'invalid_work_review')
        current=latest(db,payload['chunkID'])
        if payload['expectedWorkID']!=(current['id'] if current else None):raise EditError(409,'work_conflict')
        record={k:payload[k] for k in FIELDS}
        record.update(id=new_id(),createdAt=database.now())
        insert(database,db,record)
    return {'work':record}


def seed_work(database,directory):
    for path in sorted(Path(directory).glob('*.json')):
        record=json.loads(path.read_text())
        with database.connection(write=True) as db:
            row=db.execute('SELECT payload FROM work_reviews WHERE id=?',(record.get('id'),)).fetchone()
            if row:
                if json.loads(row['payload'])!=record:raise EditError(409,'work_seed_changed')
            else:insert(database,db,record)


def apply_work(manifest, records):
    result=deepcopy(manifest)
    ordered=sorted(records,key=lambda r:(r['createdAt'],r['id']))
    current={r['chunkID']:r for r in ordered}
    for chunk in result['chunks']:
        work=current.get(chunk['id'])
        if not work:continue
        reviewed=work['reviewedOriginalIDs']
        chunk['goals']=dict(status='complete' if set(reviewed)==set(chunk['entityIDs']) else 'inProgress',reviewedOriginalIDs=reviewed,goalIDs=work['goalIDs'],annotationIDs=work['annotationIDs'],release=work['release'],reviewID=work['id'],label=work['label'],note=work['note'],updatedOn=work['createdAt'])
    if ordered:
        work=ordered[-1]
        result['next']=work['next']
        result['updatedOn']=datetime.fromisoformat(work['createdAt']).astimezone(ZoneInfo('Asia/Tokyo')).date().isoformat()
    result['totals']['goalChunksComplete']=sum(c['goals']['status']=='complete' for c in result['chunks'])
    result['totals']['goalChunksInProgress']=sum(c['goals']['status']=='inProgress' for c in result['chunks'])
    result['totals']['reviewedOriginalItems']=sum(len(c['goals']['reviewedOriginalIDs']) for c in result['chunks'])
    result['totals']['goals']=sum(len(c['goals']['goalIDs']) for c in result['chunks'])
    result['totals']['annotations']=sum(len(c['goals']['annotationIDs']) for c in result['chunks'])
    return result


def coverage(database,manifest):
    return apply_work(manifest,work_records(database))


def offline_coverage(manifest,directory):
    return apply_work(manifest,[json.loads(p.read_text()) for p in sorted(Path(directory).glob('*.json'))])
