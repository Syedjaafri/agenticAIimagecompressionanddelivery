from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "logs" / "delivery_log.csv"
FIELDS = [
    "timestamp_utc", "recipient", "original_kb", "compressed_kb", "selected_quality",
    "similarity", "attempts", "status", "message"
]


def write_delivery_log(record: dict) -> None:
    LOG_PATH.parent.mkdir(exist_ok=True)
    exists = LOG_PATH.exists()
    row = {key: record.get(key, "") for key in FIELDS}
    row["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    with LOG_PATH.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(row)
