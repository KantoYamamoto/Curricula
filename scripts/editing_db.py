"""Local authoring storage. Immutable revisions + manifests; Swift validates the exchange model."""
from contextlib import closing, contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import uuid
from schema_v2_store import COLLECTIONS, Index

ROOT = Path(__file__).resolve().parents[1]


def new_id():
    return str(uuid.uuid4())


def packed(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


class EditError(Exception):
    def __init__(self, status, code, **details):
        self.status, self.code, self.details = status, code, details
        super().__init__(code)


class SwiftValidator:
    def __init__(self, executable=None):
        self.executable = Path(executable or ROOT / '.build/debug/curricula').resolve()
        if not self.executable.is_file():
            raise ValueError('Run swift build before starting the editor.')

    def check(self, dataset, history):
        try:
            result = subprocess.run([str(self.executable), 'check-json'],
                                    input=packed(dict(dataset=dataset, history=history)),
                                    text=True, capture_output=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise EditError(503, 'validator_unavailable') from error
        if result.returncode:
            raise EditError(422, 'invalid_exchange_data', message=result.stderr[:2000])
        output = json.loads(result.stdout)
        normalized = deepcopy(dataset)
        for collection in COLLECTIONS:
            normalized[collection].sort(key=lambda record: record['id'])
        if json.loads(output['canonical']) != normalized:
            # The exchange decoder must never silently discard unknown data.
            raise EditError(422, 'lossy_exchange_conversion')
        return output


SCHEMA = """
CREATE TABLE IF NOT EXISTS identities (id TEXT PRIMARY KEY, collection TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS revisions (
    revision_id TEXT PRIMARY KEY, record_id TEXT NOT NULL REFERENCES identities(id),
    payload TEXT NOT NULL, UNIQUE(record_id, revision_id));
CREATE TABLE IF NOT EXISTS snapshots (
    id TEXT PRIMARY KEY, release TEXT NOT NULL UNIQUE, kind TEXT NOT NULL CHECK(kind IN ('seed','draft','published')),
    header TEXT NOT NULL, sha256 TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS snapshot_records (
    snapshot_id TEXT NOT NULL REFERENCES snapshots(id), collection TEXT NOT NULL, position INTEGER NOT NULL,
    record_id TEXT NOT NULL, revision_id TEXT NOT NULL,
    PRIMARY KEY(snapshot_id, collection, position), UNIQUE(snapshot_id, record_id),
    FOREIGN KEY(record_id,revision_id) REFERENCES revisions(record_id,revision_id));
CREATE TABLE IF NOT EXISTS aliases (
    snapshot_id TEXT NOT NULL REFERENCES snapshots(id), alias TEXT NOT NULL, record_id TEXT NOT NULL REFERENCES identities(id),
    PRIMARY KEY(snapshot_id,alias));
CREATE TABLE IF NOT EXISTS education_scopes (
    revision_id TEXT NOT NULL REFERENCES revisions(revision_id), position INTEGER NOT NULL,
    stage TEXT NOT NULL, grade_status TEXT NOT NULL, subject_id TEXT NOT NULL REFERENCES identities(id),
    course_id TEXT REFERENCES identities(id), PRIMARY KEY(revision_id,position));
CREATE TABLE IF NOT EXISTS scope_grades (
    revision_id TEXT NOT NULL, position INTEGER NOT NULL, grade INTEGER NOT NULL,
    PRIMARY KEY(revision_id,position,grade),
    FOREIGN KEY(revision_id,position) REFERENCES education_scopes(revision_id,position));
CREATE INDEX IF NOT EXISTS education_search ON education_scopes(subject_id,stage,grade_status);
CREATE TABLE IF NOT EXISTS drafts (
    id TEXT PRIMARY KEY, title TEXT NOT NULL, base_id TEXT NOT NULL REFERENCES snapshots(id),
    head_id TEXT NOT NULL REFERENCES snapshots(id), published_id TEXT REFERENCES snapshots(id));
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY, draft_id TEXT NOT NULL REFERENCES drafts(id),
    before_id TEXT NOT NULL REFERENCES snapshots(id), after_id TEXT NOT NULL REFERENCES snapshots(id),
    actor TEXT NOT NULL, reason TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY, draft_id TEXT NOT NULL REFERENCES drafts(id), head_id TEXT NOT NULL REFERENCES snapshots(id),
    actor TEXT NOT NULL, note TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS immutable_revision_update BEFORE UPDATE ON revisions BEGIN SELECT RAISE(ABORT,'immutable revision'); END;
CREATE TRIGGER IF NOT EXISTS immutable_revision_delete BEFORE DELETE ON revisions BEGIN SELECT RAISE(ABORT,'immutable revision'); END;
CREATE TRIGGER IF NOT EXISTS immutable_snapshot_update BEFORE UPDATE ON snapshots BEGIN SELECT RAISE(ABORT,'immutable snapshot'); END;
CREATE TRIGGER IF NOT EXISTS immutable_snapshot_delete BEFORE DELETE ON snapshots BEGIN SELECT RAISE(ABORT,'immutable snapshot'); END;
CREATE TRIGGER IF NOT EXISTS immutable_manifest_update BEFORE UPDATE ON snapshot_records BEGIN SELECT RAISE(ABORT,'immutable manifest'); END;
CREATE TRIGGER IF NOT EXISTS immutable_manifest_delete BEFORE DELETE ON snapshot_records BEGIN SELECT RAISE(ABORT,'immutable manifest'); END;
CREATE TRIGGER IF NOT EXISTS immutable_alias_update BEFORE UPDATE ON aliases BEGIN SELECT RAISE(ABORT,'immutable alias'); END;
CREATE TRIGGER IF NOT EXISTS immutable_alias_delete BEFORE DELETE ON aliases BEGIN SELECT RAISE(ABORT,'immutable alias'); END;
CREATE TRIGGER IF NOT EXISTS immutable_identity_update BEFORE UPDATE ON identities BEGIN SELECT RAISE(ABORT,'immutable identity'); END;
CREATE TRIGGER IF NOT EXISTS immutable_identity_delete BEFORE DELETE ON identities BEGIN SELECT RAISE(ABORT,'immutable identity'); END;
CREATE TRIGGER IF NOT EXISTS immutable_event_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'immutable event'); END;
CREATE TRIGGER IF NOT EXISTS immutable_event_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'immutable event'); END;
CREATE TRIGGER IF NOT EXISTS immutable_review_update BEFORE UPDATE ON reviews BEGIN SELECT RAISE(ABORT,'immutable review'); END;
CREATE TRIGGER IF NOT EXISTS immutable_review_delete BEFORE DELETE ON reviews BEGIN SELECT RAISE(ABORT,'immutable review'); END;
PRAGMA user_version=1;
"""


class Database:
    def __init__(self, path, validator=None):
        self.path = Path(path).resolve()
        self.validator = validator or SwiftValidator()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1):
                raise ValueError('Unsupported editing database version')
            db.executescript(SCHEMA)

    @contextmanager
    def connection(self, write=False):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _dataset(self, db, snapshot_id):
        row = db.execute('SELECT header FROM snapshots WHERE id=?', (snapshot_id,)).fetchone()
        if row is None:
            raise EditError(404, 'snapshot_not_found')
        data = json.loads(row['header'])
        data['aliases'] = {r['alias']: r['record_id'] for r in db.execute('SELECT * FROM aliases WHERE snapshot_id=? ORDER BY alias', (snapshot_id,))}
        for key in COLLECTIONS:
            data[key] = [json.loads(r['payload']) for r in db.execute(
                'SELECT r.payload FROM snapshot_records s JOIN revisions r USING(record_id,revision_id) WHERE s.snapshot_id=? AND s.collection=? ORDER BY s.position',
                (snapshot_id, key))]
        return data

    def _history(self, db):
        return [self._dataset(db, r['id']) for r in db.execute("SELECT id FROM snapshots WHERE kind IN ('seed','published') ORDER BY release")]

    def _insert(self, db, dataset, kind, canonical):
        Index(dataset)
        snapshot_id = new_id()
        header = {k: v for k, v in dataset.items() if k not in COLLECTIONS and k != 'aliases'}
        db.execute('INSERT INTO snapshots VALUES(?,?,?,?,?,?)', (snapshot_id, dataset['release'], kind, packed(header), hashlib.sha256(canonical.encode()).hexdigest(), self.now()))
        records = [(key, n, r) for key in COLLECTIONS for n, r in enumerate(dataset[key])]
        records += [('sections', n, r) for n, r in enumerate(s for o in dataset['readingOutlines'] for s in o['sections'])]
        # All identities first, so education indexes can refer to taxons inserted later.
        for key, _, r in records:
            row = db.execute('SELECT collection FROM identities WHERE id=?', (r['id'],)).fetchone()
            if row and row['collection'] != key:
                raise EditError(422, 'identity_kind_changed')
            db.execute('INSERT OR IGNORE INTO identities VALUES(?,?)', (r['id'], key))
        for key, pos, r in records:
            payload = packed(r)
            row = db.execute('SELECT record_id,payload FROM revisions WHERE revision_id=?', (r['revisionID'],)).fetchone()
            if row and (row['record_id'] != r['id'] or row['payload'] != payload):
                raise EditError(422, 'mutated_revision')
            if not row:
                db.execute('INSERT INTO revisions VALUES(?,?,?)', (r['revisionID'], r['id'], payload))
                for n, scope in enumerate(r.get('education', [])):
                    db.execute('INSERT INTO education_scopes VALUES(?,?,?,?,?,?)', (r['revisionID'], n, scope['stage'], scope['gradeStatus'], scope['subjectID'], scope.get('courseID')))
                    for grade in scope['grades']:
                        db.execute('INSERT INTO scope_grades VALUES(?,?,?)', (r['revisionID'], n, grade))
            db.execute('INSERT INTO snapshot_records VALUES(?,?,?,?,?)', (snapshot_id, key, pos, r['id'], r['revisionID']))
        db.executemany('INSERT INTO aliases VALUES(?,?,?)', [(snapshot_id, alias, identifier) for alias, identifier in dataset['aliases'].items()])
        return snapshot_id

    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat()

    def seed(self, directory):
        inputs = [(path, json.loads(path.read_text())) for path in sorted(Path(directory).glob('*.json'))]
        inputs = [(p, d) for p, d in inputs if d['schemaVersion'] == '0.2.0']
        with self.connection(write=True) as db:
            history = self._history(db) + [d for _, d in inputs]
            for path, data in inputs:
                checked = self.validator.check(data, history)
                if checked['issues'] or checked['canonical'].encode() != path.read_bytes():
                    raise EditError(422, 'seed_roundtrip_failed', release=data['release'], issues=checked['issues'])
                row = db.execute('SELECT id FROM snapshots WHERE release=?', (data['release'],)).fetchone()
                if row:
                    if self._dataset(db, row['id']) != data:
                        raise EditError(409, 'seed_changed', release=data['release'])
                else:
                    self._insert(db, data, 'seed', checked['canonical'])

    def published(self):
        with self.connection() as db:
            return self._history(db)

    def export(self, release):
        with self.connection() as db:
            row = db.execute("SELECT id,sha256 FROM snapshots WHERE release=? AND kind IN ('seed','published')", (release,)).fetchone()
            if not row:
                raise EditError(404, 'release_not_found')
            checked = self.validator.check(self._dataset(db, row['id']), self._history(db))
            if checked['issues'] or hashlib.sha256(checked['canonical'].encode()).hexdigest() != row['sha256']:
                raise EditError(422, 'snapshot_integrity_failed')
            return checked['canonical'].encode()

    def list_drafts(self):
        with self.connection() as db:
            return [dict(r) for r in db.execute('SELECT d.*,s.release AS base_release FROM drafts d JOIN snapshots s ON s.id=d.base_id ORDER BY d.rowid DESC')]

    def create(self, base_release, title):
        if not isinstance(title, str) or not title.strip() or len(title) > 200:
            raise EditError(400, 'title_required')
        with self.connection(write=True) as db:
            base = db.execute("SELECT id FROM snapshots WHERE release=? AND kind IN ('seed','published')", (base_release,)).fetchone()
            if not base:
                raise EditError(404, 'release_not_found')
            identifier = new_id()
            db.execute('INSERT INTO drafts VALUES(?,?,?,?,NULL)', (identifier, title.strip(), base['id'], base['id']))
        return self.detail(identifier)

    def _draft(self, db, identifier, expected=None):
        row = db.execute('SELECT * FROM drafts WHERE id=?', (identifier,)).fetchone()
        if not row:
            raise EditError(404, 'draft_not_found')
        if expected is not None:
            if row['published_id']:
                raise EditError(409, 'draft_already_published')
            if row['head_id'] != expected:
                raise EditError(409, 'edit_conflict', currentHead=row['head_id'])
        return row

    def detail(self, identifier):
        with self.connection() as db:
            draft = self._draft(db, identifier)
            data = self._dataset(db, draft['head_id'])
            base = self._dataset(db, draft['base_id'])
            checked = self.validator.check(data, self._history(db))
            review = db.execute('SELECT * FROM reviews WHERE draft_id=? AND head_id=? ORDER BY rowid DESC LIMIT 1', (identifier, draft['head_id'])).fetchone()
            published = db.execute('SELECT release FROM snapshots WHERE id=?', (draft['published_id'],)).fetchone()
            events = [dict(e) for e in db.execute('SELECT * FROM events WHERE draft_id=? ORDER BY rowid', (identifier,))]
            for e in events:
                e['details'] = json.loads(e['details'])
            return dict(draft={**dict(draft), 'published_release': published['release'] if published else None}, dataset=data, base=base, issues=checked['issues'], review=dict(review) if review else None, events=events)

    @staticmethod
    def reason(value):
        if not isinstance(value, str) or not value.strip() or len(value) > 4000:
            raise EditError(400, 'reason_required')
        return value.strip()

    def save(self, identifier, payload):
        allowed = {'expectedHead', 'entityID', 'entity', 'annotations', 'newAnnotation', 'confirmAnnotationIDs', 'confirmEvidenceIDs', 'reason'}
        if set(payload) - allowed or not isinstance(payload.get('expectedHead'), str) or not isinstance(payload.get('entityID'), str):
            raise EditError(400, 'invalid_edit')
        reason = self.reason(payload.get('reason'))
        with self.connection(write=True) as db:
            draft = self._draft(db, identifier, payload['expectedHead'])
            data = self._dataset(db, draft['head_id'])
            index = Index(data)
            entity = index.collections['entities'].get(index.resolve(payload.get('entityID')))
            if not entity:
                raise EditError(404, 'entity_not_found')
            if entity['kind'] == 'frameworkItem' or entity['provenance']['origin'] == 'original' or entity['lifecycle'] != 'active':
                raise EditError(403, 'original_or_retired_read_only')
            patch = payload.get('entity', {})
            if not isinstance(patch, dict) or set(patch) - {'label', 'text', 'conditions'} or any(not isinstance(v, str) or len(v) > 20000 for v in patch.values()):
                raise EditError(400, 'invalid_edit')
            notes = {a['id']: a for a in data['annotations'] if a['goal']['id'] == entity['id']}
            note_edits = payload.get('annotations', {})
            if not isinstance(note_edits, dict) or set(note_edits) - set(notes) or any(not isinstance(v, str) or not v.strip() or len(v) > 20000 for v in note_edits.values()):
                raise EditError(400, 'invalid_annotation')
            confirms = payload.get('confirmAnnotationIDs', [])
            evidence = {e['id']: e for e in data['evidence'] if e['target']['id'] in {entity['id'], *notes}}
            evidence_confirms = payload.get('confirmEvidenceIDs', [])
            if not isinstance(confirms, list) or any(not isinstance(i, str) or i not in notes for i in confirms) or not isinstance(evidence_confirms, list) or any(not isinstance(i, str) or i not in evidence for i in evidence_confirms):
                raise EditError(400, 'invalid_confirmation')
            changed_ids = []
            if any(entity.get(k) != v for k, v in patch.items()):
                entity.update(patch)
                entity['revisionID'] = new_id()
                changed_ids.append(entity['id'])
            for a in notes.values():
                new_text = note_edits.get(a['id'], a['text'])
                changed_text = new_text != a['text']
                changed_pin = a['id'] in confirms and a['goal']['revisionID'] != entity['revisionID']
                if changed_text or changed_pin:
                    a['text'] = new_text
                    a['revisionID'] = new_id()
                    # Editing the annotation explicitly also chooses its current goal.
                    a['goal'] = dict(id=entity['id'], revisionID=entity['revisionID'])
                    changed_ids.append(a['id'])
            new_note = payload.get('newAnnotation', '')
            if not isinstance(new_note, str) or len(new_note) > 20000:
                raise EditError(400, 'invalid_annotation')
            if new_note.strip():
                if entity['kind'] != 'goal':
                    raise EditError(400, 'invalid_annotation_target')
                a = dict(id=new_id(), revisionID=new_id(), goal=dict(id=entity['id'], revisionID=entity['revisionID']),
                         text=new_note.strip(), position=max([a['position'] for a in notes.values()], default=-1) + 1,
                         evaluationMode='unspecified', provenance=dict(origin='editorial', rationale=reason))
                data['annotations'].append(a)
                changed_ids.append(a['id'])
            current = Index(data)
            for evidence_id in evidence_confirms:
                e = evidence[evidence_id]
                target = current.records[e['target']['id']]
                if e['target']['revisionID'] != target['revisionID']:
                    e['target']['revisionID'] = target['revisionID']
                    e['revisionID'] = new_id()
                    changed_ids.append(e['id'])
            if not changed_ids:
                raise EditError(400, 'no_changes')
            data['release'] = 'draft-' + new_id()
            checked = self.validator.check(data, self._history(db))
            # Pending pins can be saved. Other exchange failures are actionable before saving.
            blocking = [i for i in checked['issues'] if i['code'] != 'staleRevision']
            if blocking:
                raise EditError(422, 'validation_failed', issues=blocking)
            next_id = self._insert(db, data, 'draft', checked['canonical'])
            db.execute('UPDATE drafts SET head_id=? WHERE id=? AND head_id=?', (next_id, identifier, draft['head_id']))
            details = dict(entityID=entity['id'], changedIDs=changed_ids,
                           confirmedAnnotations=confirms, confirmedEvidence=evidence_confirms)
            db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?)',
                       (new_id(), identifier, draft['head_id'], next_id, 'local-user', reason, packed(details), self.now()))
        return self.detail(identifier)

    def review(self, identifier, expected, note):
        note = self.reason(note)
        with self.connection(write=True) as db:
            draft = self._draft(db, identifier, expected)
            checked = self.validator.check(self._dataset(db, expected), self._history(db))
            if checked['issues']:
                raise EditError(422, 'validation_failed', issues=checked['issues'])
            db.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?)', (new_id(), identifier, expected, 'local-user', note, self.now()))
        return self.detail(identifier)

    def publish(self, identifier, expected, release):
        if not isinstance(release, str) or re.fullmatch(r'[a-z][a-z0-9.-]{0,79}', release) is None or release.startswith('draft-'):
            raise EditError(400, 'invalid_release_name')
        with self.connection(write=True) as db:
            draft = self._draft(db, identifier, expected)
            if db.execute('SELECT 1 FROM snapshots WHERE release=?', (release,)).fetchone():
                raise EditError(409, 'release_exists')
            if not db.execute('SELECT 1 FROM reviews WHERE draft_id=? AND head_id=?', (identifier, expected)).fetchone():
                raise EditError(409, 'review_required')
            data, base = self._dataset(db, expected), self._dataset(db, draft['base_id'])
            data['release'] = release
            old = {e['id']: e for e in base['entities']}
            events = db.execute('SELECT reason,details FROM events WHERE draft_id=? ORDER BY rowid', (identifier,)).fetchall()
            for entity in data['entities']:
                if entity['revisionID'] != old[entity['id']]['revisionID']:
                    ref = lambda e: dict(id=e['id'], revisionID=e['revisionID'])
                    reasons = [e['reason'] for e in events if json.loads(e['details'])['entityID'] == entity['id']]
                    data['changes'].append(dict(id=new_id(), revisionID=new_id(), kind='edit',
                        before=[dict(release=base['release'], record=ref(old[entity['id']]))],
                        after=[dict(release=release, record=ref(entity))], rationale=' / '.join(reasons)))
            checked = self.validator.check(data, self._history(db))
            if checked['issues']:
                raise EditError(422, 'validation_failed', issues=checked['issues'])
            snapshot_id = self._insert(db, data, 'published', checked['canonical'])
            db.execute('UPDATE drafts SET published_id=? WHERE id=?', (snapshot_id, identifier))
        return dict(release=release, sha256=hashlib.sha256(checked['canonical'].encode()).hexdigest())

    def backup(self, destination):
        destination = Path(destination).resolve()
        if destination == self.path or destination.exists():
            raise EditError(409, 'backup_destination_exists')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as source:
            with closing(sqlite3.connect(destination)) as target:
                source.backup(target)

    def verify(self):
        with self.connection() as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or db.execute('PRAGMA foreign_key_check').fetchall():
                raise EditError(422, 'database_integrity_failed')
            history = self._history(db)
            for row in db.execute('SELECT * FROM snapshots'):
                checked = self.validator.check(self._dataset(db, row['id']), history)
                allowed = {'staleRevision'} if row['kind'] == 'draft' else set()
                if any(i['code'] not in allowed for i in checked['issues']) or hashlib.sha256(checked['canonical'].encode()).hexdigest() != row['sha256']:
                    raise EditError(422, 'snapshot_integrity_failed', release=row['release'])
