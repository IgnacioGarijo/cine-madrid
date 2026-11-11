"""Shared data and identity rules. No inferred identity is silently confirmed."""
import hashlib
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

MADRID = ZoneInfo('Europe/Madrid')
ROOT = Path(__file__).resolve().parents[1]

def now():
    return datetime.now(MADRID).isoformat(timespec='seconds')

def read_json(path, default=None):
    return json.loads(Path(path).read_text(encoding='utf-8')) if Path(path).exists() else default

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)

def stable_id(*values):
    return hashlib.sha256('|'.join(map(str, values)).encode()).hexdigest()[:20]

def normalize(text):
    text = unicodedata.normalize('NFKD', text.casefold())
    return re.sub(r'[^a-z0-9]', '', ''.join(c for c in text if not unicodedata.combining(c)))

def clean_title(title):
    return re.sub(r'\s*\((?:VOSE|VO|VE|35mm|70mm|digital|4K)\)\s*', ' ', title, flags=re.I).strip()

def trusted_identity(record, catalog):
    """Require both an alias AND director. Similar titles alone are candidates."""
    matches = [m for m in catalog if normalize(clean_title(record['title'])) in
               {normalize(x) for x in [m['title'], m.get('original_title', ''), *m.get('aliases', [])]}
               and record.get('director') and normalize(record['director']) == normalize(m.get('director',''))]
    return matches[0] if len(matches) == 1 else None

class Incidents:
    def __init__(self, previous=()):
        self.previous = {x['id']: x for x in previous}
        self.current = {}

    def add(self, source, code, entity, message, url='', severity='warning'):
        key = stable_id(source, code, entity)
        old = self.previous.get(key, {})
        self.current[key] = dict(id=key, source_id=source, code=code, entity=entity,
                                message=message, url=url, severity=severity, status='open',
                                first_seen=old.get('first_seen', now()), last_seen=now())

    def finish(self, checked_sources):
        for key, old in self.previous.items():
            if key not in self.current:
                item = dict(old)
                if old['source_id'] in checked_sources and old['status'] == 'open':
                    item.update(status='resolved', resolved_at=now())
                self.current[key] = item
        return sorted(self.current.values(), key=lambda x:(x['status'] != 'open', x['first_seen']), reverse=False)
