
import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path


SERVICES = [
    ("payment-api", "svc_001"),
    ("user-api", "svc_002"),
    ("order-api", "svc_003"),
    ("notification-api", "svc_004"),
]

SEVERITIES = ["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"]

ENDPOINTS = [
    "/api/v1/payments",
    "/api/v1/users",
    "/api/v1/orders",
    "/api/v1/notifications",
]

MESSAGES = [
    "Request processed successfully",
    "Database connection established",
    "Request validation failed",
    "Internal server error",
    "Request timeout",
]


def generate_event(index, rng, base_time):
    """Generate one deterministic synthetic application event."""

    service_name, service_id = rng.choice(SERVICES)
    timestamp = base_time + timedelta(
        seconds=rng.randint(0, 86400)
    )

    return {
        "event_id": f"evt_{index:08d}",
        "timestamp": timestamp.isoformat(),
        "service_name": service_name,
        "service_id": service_id,
        "severity": rng.choice(SEVERITIES),
        "message": rng.choice(MESSAGES),
        "endpoint": rng.choice(ENDPOINTS),
        "status_code": rng.choice(
            [200, 201, 400, 401, 404, 429, 500, 502, 503]
        ),
        "latency_ms": round(rng.uniform(1, 5000), 2),
    }


def to_plain_text(event):
    """Convert an event into semi-structured log format."""

    return (
        f'{event["timestamp"]} | {event["severity"]} | '
        f'service={event["service_name"]} | '
        f'service_id={event["service_id"]} | '
        f'event_id={event["event_id"]} | '
        f'endpoint={event["endpoint"]} | '
        f'status={event["status_code"]} | '
        f'latency_ms={event["latency_ms"]} | '
        f'message={event["message"]}'
    )


def generate_dataset(output_dir, records=1000, seed=42):
    """Generate reproducible structured and semi-structured logs."""

    if records < 1:
        raise ValueError("records must be greater than zero")

    rng = random.Random(seed)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_time = datetime(
        2026, 11, 1, tzinfo=timezone.utc
    )

    structured_count = records // 2
    events = [
        generate_event(i + 1, rng, base_time)
        for i in range(records)
    ]

    structured = events[:structured_count]
    semi_structured = events[structured_count:]

    structured_lines = [
        json.dumps(event) for event in structured
    ]

    text_lines = [
        to_plain_text(event) for event in semi_structured
    ]

    # Negative scenarios are deliberately added separately
    # from the normal generated records.

    duplicate_event = dict(events[0])

    missing_field = dict(events[1])
    missing_field.pop("timestamp")

    invalid_reference = dict(events[2])
    invalid_reference["service_id"] = "svc_unknown"

    schema_change = dict(events[3])
    schema_change["unexpected_field"] = "unexpected_value"

    malformed_json = '{"event_id": "broken", "timestamp": '

    structured_lines.extend([
        json.dumps(duplicate_event),
        json.dumps(missing_field),
        json.dumps(invalid_reference),
        json.dumps(schema_change),
        malformed_json,
    ])

    # Shuffle timestamps/order to simulate out-of-order arrival.
    rng.shuffle(text_lines)

    structured_path = output_dir / "structured_logs.jsonl"
    text_path = output_dir / "application.log"

    structured_path.write_text(
        "\n".join(structured_lines) + "\n",
        encoding="utf-8",
    )

    text_path.write_text(
        "\n".join(text_lines) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "seed": seed,
        "requested_valid_records": records,
        "structured_records": len(structured),
        "semi_structured_records": len(semi_structured),
        "additional_test_records": 5,
        "known_scenarios": [
            "duplicate_event",
            "missing_timestamp",
            "invalid_service_reference",
            "unexpected_schema_field",
            "malformed_json",
            "out_of_order_arrival",
        ],
    }

    (output_dir / "expected_manifest.json").write_text(
        json.dumps(manifest, indent=4),
        encoding="utf-8",
    )

    print("Dataset generation completed!")
    print(f"Output directory: {output_dir.resolve()}")
    print(f"Structured records: {len(structured_lines)}")
    print(f"Semi-structured records: {len(text_lines)}")
    print("Additional negative scenarios: 5")
    print(f"Random seed: {seed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate synthetic application logs"
    )

    parser.add_argument(
        "--records",
        type=int,
        default=1000,
        help="Number of normal records to generate",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    parser.add_argument(
        "--output",
        default="data/sample",
    )

    args = parser.parse_args()

    generate_dataset(
        output_dir=args.output,
        records=args.records,
        seed=args.seed,
    )
