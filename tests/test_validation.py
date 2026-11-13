
import pytest

from src.validation import validate_record, validate_records


@pytest.fixture
def valid_record():
    return {
        "event_id": "evt_12345678",
        "timestamp": "2026-11-13T10:00:00+00:00",
        "service_id": "svc_001",
        "service_name": "payment-api",
        "severity": "ERROR",
        "message": "Payment request failed",
        "endpoint": "/api/payment",
        "status_code": 500,
        "latency_ms": 250.5,
        "source_file": "application.log",
        "source_line": 1,
        "raw_record": "sample log record",
    }


def test_valid_record_is_accepted(valid_record):
    result = validate_record(valid_record)
    assert result["error"] is None
    assert result["record"]["event_id"] == "evt_12345678"


def test_empty_input():
    accepted, rejected = validate_records([])
    assert accepted == []
    assert rejected == []


def test_missing_required_field(valid_record):
    valid_record.pop("timestamp")
    result = validate_record(valid_record)
    assert result["record"] is None
    assert result["error"] is not None


def test_unknown_service_reference(valid_record):
    valid_record["service_id"] = "svc_unknown"
    result = validate_record(valid_record)
    assert result["record"] is None
    assert result["error"] is not None


def test_service_name_mismatch(valid_record):
    valid_record["service_name"] = "wrong-service"
    result = validate_record(valid_record)
    assert result["record"] is None
    assert result["error"] is not None


def test_invalid_http_status(valid_record):
    valid_record["status_code"] = 700
    result = validate_record(valid_record)
    assert result["record"] is None
    assert result["error"] is not None


def test_negative_latency(valid_record):
    valid_record["latency_ms"] = -10
    result = validate_record(valid_record)
    assert result["record"] is None
    assert result["error"] is not None


def test_unexpected_schema_field(valid_record):
    valid_record["unexpected_column"] = "extra"
    result = validate_record(valid_record)
    assert result["record"] is None
    assert result["error"] is not None
