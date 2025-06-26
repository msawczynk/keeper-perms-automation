"""Apply CSV changes to Keeper."""
import csv, base64, datetime, tempfile, os
from pathlib import Path
from typing import Union
from .csv_schema import PermRow
from .keeper_client import get_record, put_record, create_record, upload_file
from .config import META_FOLDER_UID, LOG_FOLDER_UID, IMMUTABLE_RECORDS
from .logger import log as build_log

def _encode_row(row: list[str]) -> str:
    """Base64 encodes a list of strings after joining them."""
    return base64.b64encode(",".join(row).encode()).decode()

def apply_csv(path: Union[str, Path], dry: bool = False):
    """
    Reads a permissions CSV and applies the state to Keeper records.

    Args:
        path (Union[str, Path]): The path to the CSV file.
        dry (bool): If True, performs a dry run without making live changes.
    """
    path = Path(path)
    stamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    changes: list[str] = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for raw in reader:
            # Create a dictionary from the header and the current row
            row_dict = dict(zip(header, raw))
            perm = PermRow(**row_dict)
            rec = get_record(perm.record_uid)
            wanted = _encode_row(raw)
            current = rec.custom_fields.get("perms")

            # If the permission is already correctly set, skip it
            if current == wanted:
                continue

            changes.append(perm.record_uid)
            if dry:
                continue

            # Apply changes based on the immutability setting
            if IMMUTABLE_RECORDS:
                # Create a successor record and mark the current one as superseded
                new_rec = rec.clone()
                new_rec.custom_fields["perms"] = wanted
                # The new record needs a UID before it can be referenced
                new_rec_uid = create_record(new_rec)
                rec.custom_fields["superseded_by"] = new_rec_uid
                put_record(rec)
            else:
                # Update the record in-place
                rec.custom_fields["perms"] = wanted
                put_record(rec)

    # Build and upload audit artifacts
    log_bytes = build_log({"csv": path.name, "changes": changes, "dry": dry})
    if not dry:
        # Upload a snapshot of the CSV that was applied
        upload_file(META_FOLDER_UID, str(path), f"perms_{stamp}.csv")

    # Always store the log file of the run
    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as tmp:
        tmp.write(log_bytes)
        tmp_path = tmp.name
    try:
        upload_file(LOG_FOLDER_UID, tmp_path, f"log_{stamp}.json.gz")
    finally:
        os.unlink(tmp_path) # Clean up the temporary file

    print(f"{'DRY' if dry else 'LIVE'} run complete – {len(changes)} record(s) touched.")
