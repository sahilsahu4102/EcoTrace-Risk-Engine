import sqlite3
import json
import os
from datetime import datetime

# Path to local sqlite cache
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "risk_cache.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS risk_cache (
                query TEXT PRIMARY KEY,
                risk_score REAL,
                risk_level TEXT,
                confidence_score REAL,
                confidence_level TEXT,
                response_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def get_cached_risk(query: str):
    """Fetch from cache if it was created within the last 24 hours."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT response_json FROM risk_cache 
            WHERE lower(query) = lower(?) AND created_at > datetime('now', '-1 day')
            """, (query,)
        )
        row = cur.fetchone()
        if row:
            return json.loads(row["response_json"])
    return None

def save_cached_risk(query: str, risk_score: float, risk_level: str, confidence_score: float, confidence_level: str, response_dict: dict):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO risk_cache (query, risk_score, risk_level, confidence_score, confidence_level, response_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(query) DO UPDATE SET
                risk_score=excluded.risk_score,
                risk_level=excluded.risk_level,
                confidence_score=excluded.confidence_score,
                confidence_level=excluded.confidence_level,
                response_json=excluded.response_json,
                created_at=datetime('now')
            """,
            (query, risk_score, risk_level, confidence_score, confidence_level, json.dumps(response_dict))
        )
        conn.commit()

def get_recent_history(limit: int = 50):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT query, risk_score, risk_level, confidence_score, confidence_level, created_at 
            FROM risk_cache 
            ORDER BY created_at DESC 
            LIMIT ?
            """, (limit,)
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]
