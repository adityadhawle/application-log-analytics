
import pytest

from src.parser import parse_text_line
from src.transformation import deduplicate_records


def test_parse_valid_text_log():
    line = (
        "2026-11-13T10:00:00Z | INFO | "
        "service=payment-api | "
        "event_id=evt_12345678 | "
        "message=Payment successful"
    )

    record = parse_text_line(line)

    assert record["service_name"] == "payment-api"
    assert record["severity"] == "INFO"
    assert record["event_id"] == "evt_12345678"


def test_parse_empty_text_log():
    with pytest.raises(ValueError):
        parse_text_line("")


def test_duplicate_event_is_rejected():
    records = [
        {"event_id": "evt_12345678", "source_line": 1},
        {"event_id": "evt_12345678", "source_line": 2},
    ]

    accepted, rejected = deduplicate_records(records)

    assert len(accepted) == 1
    assert len(rejected) == 1
    assert rejected[0]["error"][0]["type"] == "duplicate_event_id"


def test_unique_events_are_accepted():
    records = [
        {"event_id": "evt_12345678"},
        {"event_id": "evt_87654321"},
    ]

    accepted, rejected = deduplicate_records(records)

    assert len(accepted) == 2
    assert len(rejected) == 0


def test_empty_duplicate_input():
    accepted, rejected = deduplicate_records([])

    assert accepted == []
    assert rejected == []
