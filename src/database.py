
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


DB_PATH = Path("data/output/log_analytics.db")


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    """Create database tables if they do not already exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT NOT NULL,
                parsed_records INTEGER DEFAULT 0,
                parser_rejects INTEGER DEFAULT 0,
                validation_rejects INTEGER DEFAULT 0,
                duplicate_rejects INTEGER DEFAULT 0,
                inserted_events INTEGER DEFAULT 0,
                error_message TEXT
            );

            CREATE TABLE IF NOT EXISTS log_events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                service_id TEXT NOT NULL,
                service_name TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                source_file TEXT NOT NULL,
                source_line INTEGER NOT NULL,
                run_id TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
            );

            CREATE TABLE IF NOT EXISTS rejected_records (
                reject_id TEXT PRIMARY KEY,
                source_file TEXT,
                source_line INTEGER,
                error_json TEXT NOT NULL,
                raw_record TEXT,
                run_id TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
            );

            CREATE INDEX IF NOT EXISTS idx_events_timestamp
                ON log_events(timestamp);

            CREATE INDEX IF NOT EXISTS idx_events_service
                ON log_events(service_name);

            CREATE INDEX IF NOT EXISTS idx_events_severity
                ON log_events(severity);
        """)


def start_run():
    """Create a new pipeline run and return its ID."""
    run_id = str(uuid4())
    started_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO pipeline_runs (run_id, started_at, status)
            VALUES (?, ?, ?)
            """,
            (run_id, started_at, "RUNNING"),
        )

    return run_id


def save_events(records, run_id):
    """Insert valid events; ignore event IDs already present."""
    rows = [
        (
            record["event_id"],
            record["timestamp"],
            record["service_id"],
            record["service_name"],
            record["severity"],
            record["message"],
            record["endpoint"],
            record["status_code"],
            record["latency_ms"],
            record["source_file"],
            record["source_line"],
            run_id,
        )
        for record in records
    ]

    with get_connection() as conn:
        before = conn.total_changes

        conn.executemany(
            """
            INSERT OR IGNORE INTO log_events (
                event_id, timestamp, service_id, service_name,
                severity, message, endpoint, status_code,
                latency_ms, source_file, source_line, run_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

        inserted = conn.total_changes - before

    return inserted


def save_rejects(rejects, run_id):
    """Persist rejected records with a deterministic reject ID."""
    rows = []

    for item in rejects:
        source_file = item.get("source_file") or ""
        source_line = item.get("source_line") or 0
        raw_record = item.get("raw_record") or ""
        error_json = json.dumps(
            item.get("error"),
            sort_keys=True,
            default=str,
        )

        fingerprint = "|".join([
            source_file,
            str(source_line),
            raw_record,
            error_json,
        ])

        reject_id = hashlib.sha256(
            fingerprint.encode("utf-8")
        ).hexdigest()

        rows.append((
            reject_id,
            source_file,
            source_line,
            error_json,
            raw_record,
            run_id,
        ))

    with get_connection() as conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO rejected_records (
                reject_id, source_file, source_line,
                error_json, raw_record, run_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    return len(rows)


def finish_run(run_id, status, counts, error_message=None):
    """Update pipeline run status and processing counts."""
    completed_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE pipeline_runs
            SET completed_at = ?,
                status = ?,
                parsed_records = ?,
                parser_rejects = ?,
                validation_rejects = ?,
                duplicate_rejects = ?,
                inserted_events = ?,
                error_message = ?
            WHERE run_id = ?
            """,
            (
                completed_at,
                status,
                counts.get("parsed_records", 0),
                counts.get("parser_rejects", 0),
                counts.get("validation_rejects", 0),
                counts.get("duplicate_rejects", 0),
                counts.get("inserted_events", 0),
                error_message,
                run_id,
            ),
        )
