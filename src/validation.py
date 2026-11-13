
import math
import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


VALID_SERVICES = {
    "svc_001": "payment-api",
    "svc_002": "user-api",
    "svc_003": "order-api",
    "svc_004": "notification-api",
}

VALID_SEVERITIES = {
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
}


class LogEvent(BaseModel):
    """Canonical validated application log schema."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    timestamp: datetime
    service_id: str = Field(min_length=1)
    service_name: str = Field(min_length=1)
    severity: Literal[
        "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    ]
    message: str = Field(min_length=1)
    endpoint: str = Field(min_length=1)
    status_code: int
    latency_ms: float

    source_file: str = Field(min_length=1)
    source_line: int = Field(ge=1)
    raw_record: str

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, value):
        if not re.fullmatch(r"evt_[0-9]{8}", value):
            raise ValueError("Invalid event_id format")
        return value

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamp must include timezone")

        return value.astimezone(timezone.utc)

    @field_validator("service_id")
    @classmethod
    def validate_service_id(cls, value):
        if value not in VALID_SERVICES:
            raise ValueError(f"Unknown service_id: {value}")
        return value

    @field_validator("service_name")
    @classmethod
    def validate_service_name(cls, value, info):
        service_id = info.data.get("service_id")

        if service_id and VALID_SERVICES.get(service_id) != value:
            raise ValueError("service_name and service_id mismatch")

        return value

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value):
        if value not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity: {value}")
        return value

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, value):
        if not value.startswith("/"):
            raise ValueError("Endpoint must start with /")
        return value

    @field_validator("status_code")
    @classmethod
    def validate_status_code(cls, value):
        if not 100 <= value <= 599:
            raise ValueError("HTTP status must be between 100 and 599")
        return value

    @field_validator("latency_ms")
    @classmethod
    def validate_latency(cls, value):
        if not math.isfinite(value) or value < 0:
            raise ValueError("Latency must be finite and non-negative")
        return value


def validate_record(record):
    """Validate one parsed record and return a traceable result."""

    try:
        event = LogEvent.model_validate(record)

        return {
            "record": event.model_dump(mode="json"),
            "error": None,
            "source_file": record.get("source_file"),
            "source_line": record.get("source_line"),
            "raw_record": record.get("raw_record"),
        }

    except ValidationError as exc:
        return {
            "record": None,
            "error": exc.errors(include_url=False),
            "source_file": record.get("source_file"),
            "source_line": record.get("source_line"),
            "raw_record": record.get("raw_record"),
        }


def validate_records(records):
    """Validate a collection of parsed records."""

    accepted = []
    rejected = []

    for record in records:
        result = validate_record(record)

        if result["error"] is None:
            accepted.append(result["record"])
        else:
            rejected.append(result)

    return accepted, rejected
