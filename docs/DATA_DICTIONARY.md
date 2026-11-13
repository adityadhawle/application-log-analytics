\# Data Dictionary – Application Log Analytics Pipeline



\## 1. Document Purpose



This document describes the source data, target database schema, field definitions, relationships, data grain, validation rules, and business assumptions used in the Application Log Analytics Pipeline.



\## 2. Source Data



The pipeline accepts two input formats:



| Source | Format | Description |

|---|---|---|

| Structured logs | JSONL | One JSON event per line |

| Semi-structured logs | Text | Key-value fields separated by delimiters |



\### Source Event Fields



| Field | Data Type | Description |

|---|---|---|

| event\_id | String | Unique event identifier |

| timestamp | ISO 8601 String | Event occurrence time |

| service\_id | String | Service reference identifier |

| service\_name | String | Application service name |

| severity | String | Log severity level |

| message | String | Log message |

| endpoint | String | API endpoint or application route |

| status\_code | Integer | HTTP response status |

| latency\_ms | Numeric | Request processing latency in milliseconds |



Additional metadata such as source file, source line, and raw record is maintained during processing for traceability.



\## 3. Target Database



The pipeline stores processed data in SQLite:



`data/output/log\_analytics.db`



The database contains three main tables.



\### 3.1 log\_events



\*\*Purpose:\*\* Stores validated and deduplicated application events.



\*\*Grain:\*\* One row per unique event ID.



\*\*Primary Key:\*\* event\_id



| Column | Data Type | Description |

|---|---|---|

| event\_id | TEXT | Unique event identifier; primary key |

| timestamp | TEXT | Normalized UTC event timestamp |

| service\_id | TEXT | Service reference identifier |

| service\_name | TEXT | Application service name |

| severity | TEXT | Normalized severity |

| message | TEXT | Application log message |

| endpoint | TEXT | API endpoint |

| status\_code | INTEGER | HTTP response status |

| latency\_ms | REAL | Processing latency in milliseconds |

| source\_file | TEXT | Original input file |

| source\_line | INTEGER | Original line number |

| run\_id | TEXT | Pipeline execution identifier |



\### 3.2 rejected\_records



\*\*Purpose:\*\* Stores records rejected during parsing, validation, or duplicate detection.



| Column | Data Type | Description |

|---|---|---|

| reject\_id | TEXT | Deterministic rejection identifier; primary key |

| source\_file | TEXT | Original input file |

| source\_line | INTEGER | Original line number |

| error\_json | TEXT | Rejection reason or validation errors |

| raw\_record | TEXT | Original input record |

| run\_id | TEXT | Pipeline execution identifier |



\### 3.3 pipeline\_runs



\*\*Purpose:\*\* Maintains pipeline execution history and operational status.



| Column | Data Type | Description |

|---|---|---|

| run\_id | TEXT | Unique pipeline execution identifier; primary key |

| started\_at | TEXT | Execution start timestamp |

| completed\_at | TEXT | Execution completion timestamp |

| status | TEXT | SUCCESS or FAILED |

| parsed\_records | INTEGER | Successfully parsed records |

| parser\_rejects | INTEGER | Records rejected during parsing |

| validation\_rejects | INTEGER | Records rejected during validation |

| duplicate\_rejects | INTEGER | Duplicate records detected |

| inserted\_events | INTEGER | New events inserted |

| error\_message | TEXT | Failure details, if any |



\## 4. Relationships



\- `pipeline\_runs.run\_id` identifies a pipeline execution.

\- `log\_events.run\_id` associates each inserted event with its processing run.

\- `rejected\_records.run\_id` associates each rejection with its processing run.

\- `log\_events.event\_id` uniquely identifies an event.

\- `rejected\_records.reject\_id` uniquely identifies a rejection entry.



\## 5. Data Quality Rules



| Rule | Validation |

|---|---|

| Event ID | Must follow `evt\_########` format |

| Timestamp | Must be valid and timezone-aware after normalization |

| Service reference | Service ID and service name must match configured reference data |

| Severity | Must belong to the supported severity values |

| Message | Required and non-null |

| Endpoint | Must begin with `/` |

| HTTP status | Must be between 100 and 599 |

| Latency | Must be finite and non-negative |

| Schema | Unexpected fields are rejected |

| Duplicate event | Only the first occurrence of an event ID is retained |



\## 6. Transformations



\- Normalize timestamps to UTC.

\- Normalize severity values, including WARN to WARNING and FATAL to CRITICAL.

\- Convert text log fields into the canonical event schema.

\- Validate records against the Pydantic model.

\- Deduplicate records using event\_id.

\- Persist accepted events and rejected records separately.



\## 7. Analytics Definitions



| Metric | Definition |

|---|---|

| Total Requests | Count of accepted events per service |

| Error Count | Events with severity ERROR or CRITICAL |

| Error Rate | Error Count / Total Requests × 100 |

| HTTP 5xx Count | Events with status code from 500 to 599 |

| HTTP 5xx Rate | HTTP 5xx Count / Total Requests × 100 |

| Average Latency | Arithmetic mean of latency\_ms |

| P95 Latency | 95th percentile using the nearest-rank method |



Analytics are grouped by service\_name and exported to `reports/service\_metrics.csv`.



\## 8. Assumptions and Design Decisions



\- Input files are processed as batch workloads.

\- Timezone-less timestamps are interpreted as UTC.

\- Event IDs are expected to be stable and unique across reruns.

\- The first occurrence of a duplicate event ID is retained.

\- Configured service reference data is treated as the valid service mapping.

\- SQLite is used for local, reproducible execution.

\- Rejected records are retained separately for troubleshooting and auditability.

\- Late-arriving and out-of-order events are accepted; event timestamps are not required to arrive chronologically.



\## 9. Known Limitations



\- The current implementation uses local file inputs and SQLite.

\- Distributed processing and cloud deployment are outside the current scope.

\- Incremental event-time watermarking and automated alerting are future improvements.
