"""Creation and source linking using the same immutable draft snapshots as text edits."""
from copy import deepcopy
from editing_db import EditError, new_id, packed
from schema_v2_store import Index


def strings(value, maximum=40):
    if not isinstance(value,list) or len(value)>maximum or any(not isinstance(v,str) for v in value) or len(set(value))!=len(value):
        raise EditError(400,'invalid_selection')
    return value


def source_items(index, identifiers):
    items=[];seen=set()
    for identifier in strings(identifiers):
        item=index.collections['entities'].get(index.resolve(identifier))
        if not item or item['kind']!='frameworkItem' or item['provenance']['origin']!='original':
            raise EditError(400,'invalid_source_item')
        if item['id'] in seen:raise EditError(400,'invalid_selection')
        seen.add(item['id'])
        quotes=[e for e in index.evidence.get(item['id'],[]) if e['role']=='quotation' and e['field']=='text' and e['target']['revisionID']==item['revisionID']]
        if len(quotes)!=1:raise EditError(422,'ambiguous_source_item')
        citations=[dict(source=deepcopy(c['source']),locator=c['locator'],item=dict(id=item['id'],revisionID=item['revisionID'])) for c in quotes[0]['citations']]
        items.extend(citations)
    return items


def evidence(data, index, target, field, ids, reason):
    citations=source_items(index,ids)
    if not citations:return []
    entry=dict(id=new_id(),revisionID=new_id(),target=dict(id=target['id'],revisionID=target['revisionID']),field=field,role='supports',citations=citations,rationale=reason)
    data['evidence'].append(entry)
    return [entry['id']]


def advance(database, db, draft, data, reason, details):
    data['release']='draft-'+new_id()
    checked=database.validator.check(data,database._history(db))
    blocking=[i for i in checked['issues'] if i['code']!='staleRevision']
    if blocking:raise EditError(422,'validation_failed',issues=blocking)
    head=database._insert(db,data,'draft',checked['canonical'])
    db.execute('UPDATE drafts SET head_id=? WHERE id=? AND head_id=?',(head,draft['id'],draft['head_id']))
    db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?)',(new_id(),draft['id'],draft['head_id'],head,'local-user',reason,packed(details),database.now()))


def add_entity(database, identifier, payload):
    fields={'expectedHead','kind','label','text','conditions','educationFrom','targetIDs','sourceItemIDs','conditionItemIDs','annotations','reason'}
    if set(payload)-fields or not isinstance(payload.get('expectedHead'),str) or payload.get('kind') not in ('subjectMatter','goal') or not isinstance(payload.get('educationFrom'),str):
        raise EditError(400,'invalid_creation')
    for field in ('label','text','conditions'):
        value=payload.get(field,'' if field=='conditions' else None)
        if not isinstance(value,str) or len(value)>20000 or (field!='conditions' and not value.strip()):
            raise EditError(400,'invalid_creation')
    reason=database.reason(payload.get('reason'))
    annotations=strings(payload.get('annotations',[]),20)
    if any(not a.strip() or len(a)>20000 for a in annotations) or annotations and payload['kind']!='goal':
        raise EditError(400,'invalid_annotation')
    with database.connection(write=True) as db:
        draft=database._draft(db,identifier,payload['expectedHead'])
        data=database._dataset(db,draft['head_id']); index=Index(data)
        scope=index.collections['entities'].get(index.resolve(payload.get('educationFrom','')))
        if not scope or scope['kind']!='frameworkItem' or scope['provenance']['origin']!='original' or not scope['education']:
            raise EditError(400,'education_source_required')
        targets=strings(payload.get('targetIDs',[]))
        if payload['kind']=='subjectMatter' and targets:raise EditError(400,'invalid_target')
        targets=[index.resolve(i) for i in targets]
        if len(set(targets))!=len(targets) or any(index.collections['entities'].get(i,{}).get('kind')!='subjectMatter' or index.records[i]['lifecycle']!='active' for i in targets):
            raise EditError(400,'invalid_target')
        entity=dict(id=new_id(),revisionID=new_id(),kind=payload['kind'],label=payload['label'].strip(),text=payload['text'].strip(),conditions=payload.get('conditions','').strip(),education=deepcopy(scope['education']),provenance=dict(origin='editorial',rationale=reason),externalIDs={},targetIDs=targets,lifecycle='active',successorIDs=[])
        data['entities'].append(entity)
        changed=[entity['id']]
        changed+=evidence(data,index,entity,'education',[scope['id']],'原典の学年・教科・分野を選択し、この項目の適用範囲として設定。'+reason)
        changed+=evidence(data,index,entity,'text',payload.get('sourceItemIDs',[]),reason)
        conditions=strings(payload.get('conditionItemIDs',[]))
        if conditions and not entity['conditions']:raise EditError(400,'conditions_required')
        changed+=evidence(data,index,entity,'conditions',conditions,reason)
        for position,text in enumerate(annotations):
            note=dict(id=new_id(),revisionID=new_id(),goal=dict(id=entity['id'],revisionID=entity['revisionID']),text=text.strip(),position=position,evaluationMode='unspecified',provenance=dict(origin='editorial',rationale=reason))
            data['annotations'].append(note);changed.append(note['id'])
        # A reading section for additions keeps every new item reachable from the reader.
        alias='reading.authored'
        outline=next((o for o in data['readingOutlines'] if o['id']==data['aliases'].get(alias)),None)
        if not outline:
            outline=dict(id=new_id(),revisionID=new_id(),label='整理した学ぶ対象と目標',sections=[dict(id=new_id(),revisionID=new_id(),label='追加した学び',entityIDs=[])])
            data['readingOutlines'].append(outline);data['aliases'][alias]=outline['id']
        section=outline['sections'][0]
        section['entityIDs'].append(entity['id']);section['revisionID']=new_id();outline['revisionID']=new_id()
        advance(database,db,draft,data,reason,dict(entityID=entity['id'],changedIDs=changed,operation='create',confirmedAnnotations=[],confirmedEvidence=[]))
    result=database.detail(identifier)
    result['createdEntityID']=entity['id']
    return result


def add_evidence(database, identifier, payload):
    if set(payload)!={'expectedHead','entityID','field','sourceItemIDs','reason'} or not isinstance(payload['expectedHead'],str) or not isinstance(payload['entityID'],str) or payload['field'] not in ('text','conditions'):
        raise EditError(400,'invalid_source_link')
    reason=database.reason(payload['reason'])
    with database.connection(write=True) as db:
        draft=database._draft(db,identifier,payload['expectedHead'])
        data=database._dataset(db,draft['head_id']);index=Index(data)
        entity=index.collections['entities'].get(index.resolve(payload['entityID']))
        if not entity or entity['kind']=='frameworkItem' or entity['provenance']['origin']=='original' or entity['lifecycle']!='active':
            raise EditError(403,'original_or_retired_read_only')
        if payload['field']=='conditions' and not entity['conditions']:raise EditError(400,'conditions_required')
        ids=evidence(data,index,entity,payload['field'],payload['sourceItemIDs'],reason)
        if not ids:raise EditError(400,'source_required')
        advance(database,db,draft,data,reason,dict(entityID=entity['id'],changedIDs=ids,operation='sourceLink',confirmedAnnotations=[],confirmedEvidence=[]))
    return database.detail(identifier)
