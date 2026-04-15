from __future__ import annotations

import hashlib
import hmac
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .models import ApiKey

API_KEY_SCHEME = "sha256"


def hash_api_key(raw: str) -> str:
    return f"{API_KEY_SCHEME}${hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


def ensure_api_key_storage(engine: Engine) -> None:
    with engine.begin() as conn:
        columns = {row[1] for row in conn.execute(text("PRAGMA table_info(api_keys)"))}
        if "key_hash" not in columns:
            conn.execute(text("ALTER TABLE api_keys ADD COLUMN key_hash VARCHAR"))
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_key_hash "
                "ON api_keys(key_hash)"
            )
        )


def migrate_api_keys(db: Session) -> None:
    dirty = False
    for api_key in db.query(ApiKey).all():
        if api_key.key_hash:
            if api_key.key and hmac.compare_digest(api_key.key_hash, hash_api_key(api_key.key)):
                api_key.key = None
                db.add(api_key)
                dirty = True
            continue
        if api_key.key:
            api_key.key_hash = hash_api_key(api_key.key)
            api_key.key = None
            db.add(api_key)
            dirty = True
    if dirty:
        db.commit()


def lookup_api_key(db: Session, raw: str) -> Optional[ApiKey]:
    hashed = hash_api_key(raw)
    api_key = db.query(ApiKey).filter(ApiKey.key_hash == hashed).first()
    if api_key:
        return api_key

    legacy_key = db.query(ApiKey).filter(ApiKey.key == raw).first()
    if legacy_key and legacy_key.key and hmac.compare_digest(legacy_key.key, raw):
        legacy_key.key_hash = hashed
        legacy_key.key = None
        db.add(legacy_key)
        db.commit()
        db.refresh(legacy_key)
        return legacy_key
    return None
