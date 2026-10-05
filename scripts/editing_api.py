"""Explicitly enabled local editing API, separate from immutable read routes."""
from editing_db import EditError


class EditingAPI:
    def __init__(self, database, token):
        self.database, self.token = database, token

    def get(self, path, query):
        if query:
            raise EditError(400, 'unknown_query')
        if path == '/api/edit/session':
            return {'token': self.token, 'actor': 'local-user'}
        if path == '/api/edit/drafts':
            return {'drafts': self.database.list_drafts()}
        if path == '/api/edit/work':
            from authoring_work import work_records
            return {'work': work_records(self.database)}
        parts = path.strip('/').split('/')
        if len(parts) == 4 and parts[:3] == ['api', 'edit', 'drafts']:
            return self.database.detail(parts[3])
        if len(parts) == 6 and parts[:3] == ['api', 'edit', 'drafts'] and parts[4] == 'history':
            with self.database.connection() as db:
                draft = self.database._draft(db, parts[3])
                allowed = {draft['base_id'], draft['head_id']}
                for row in db.execute('SELECT before_id,after_id FROM events WHERE draft_id=?', (parts[3],)):
                    allowed.update(row)
                if parts[5] not in allowed:
                    raise EditError(404, 'snapshot_not_found')
                return {'dataset': self.database._dataset(db, parts[5])}
        if len(parts) == 5 and parts[:3] == ['api', 'edit', 'releases'] and parts[4] == 'export':
            return self.database.export(parts[3])
        raise EditError(404, 'route_not_found')

    def post(self, path, payload):
        if not isinstance(payload, dict):
            raise EditError(400, 'invalid_request')
        if path == '/api/edit/work':
            return self.database.record_work(payload)
        if path == '/api/edit/drafts' and set(payload) == {'baseRelease', 'title'}:
            if not isinstance(payload['baseRelease'], str):
                raise EditError(400, 'invalid_request')
            return self.database.create(payload['baseRelease'], payload['title'])
        parts = path.strip('/').split('/')
        if len(parts) != 5 or parts[:3] != ['api', 'edit', 'drafts']:
            raise EditError(404, 'route_not_found')
        if parts[4] == 'save':
            return self.database.save(parts[3], payload)
        if parts[4] == 'entities':
            return self.database.add_entity(parts[3], payload)
        if parts[4] == 'evidence':
            return self.database.add_evidence(parts[3], payload)
        if parts[4] == 'review' and set(payload) == {'expectedHead', 'note'}:
            if not isinstance(payload['expectedHead'], str):
                raise EditError(400, 'invalid_request')
            return self.database.review(parts[3], payload['expectedHead'], payload['note'])
        if parts[4] == 'publish' and set(payload) == {'expectedHead', 'release'}:
            if not isinstance(payload['expectedHead'], str):
                raise EditError(400, 'invalid_request')
            return self.database.publish(parts[3], payload['expectedHead'], payload['release'])
        raise EditError(400, 'invalid_request')
