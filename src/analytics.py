
import csv
import math
from pathlib import Path

from src.database import get_connection


REPORT_PATH = Path("reports/service_metrics.csv")


def calculate_percentile(values, percentile=0.95):
    """Calculate percentile using the nearest-rank method."""
    if not values:
        return 0.0

    sorted_values = sorted(values)
    index = math.ceil(percentile * len(sorted_values)) - 1
    return sorted_values[max(0, index)]


def generate_service_metrics():
    """Calculate error and latency metrics for each service."""

    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                service_name,
                severity,
                status_code,
                latency_ms
            FROM log_events
            ORDER BY service_name, timestamp
        """).fetchall()

    if not rows:
        print("No events available for analytics.")
        return []

    grouped = {}

    for row in rows:
        service = row["service_name"]

        if service not in grouped:
            grouped[service] = {
                "total_requests": 0,
                "error_count": 0,
                "http_5xx_count": 0,
                "latencies": [],
            }

        metrics = grouped[service]

        metrics["total_requests"] += 1
        metrics["latencies"].append(row["latency_ms"])

        if row["severity"] in ("ERROR", "CRITICAL"):
            metrics["error_count"] += 1

        if row["status_code"] >= 500:
            metrics["http_5xx_count"] += 1

    results = []

    for service, metrics in sorted(grouped.items()):
        total = metrics["total_requests"]

        results.append({
            "service_name": service,
            "total_requests": total,
            "error_count": metrics["error_count"],
            "error_rate_pct": round(
                metrics["error_count"] / total * 100, 2
            ),
            "http_5xx_count": metrics["http_5xx_count"],
            "http_5xx_rate_pct": round(
                metrics["http_5xx_count"] / total * 100, 2
            ),
            "avg_latency_ms": round(
                sum(metrics["latencies"]) / total, 2
            ),
            "p95_latency_ms": round(
                calculate_percentile(metrics["latencies"]), 2
            ),
        })

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with REPORT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=results[0].keys(),
        )
        writer.writeheader()
        writer.writerows(results)

    print("\n========== SERVICE ANALYTICS ==========")

    for result in results:
        print(f"\nService: {result['service_name']}")
        print(f"Total requests: {result['total_requests']}")
        print(f"Error rate: {result['error_rate_pct']}%")
        print(f"HTTP 5xx rate: {result['http_5xx_rate_pct']}%")
        print(f"Average latency: {result['avg_latency_ms']} ms")
        print(f"P95 latency: {result['p95_latency_ms']} ms")

    print("\nReport saved to:", REPORT_PATH)

    return results


if __name__ == "__main__":
    generate_service_metrics()
