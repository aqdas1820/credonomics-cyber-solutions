# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class ClosingConnection(sqlite3.Connection):
    """Commit/roll back and release the database handle at each context boundary."""
    def __exit__(self,kind,value,traceback):
        try:return super().__exit__(kind,value,traceback)
        finally:self.close()


def data_directory():
    from .windows_package import package_family_name
    family=package_family_name()
    local=Path(os.environ.get('LOCALAPPDATA',Path.home()))
    default=local/'Packages'/family/'LocalState' if family else local/'CredoNomicsCyberSolutions'
    root = Path(os.environ.get('CREDONOMICS_DATA_DIR') or default)
    root.mkdir(parents=True, exist_ok=True)
    return root


class Store:
    def __init__(self, path=None):
        self.path = Path(path) if path else data_directory() / 'workspace.sqlite3'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY, kind TEXT NOT NULL,
              phone TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL, created TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS record_lookup ON records(kind, phone);
            CREATE TABLE IF NOT EXISTS counters(name TEXT PRIMARY KEY, value INTEGER NOT NULL);
            ''')

    def connect(self):
        return sqlite3.connect(self.path, timeout=10,factory=ClosingConnection)

    def get(self, key, default=None):
        with self.connect() as db:
            row = db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        if not row:return default
        try:value=json.loads(row[0])
        except (ValueError,TypeError):return default
        if key in ('appearance','branding','business','folders','window','print_preferences'):
            if not isinstance(value,dict):return default if isinstance(default,dict) else {}
            clean={}
            for name,item in value.items():
                if key=='appearance':
                    if name=='theme' and isinstance(item,str) and item in ('Light','Dark','System','High contrast'):clean[name]=item
                    elif name in ('compact_menu','reduce_motion','reduce_transparency') and type(item) is bool:clean[name]=item
                elif key=='window':
                    if name=='maximized' and type(item) is bool:clean[name]=item
                    elif name in ('x','y','width','height') and type(item) is int and abs(item)<100000:clean[name]=item
                elif key in ('branding','business'):
                    text_fields={'product_name','company_name','logo','accent','support','website','copyright','name','address','gstin','upi','footer'}
                    if name not in text_fields or isinstance(item,str):clean[name]=item
                elif isinstance(item,str):clean[name]=item
            return clean
        return value

    def set(self, key, value):
        self.set_many({key:value})

    def set_many(self, values):
        with self.connect() as db:
            db.executemany('INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',[(key,json.dumps(value)) for key,value in values.items()])

    def save_record(self, kind, phone, title, body):
        with self.connect() as db:
            return db.execute('INSERT INTO records(kind,phone,title,body,created) VALUES(?,?,?,?,?)',
                (kind, phone, title, json.dumps(body), datetime.now(timezone.utc).isoformat())).lastrowid

    def records(self, kind, phone=''):
        with self.connect() as db:
            rows = db.execute('SELECT id,title,body,created,phone FROM records WHERE kind=? AND phone LIKE ? ORDER BY id DESC', (kind, '%' + phone + '%')).fetchall()
        result=[]
        for row in rows:
            try:body=json.loads(row[2])
            except (ValueError,TypeError):body=None
            result.append(dict(id=row[0],title=row[1],body=body if isinstance(body,dict) else {},corrupt=not isinstance(body,dict),created=row[3],phone=row[4]))
        return result

    def delete_record(self, identifier):
        with self.connect() as db:
            db.execute('DELETE FROM records WHERE id=?', (identifier,))

    def next_number(self, key='invoice'):
        with self.connect() as db:
            db.execute('INSERT INTO counters VALUES(?,1) ON CONFLICT(name) DO UPDATE SET value=value+1', (key,))
            number = db.execute('SELECT value FROM counters WHERE name=?', (key,)).fetchone()[0]
        return f'CN-{number:05d}'
