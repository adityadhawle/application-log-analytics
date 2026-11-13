# Application Log Analytics Pipeline

## 1. Project Overview

An end-to-end Python-based application log analytics pipeline that processes structured JSONL and semi-structured text application logs.

The pipeline parses, normalizes, validates, deduplicates, and stores application events in SQLite. It also generates service-level analytics, tracks rejected records, and maintains pipeline execution history.

## 2. Key Features

- Structured JSONL and semi-structured text log parsing
- Timestamp and severity normalization
- Pydantic-based schema and data-quality validation
- Duplicate event detection using deterministic event IDs
- SQLite-based event and rejection storage
- Idempotent pipeline execution
- Pipeline run tracking with SUCCESS and FAILED statuses
- Error-rate and latency analytics
- 100K-record benchmark
- Automated unit and integration tests
- Failure simulation and retry verification

## 3. Architecture

```text
Structured JSONL       Semi-structured Text
       |                         |
       +-----------+-------------+
                   |
                Parser
                   |
          Timestamp Normalization
                   |
             Validation
                   |
              Deduplication
                   |
          +--------+--------+
          |                 |
      Valid Events      Rejected Records
          |                 |
          +--------+--------+
                   |
              SQLite DB
                   |
          Analytics Aggregation
                   |
             CSV Reports
```

## 4. Technology Stack

- Python 3.14
- Pydantic 2.x – schema validation
- SQLite – local data persistence
- Pytest – unit and integration testing
- Python Standard Library – CSV reporting, percentile calculations, file handling and database operations

## 5. Project Structure

application-log-analytics/
|-- config/
|-- data/
|   |-- input/
|   |-- sample/
|   |-- benchmark/
|   `-- output/
|-- reports/
|   `-- service_metrics.csv
|-- src/
|   |-- generator.py
|   |-- parser.py
|   |-- validation.py
|   |-- transformation.py
|   |-- database.py
|   |-- pipeline.py
|   |-- analytics.py
|   `-- benchmark.py
|-- tests/
|   |-- test_parser.py
|   |-- test_validation.py
|   `-- test_pipeline.py
|-- requirements.txt
|-- README.md
`-- .gitignore

## 6. Setup Instructions

Clone the repository and navigate to the project directory.

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## 7. Generate Sample Data

```bash
python -m src.generator --records 1000 --seed 42
```

The generator creates structured and semi-structured log files along with an expected manifest.

## 8. Run the Pipeline

```bash
python -m src.pipeline
```

The pipeline processes sample input files and stores valid events and rejected records in SQLite.

Database location:

```text
data/output/log_analytics.db
```

## 9. Generate Analytics

```bash
python -m src.analytics
```

The analytics output is generated at:

```text
reports/service_metrics.csv
```

Metrics include:

- Total requests
- Error count and error rate
- HTTP 5xx count and rate
- Average latency
- P95 latency

## 10. Run Tests

Run the complete test suite:

```bash
python -m pytest -v
```

Current verified result:

**20 tests passed.**

Coverage includes parsing, validation, duplicate handling, empty input, out-of-order timestamps, null values, schema drift, invalid references, pipeline idempotency, and failure recovery.

## 11. Performance Benchmark

Generate 100K records:

```python
from pathlib import Path
from src.generator import generate_dataset

generate_dataset(
    Path("data/benchmark"),
    records=100000,
    seed=42
)
```

Run the benchmark:

```bash
python -m src.benchmark
```

Verified initial benchmark:

| Metric | Result |
|---|---:|
| Raw input lines | 100,005 |
| Parsed records | 100,003 |
| Unique valid events | 100,000 |
| Rejected records | 5 |
| Execution time | 3.55 seconds |
| Throughput | 28,209 records/second |
| Events inserted | 100,000 |

A second run inserted zero new events, confirming idempotency.

## 12. Data Quality and Reliability

The pipeline handles:

- Malformed JSON and malformed log lines
- Missing required fields
- Invalid service references
- Unexpected schema fields
- Duplicate event IDs
- Invalid timestamps and severity values
- Empty input batches
- Late-arriving and out-of-order events
- Database failures and retry scenarios

Rejected records are stored separately for troubleshooting and auditability.

## 13. Design Decisions

- SQLite provides a lightweight local persistence layer without requiring external infrastructure.
- Pydantic provides strict schema validation.
- Deterministic event IDs support duplicate detection.
- `INSERT OR IGNORE` prevents duplicate event insertion during reruns.
- Separate pipeline run and rejection tables support operational monitoring.
- Batch processing keeps the implementation simple and locally reproducible.

## 14. Future Improvements

- Incremental processing using event-time watermarks
- Configurable service reference data
- Structured application monitoring and alerting
- Parallel processing for larger workloads
- Production deployment using cloud storage and distributed processing

---

**Project:** Application Log Analytics Pipeline  
**Purpose:** End-to-end data ingestion, quality validation, transformation, persistence, and analytics.
