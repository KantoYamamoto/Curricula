#!/usr/bin/env python3
"""Read-only, loopback-only API. Only explicit web assets are served."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from schema_v2_store import Index

ROOT = Path(__file__).resolve().parents[1]

class Store:
    def __init__(self, directory):
        self.releases = {}
        self.indexes = {}
        for path in sorted(Path(directory).glob('*.json')):
            data = json.loads(path.read_text(encoding='utf-8'))
            if data['schemaVersion'] not in ('0.1.0', '0.2.0') or data['release'] != path.stem:
                raise ValueError(f'Invalid schema or release identity: {path.name}')
            for field in ('entities', 'frameworks', 'sources', 'contexts', 'relations', 'readingOutlines'):
                ids = [entry['id'] for entry in data[field]]
                if len(ids) != len(set(ids)):
                    raise ValueError(f'Duplicate IDs: {path.name}/{field}')
            self.releases[data['release']] = data
            if data['schemaVersion'] == '0.2.0':
                self.indexes[data['release']] = Index(data)
        if not self.releases:
            raise ValueError('No releases found. Run make export first.')

    def get(self, path, query):
        if path == '/api/v1/releases':
            return 200, {'releases': [{'release': d['release'], 'schemaVersion': d['schemaVersion']} for d in self.releases.values()]}
        parts = path.strip('/').split('/')
        if len(parts) < 5 or parts[:3] != ['api', 'v1', 'releases']:
            return 404, {'error': {'code': 'route_not_found'}}
        data = self.releases.get(parts[3])
        if data is None:
            return 404, {'error': {'code': 'release_not_found', 'release': parts[3]}}
        envelope = {'release': data['release'], 'schemaVersion': data['schemaVersion']}
        def result(status, payload):
            return status, {**envelope, **payload}
        def error(status, code):
            return result(status, {'error': {'code': code}})
        resource = parts[4]
        index = self.indexes.get(data['release'])
        if index and resource not in ('relations', 'overview'):
            if len(parts) not in (5, 6):
                return error(404, 'route_not_found')
            status, body = index.get(resource, parts[5] if len(parts) == 6 else None, query)
            return result(status, body)
        if query and resource != 'relations':
            return error(400, 'unknown_query')
        if resource == 'overview' and len(parts) == 5:
            return result(200, {k: data[k] for k in ('frameworks', 'contexts', 'readingOutlines', 'limitations') + (('taxons',) if index else ())})
        if resource == 'relations' and len(parts) == 5:
            if any(k not in ('entityId', 'contextId') or len(v) != 1 or not v[0] for k, v in query.items()):
                return error(400, 'invalid_query')
            entity_id = query.get('entityId', [None])[0]
            context_id = query.get('contextId', [None])[0]
            if index:
                entity_id = index.resolve(entity_id) if entity_id else None
                context_id = index.resolve(context_id) if context_id else None
            if entity_id and not any(e['id'] == entity_id for e in data['entities']):
                return error(404, 'entity_not_found')
            if context_id and not any(c['id'] == context_id for c in data['contexts']):
                return error(404, 'context_not_found')
            relations = [r for r in data['relations'] if
                         (not entity_id or entity_id in (r['from'], r['to'])) and
                         (not context_id or r.get('contextID') == context_id)]
            return result(200, {'relations': relations, 'contextPolicy': 'exact' if context_id else 'all_preserved'})
        fields = {'entities': 'entities', 'frameworks': 'frameworks', 'sources': 'sources', 'contexts': 'contexts', 'reading-outlines': 'readingOutlines'}
        if resource in fields and len(parts) == 6:
            entry = next((e for e in data[fields[resource]] if e['id'] == parts[5]), None)
            if entry is None:
                return error(404, 'id_not_found')
            payload = {'data': entry}
            if resource == 'frameworks':
                payload['items'] = [e for e in data['entities'] if e.get('frameworkID') == entry['id']]
            return result(200, payload)
        return error(404, 'route_not_found')


def handler_for(store):
    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, body, content_type='application/json; charset=utf-8'):
            raw = json.dumps(body, ensure_ascii=False).encode() if isinstance(body, dict) else body
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'")
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(raw)

        def do_GET(self):
            url = urlsplit(self.path)
            path = unquote(url.path)
            if path.startswith('/api/'):
                status, payload = store.get(path, parse_qs(url.query, keep_blank_values=True))
                return self.respond(status, payload)
            assets = {'/': ('index.html', 'text/html'), '/read': ('index.html', 'text/html'),
                      '/structure': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
            if path not in assets:
                return self.respond(404, {'error': {'code': 'route_not_found'}})
            file, content_type = assets[path]
            return self.respond(200, (ROOT / 'web' / file).read_bytes(), content_type + '; charset=utf-8')

        do_HEAD = do_GET
        def do_POST(self):
            self.respond(405, {'error': {'code': 'read_only'}})
        do_PUT = do_DELETE = do_PATCH = do_POST
    return Handler

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'data/releases')
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler_for(Store(args.data_dir)))
    print(f'Curricula: http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
