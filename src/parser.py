
import json
from datetime import datetime, timezone
from pathlib import Path


SEVERITY_MAP = {
    "WARN": "WARNING",
    "WARNING": "WARNING",
    "INFO": "INFO",
    "DEBUG": "DEBUG",
    "ERROR": "ERROR",
    "FATAL": "CRITICAL",
    "CRITICAL": "CRITICAL",
}


def normalize_timestamp(value):
    """Convert supported ISO-8601 timestamps to UTC."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError("Missing or invalid timestamp")

    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)

    # Documented assumption: timestamps without timezone are UTC.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc).isoformat()


def normalize_severity(value):
    """Normalize severity names to standard uppercase values."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError("Missing or invalid severity")

    severity = value.strip().upper()
    return SEVERITY_MAP.get(severity, severity)


def parse_json_line(raw_line):
    """Parse one structured JSON log record."""

    record = json.loads(raw_line)

    if not isinstance(record, dict):
        raise ValueError("JSON log must contain an object")

    return record


def parse_text_line(raw_line):
    """Parse one semi-structured application log record."""

    parts = raw_line.strip().split(" | ", 2)

    if len(parts) < 3:
        raise ValueError("Invalid plain-text log format")

    timestamp, severity, remaining = parts

    record = {
        "timestamp": timestamp.strip(),
        "severity": severity.strip(),
    }

    fields = remaining.split(" | ")

    for field in fields:
        key, separator, value = field.partition("=")

        if not separator:
            raise ValueError(f"Invalid key-value field: {field}")

        key = key.strip()
        if key == "service":
            key = "service_name"
        value = value.strip()

        if key == "status":
            key = "status_code"

        if key in record:
            raise ValueError(f"Duplicate field: {key}")

        record[key] = value

    return record


def parse_record(raw_line, source_file, line_number, file_format):
    """Parse and normalize a single source record."""

    try:
        if not raw_line.strip():
            raise ValueError("Empty log record")

        if file_format == "json":
            record = parse_json_line(raw_line)
        elif file_format == "text":
            record = parse_text_line(raw_line)
        else:
            raise ValueError(f"Unsupported format: {file_format}")

        record["timestamp"] = normalize_timestamp(
            record.get("timestamp")
        )

        record["severity"] = normalize_severity(
            record.get("severity")
        )

        record["source_file"] = str(source_file)
        record["source_line"] = line_number
        record["raw_record"] = raw_line.rstrip("\r\n")

        return {
            "record": record,
            "error": None,
        }

    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return {
            "record": None,
            "error": str(exc),
            "source_file": str(source_file),
            "source_line": line_number,
            "raw_record": raw_line.rstrip("\r\n"),
        }


def parse_file(file_path):
    """Read a file and separate parsed records from parse failures."""

    path = Path(file_path)

    if path.suffix.lower() == ".jsonl":
        file_format = "json"
    elif path.suffix.lower() == ".log":
        file_format = "text"
    else:
        raise ValueError(f"Unsupported file extension: {path.suffix}")

    accepted = []
    rejected = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):

            result = parse_record(
                raw_line=raw_line,
                source_file=path.name,
                line_number=line_number,
                file_format=file_format,
            )

            if result["error"] is None:
                accepted.append(result["record"])
            else:
                rejected.append(result)

    return accepted, rejected
