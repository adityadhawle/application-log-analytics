
import time
from pathlib import Path

import src.database as db
from src.pipeline import run_pipeline


def main():
    # Use a separate database for benchmarking
    db.DB_PATH = Path("data/output/benchmark.db")

    structured_file = Path("data/benchmark/structured_logs.jsonl")
    text_file = Path("data/benchmark/application.log")

    start_time = time.perf_counter()

    counts = run_pipeline(structured_file, text_file)

    elapsed = time.perf_counter() - start_time

    throughput = counts["parsed_records"] / elapsed

    print("\n========== PERFORMANCE BENCHMARK ==========")
    print(f"Execution time: {elapsed:.2f} seconds")
    print(f"Input records: {counts['parsed_records']}")
    print(f"Processing throughput: {throughput:.2f} records/second")
    print(f"New events inserted: {counts['inserted_events']}")
    print("============================================")


if __name__ == "__main__":
    main()
