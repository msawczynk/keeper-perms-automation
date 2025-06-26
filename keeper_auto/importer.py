"""Apply CSV changes to Keeper."""
import csv, base64, datetime, tempfile, os
from pathlib import Path
from .csv_schema import PermRow
from .keeper_client import get_record, put_record, create_record, upload_file
from .config import META_FOLDER_UID, LOG_FOLDER_UID, IMMUTABLE_RECORDS
from .logger import log as build_log

def _encode_row(row: list[str]) -> str:
    return base64.b64encode(",".join(row).encode()).decode()

def apply_csv(path: str | Path, dry: bool = False):
    path = Path(path)
    stamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    changes: list[str] = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for raw in reader:
            row_dict = dict(zip(header, raw))
            perm = PermRow(**row_dict)
            rec = get_record(perm.record_uid)
            wanted = _encode_row(raw)
            current = rec.custom_fields.get("perms")

            if current == wanted:
                continue  # already correct

            changes.append(perm.record_uid)
            if dry:
                continue

            if IMMUTABLE_RECORDS:
                # create successor record and mark current as superseded
                new_rec = rec.clone()  # type: ignore
                new_rec.custom_fields["perms"] = wanted
                create_record(new_rec)
                rec.custom_fields["superseded_by"] = new_rec.record_uid
                put_record(rec)
            else:
                rec.custom_fields["perms"] = wanted
                put_record(rec)

    # build and upload artefacts
    log_bytes = build_log({"csv": path.name, "changes": changes, "dry": dry})
    if not dry:
        upload_file(META_FOLDER_UID, path, f"perms_{stamp}.csv")
    # always store log
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(log_bytes)
        tmp_path = tmp.name
    upload_file(LOG_FOLDER_UID, tmp_path, f"log_{stamp}.json.gz")
    os.unlink(tmp_path)

    print(f"{'DRY' if dry else 'LIVE'} run complete – {len(changes)} record(s) touched.")
