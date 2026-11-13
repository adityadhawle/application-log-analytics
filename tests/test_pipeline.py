
from pathlib import Path

import src.database as database
from src.generator import generate_dataset
from src.pipeline import run_pipeline


def test_pipeline_end_to_end_and_idempotency(tmp_path, monkeypatch):
    # Arrange
    input_dir = tmp_path / "input"
    generate_dataset(input_dir, records=20, seed=42)

    test_db = tmp_path / "test_pipeline.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)

    structured_file = input_dir / "structured_logs.jsonl"
    text_file = input_dir / "application.log"

    # First pipeline run
    first_result = run_pipeline(structured_file, text_file)

    assert first_result["inserted_events"] == 20
    assert first_result["parsed_records"] == 23
    assert first_result["parser_rejects"] == 2
    assert first_result["validation_rejects"] == 2
    assert first_result["duplicate_rejects"] == 1

    # Verify database persistence
    conn = database.get_connection()

    stored_events = conn.execute(
        "SELECT COUNT(*) FROM log_events"
    ).fetchone()[0]

    conn.close()

    assert stored_events == 20

    # Second run: verify idempotency
    second_result = run_pipeline(structured_file, text_file)

    assert second_result["inserted_events"] == 0

    conn = database.get_connection()

    stored_events = conn.execute(
        "SELECT COUNT(*) FROM log_events"
    ).fetchone()[0]

    conn.close()

    assert stored_events == 20


import pytest
import src.pipeline as pipeline


def test_pipeline_failure_and_retry(tmp_path, monkeypatch):
    # Arrange
    input_dir = tmp_path / "input"
    generate_dataset(input_dir, records=20, seed=42)

    test_db = tmp_path / "retry_test.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)

    structured_file = input_dir / "structured_logs.jsonl"
    text_file = input_dir / "application.log"

    original_save_events = pipeline.save_events
    attempt = {"count": 0}

    # Simulate a temporary database failure
    def fail_once(records, run_id):
        attempt["count"] += 1

        if attempt["count"] == 1:
            raise RuntimeError("Simulated database failure")

        return original_save_events(records, run_id)

    monkeypatch.setattr(pipeline, "save_events", fail_once)

    # First run should fail
    with pytest.raises(RuntimeError, match="Simulated database failure"):
        pipeline.run_pipeline(structured_file, text_file)

    # Verify failed run status
    conn = database.get_connection()

    failed_status = conn.execute(
        "SELECT status FROM pipeline_runs"
    ).fetchone()[0]

    conn.close()

    assert failed_status == "FAILED"

    # Retry should succeed
    retry_result = pipeline.run_pipeline(
        structured_file, text_file
    )

    assert retry_result["inserted_events"] == 20

    # Verify final database state
    conn = database.get_connection()

    stored_events = conn.execute(
        "SELECT COUNT(*) FROM log_events"
    ).fetchone()[0]

    run_statuses = conn.execute(
        "SELECT status FROM pipeline_runs ORDER BY started_at"
    ).fetchall()

    conn.close()

    assert stored_events == 20
    assert [row[0] for row in run_statuses] == [
        "FAILED", "SUCCESS"
    ]

def test_pipeline_with_empty_input(tmp_path, monkeypatch):
    input_dir = tmp_path / "empty_input"
    input_dir.mkdir()

    structured_file = input_dir / "structured_logs.jsonl"
    text_file = input_dir / "application.log"

    structured_file.write_text("", encoding="utf-8")
    text_file.write_text("", encoding="utf-8")

    test_db = tmp_path / "empty_test.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)

    result = pipeline.run_pipeline(
        structured_file, text_file
    )

    assert result["parsed_records"] == 0
    assert result["parser_rejects"] == 0
    assert result["validation_rejects"] == 0
    assert result["duplicate_rejects"] == 0
    assert result["inserted_events"] == 0

    conn = database.get_connection()
    stored_events = conn.execute(
        "SELECT COUNT(*) FROM log_events"
    ).fetchone()[0]
    conn.close()

    assert stored_events == 0

import json


def test_pipeline_accepts_out_of_order_timestamps(tmp_path, monkeypatch):
    input_dir = tmp_path / "late_input"
    input_dir.mkdir()

    structured_file = input_dir / "structured_logs.jsonl"
    text_file = input_dir / "application.log"

    records = [
        {
            "event_id": "evt_90000001",
            "timestamp": "2026-11-13T12:00:00Z",
            "service_id": "svc_001",
            "service_name": "payment-api",
            "severity": "INFO",
            "message": "Newer event",
            "endpoint": "/payments",
            "status_code": 200,
            "latency_ms": 100
        },
        {
            "event_id": "evt_90000002",
            "timestamp": "2026-11-12T10:00:00Z",
            "service_id": "svc_001",
            "service_name": "payment-api",
            "severity": "WARNING",
            "message": "Late arriving event",
            "endpoint": "/payments",
            "status_code": 200,
            "latency_ms": 150
        }
    ]

    with structured_file.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record) + "\n")

    text_file.write_text("", encoding="utf-8")

    test_db = tmp_path / "late_test.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)

    result = pipeline.run_pipeline(structured_file, text_file)

    assert result["inserted_events"] == 2
    assert result["parser_rejects"] == 0
    assert result["validation_rejects"] == 0

    conn = database.get_connection()

    timestamps = conn.execute(
        "SELECT timestamp FROM log_events ORDER BY timestamp"
    ).fetchall()

    conn.close()

    assert len(timestamps) == 2
    assert timestamps[0][0] < timestamps[1][0]

def test_pipeline_rejects_null_required_fields(tmp_path, monkeypatch):
    input_dir = tmp_path / "null_input"
    input_dir.mkdir()

    structured_file = input_dir / "structured_logs.jsonl"
    text_file = input_dir / "application.log"

    valid_record = {
        "event_id": "evt_91000001",
        "timestamp": "2026-11-13T12:00:00Z",
        "service_id": "svc_001",
        "service_name": "payment-api",
        "severity": "INFO",
        "message": "Valid event",
        "endpoint": "/payments",
        "status_code": 200,
        "latency_ms": 100
    }

    null_record = {
        **valid_record,
        "event_id": "evt_91000002",
        "message": None
    }

    missing_record = {
        **valid_record,
        "event_id": "evt_91000003"
    }
    del missing_record["timestamp"]

    with structured_file.open("w", encoding="utf-8") as file:
        for record in [valid_record, null_record, missing_record]:
            file.write(json.dumps(record) + "\n")

    text_file.write_text("", encoding="utf-8")

    test_db = tmp_path / "null_test.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)

    result = pipeline.run_pipeline(structured_file, text_file)

    assert result["inserted_events"] == 1
    assert result["validation_rejects"] == 1
    assert result["parser_rejects"] == 1

    conn = database.get_connection()

    stored_events = conn.execute(
        "SELECT COUNT(*) FROM log_events"
    ).fetchone()[0]

    rejected_records = conn.execute(
        "SELECT COUNT(*) FROM rejected_records"
    ).fetchone()[0]

    conn.close()

    assert stored_events == 1
    assert rejected_records == 2

def test_pipeline_rejects_schema_drift(tmp_path, monkeypatch):
    input_dir = tmp_path / "schema_input"
    input_dir.mkdir()

    structured_file = input_dir / "structured_logs.jsonl"
    text_file = input_dir / "application.log"

    valid_record = {
        "event_id": "evt_92000001",
        "timestamp": "2026-11-13T12:00:00Z",
        "service_id": "svc_001",
        "service_name": "payment-api",
        "severity": "INFO",
        "message": "Valid event",
        "endpoint": "/payments",
        "status_code": 200,
        "latency_ms": 100
    }

    drift_record = {
        **valid_record,
        "event_id": "evt_92000002",
        "new_unexpected_field": "unexpected_value"
    }

    with structured_file.open("w", encoding="utf-8") as file:
        file.write(json.dumps(valid_record) + "\n")
        file.write(json.dumps(drift_record) + "\n")

    text_file.write_text("", encoding="utf-8")

    test_db = tmp_path / "schema_test.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)

    result = pipeline.run_pipeline(structured_file, text_file)

    assert result["inserted_events"] == 1
    assert result["validation_rejects"] == 1
    assert result["parser_rejects"] == 0

    conn = database.get_connection()

    stored_events = conn.execute(
        "SELECT COUNT(*) FROM log_events"
    ).fetchone()[0]

    rejected_records = conn.execute(
        "SELECT COUNT(*) FROM rejected_records"
    ).fetchone()[0]

    conn.close()

    assert stored_events == 1
    assert rejected_records == 1

def test_pipeline_rejects_invalid_service_reference(tmp_path, monkeypatch):
    input_dir = tmp_path / "reference_input"
    input_dir.mkdir()

    structured_file = input_dir / "structured_logs.jsonl"
    text_file = input_dir / "application.log"

    valid_record = {
        "event_id": "evt_93000001",
        "timestamp": "2026-11-13T12:00:00Z",
        "service_id": "svc_001",
        "service_name": "payment-api",
        "severity": "INFO",
        "message": "Valid service",
        "endpoint": "/payments",
        "status_code": 200,
        "latency_ms": 100
    }

    invalid_record = {
        **valid_record,
        "event_id": "evt_93000002",
        "service_id": "svc_999"
    }

    with structured_file.open("w", encoding="utf-8") as file:
        file.write(json.dumps(valid_record) + "\n")
        file.write(json.dumps(invalid_record) + "\n")

    text_file.write_text("", encoding="utf-8")

    test_db = tmp_path / "reference_test.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)

    result = pipeline.run_pipeline(structured_file, text_file)

    assert result["inserted_events"] == 1
    assert result["validation_rejects"] == 1

    conn = database.get_connection()

    stored_events = conn.execute(
        "SELECT COUNT(*) FROM log_events"
    ).fetchone()[0]

    rejected_records = conn.execute(
        "SELECT COUNT(*) FROM rejected_records"
    ).fetchone()[0]

    conn.close()

    assert stored_events == 1
    assert rejected_records == 1
