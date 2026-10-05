#!/usr/bin/env python3
"""Initialize, export, back up, and verify a local editing database."""
import argparse
from pathlib import Path
import sys
from editing_db import Database, EditError, ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=ROOT / '.local/curricula.sqlite3')
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init')
    init.add_argument('--data-dir', type=Path, default=ROOT / 'data/releases')
    export = commands.add_parser('export')
    export.add_argument('release')
    export.add_argument('output', type=Path)
    work = commands.add_parser('export-work')
    work.add_argument('review_id')
    work.add_argument('output', type=Path)
    backup = commands.add_parser('backup')
    backup.add_argument('output', type=Path)
    commands.add_parser('verify')
    args = parser.parse_args()
    if args.command != 'init' and not args.db.is_file():
        parser.error('Database does not exist. Run init first.')
    database = Database(args.db)
    if args.command == 'init':
        database.seed(args.data_dir)
        database.seed(ROOT / 'data/catalog')
        database.seed(ROOT / 'data/authoring')
        database.seed_work(ROOT / 'data/work-reviews')
        print(f'Initialized {args.db}: {len(database.published())} published snapshots')
    elif args.command == 'export':
        if args.output.exists():
            parser.error('Output exists; choose a new path.')
        args.output.write_bytes(database.export(args.release))
        print(args.output)
    elif args.command == 'backup':
        database.backup(args.output)
        print(args.output)
    elif args.command == 'export-work':
        from authoring_work import work_records
        import json
        if args.output.exists():
            parser.error('Output exists; choose a new path.')
        record = next((r for r in work_records(database) if r['id'] == args.review_id), None)
        if record is None:
            parser.error('Unknown work review.')
        args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
        print(args.output)
    elif args.command == 'verify':
        database.verify()
        print('Database, published snapshots, and draft histories verified.')


if __name__ == '__main__':
    try:
        main()
    except EditError as error:
        sys.exit(f'{error.code}: {error.details}')
