
import argparse
from pathlib import Path

from src.parser import parse_file
from src.validation import validate_records
from src.transformation import deduplicate_records
from src.database import (
    initialize_database,
    start_run,
    save_events,
    save_rejects,
    finish_run,
)


def run_pipeline(structured_file, text_file):
    initialize_database()
    run_id = start_run()

    counts = {
        "parsed_records": 0,
        "parser_rejects": 0,
        "validation_rejects": 0,
        "duplicate_rejects": 0,
        "inserted_events": 0,
    }

    try:
        # 1. Parse both input formats
        structured_records, structured_errors = parse_file(
            str(structured_file)
        )
        text_records, text_errors = parse_file(str(text_file))

        parsed_records = structured_records + text_records
        parser_rejects = structured_errors + text_errors

        counts["parsed_records"] = len(parsed_records)
        counts["parser_rejects"] = len(parser_rejects)

        # 2. Validate parsed records
        valid_records, validation_rejects = validate_records(
            parsed_records
        )
        counts["validation_rejects"] = len(validation_rejects)

        # 3. Remove duplicate event IDs
        unique_records, duplicate_rejects = deduplicate_records(
            valid_records
        )
        counts["duplicate_rejects"] = len(duplicate_rejects)

        # 4. Persist valid events and all rejected records
        all_rejects = (
            parser_rejects
            + validation_rejects
            + duplicate_rejects
        )

        inserted = save_events(unique_records, run_id)
        counts["inserted_events"] = inserted

        save_rejects(all_rejects, run_id)

        # 5. Mark the run successful
        finish_run(run_id, "SUCCESS", counts)

        print("\n========== PIPELINE SUMMARY ==========")
        print("Run ID:", run_id)
        print("Status: SUCCESS")
        print("Parsed records:", counts["parsed_records"])
        print("Parser rejects:", counts["parser_rejects"])
        print("Validation rejects:", counts["validation_rejects"])
        print("Duplicate rejects:", counts["duplicate_rejects"])
        print("Unique valid events:", len(unique_records))
        print("New events inserted:", inserted)
        print("Total rejects:", len(all_rejects))
        print("======================================")

        return counts

    except Exception as exc:
        finish_run(run_id, "FAILED", counts, str(exc))
        raise


def main():
    argument_parser = argparse.ArgumentParser(
        description="Application Log Analytics Pipeline"
    )

    argument_parser.add_argument(
        "--structured",
        default="data/sample/structured_logs.jsonl",
        help="Path to structured JSONL logs",
    )

    argument_parser.add_argument(
        "--text",
        default="data/sample/application.log",
        help="Path to semi-structured text logs",
    )

    args = argument_parser.parse_args()

    run_pipeline(
        Path(args.structured),
        Path(args.text),
    )


if __name__ == "__main__":
    main()
