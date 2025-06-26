
"""Generate a CSV permission template from your Keeper vault.

The template:
* has one row per record
* has one column per team (so you can mark access)
* preserves the folder path so you can filter/sort easily
"""

from __future__ import annotations
import csv, argparse
from pathlib import Path
from typing import Iterable

from keepercommander import enterprise, vault      # type: ignore

from .keeper_client import get_client
from .config import TEMPLATE_PATH

HEADERS_STATIC = ["record_uid", "title", "subfolders"]

def _list_teams(sdk) -> list[str]:
    ent = enterprise.EnterpriseCommand(sdk)
    ent.execute('')
    return [t['name'] for t in ent.teams]

def _folder_path(tree, folder_uid: str) -> str:
    parts = []
    cur = tree.folders[folder_uid]
    while cur:
        parts.append(cur.name or cur.uid)
        cur = tree.folders.get(cur.parent_uid)
    return "/".join(reversed(parts))

def _iter_records(root_uid: str | None = None):
    sdk = get_client()
    tree = vault.FolderTree(sdk)
    start = [root_uid] if root_uid else [tree.root.uid]
    for root in start:
        for fld, rec in tree.subfolder_records(root):
            path = _folder_path(tree, fld.uid)
            yield rec.uid, (rec.title or ""), path

def build_template(folder_uid: str | None, force: bool = False):
    if TEMPLATE_PATH.exists() and not force:
        print(f"Template already exists: {TEMPLATE_PATH} – pass --force to overwrite")
        return

    sdk = get_client()
    teams = _list_teams(sdk)
    headers = HEADERS_STATIC + teams

    rows = sorted(_iter_records(folder_uid), key=lambda r: (r[2].lower(), r[1].lower()))

    TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TEMPLATE_PATH.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        for uid, title, path in rows:
            writer.writerow([uid, title, path] + [''] * len(teams))
    print(f"✓ CSV template saved to {TEMPLATE_PATH} – {len(rows)} records, {len(teams)} teams")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate a Keeper permissions template")
    ap.add_argument("--folder", help="Folder UID to start from (defaults to root)")
    ap.add_argument("--force", action="store_true", help="Overwrite existing template")
    args = ap.parse_args()
    build_template(args.folder, args.force)
