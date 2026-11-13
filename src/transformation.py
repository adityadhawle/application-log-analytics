
def deduplicate_records(records):
    """
    Keep the first occurrence of each event_id.
    Return unique records and duplicate rejects.
    """
    seen_event_ids = set()
    accepted = []
    rejected = []

    for record in records:
        event_id = record["event_id"]

        if event_id in seen_event_ids:
            rejected.append({
                "record": None,
                "error": [{
                    "type": "duplicate_event_id",
                    "message": f"Duplicate event_id: {event_id}"
                }],
                "source_file": record.get("source_file"),
                "source_line": record.get("source_line"),
                "raw_record": record.get("raw_record"),
            })
            continue

        seen_event_ids.add(event_id)
        accepted.append(record)

    return accepted, rejected
