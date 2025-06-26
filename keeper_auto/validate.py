"""Nightly reconcile – compare CSV perms vs vault perms."""
import csv, base64, sys
from pathlib import Path
from typing import Union
from .csv_schema import PermRow
from .keeper_client import get_record
from .config import TEMPLATE_PATH

def _encode_row(row: list[str]) -> str:
    """Base64 encodes a list of strings after joining them."""
    return base64.b64encode(",".join(row).encode()).decode()

def run(csv_path: Union[str, Path] = TEMPLATE_PATH):
    """
    Compares the state in the CSV with the state in the Keeper vault.

    Exits with status code 2 if a mismatch is found.

    Args:
        csv_path (Union[str, Path]): The path to the CSV file to use for comparison.
    """
    mismatch = False
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            for raw in reader:
                # Create a dictionary from the header and the current row
                row_dict = dict(zip(header, raw))
                perm = PermRow(**row_dict)
                rec = get_record(perm.record_uid)
                wanted = _encode_row(raw)
                current = rec.custom_fields.get("perms")
                if current != wanted:
                    print(f"mismatch: {perm.record_uid}", file=sys.stderr)
                    mismatch = True
    except FileNotFoundError:
        print(f"Error: CSV file not found at {csv_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

    if mismatch:
        sys.exit(2)
