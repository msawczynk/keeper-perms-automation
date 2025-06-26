"""Nightly reconcile – compare CSV perms vs vault perms."""
import csv, base64, sys
from pathlib import Path
from .csv_schema import PermRow
from .keeper_client import get_record
from .config import TEMPLATE_PATH

def _encode_row(row: list[str]) -> str:
    return base64.b64encode(",".join(row).encode()).decode()

def run(csv_path: str | Path = TEMPLATE_PATH):
    mismatch = False
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for raw in reader:
            row_dict = dict(zip(header, raw))
            perm = PermRow(**row_dict)
            rec = get_record(perm.record_uid)
            wanted = _encode_row(raw)
            current = rec.custom_fields.get("perms")
            if current != wanted:
                print(f"mismatch: {perm.record_uid}", file=sys.stderr)
                mismatch = True
    if mismatch:
        sys.exit(2)
