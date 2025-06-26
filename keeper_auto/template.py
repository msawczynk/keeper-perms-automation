"""Builds or lints the CSV template."""
import csv, sys, argparse
from pathlib import Path
from .config import TEMPLATE_PATH, TEAM_CODES

HEADERS = ["record_uid", "title", "subfolders", *TEAM_CODES]

def build_template(force: bool = False):
    if TEMPLATE_PATH.exists() and not force:
        print(f"Template already exists: {TEMPLATE_PATH}")
        return

    TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TEMPLATE_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(HEADERS)
    print(f"Template written to {TEMPLATE_PATH}")

def lint(paths):
    bad = False
    for p in paths:
        with open(p, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                print(f"{p}: empty CSV", file=sys.stderr)
                bad = True
                continue
            if header != HEADERS:
                print(f"{p}: header mismatch\n  expected: {HEADERS}\n  found:    {header}", file=sys.stderr)
                bad = True
    if bad:
        sys.exit(1)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--lint", action="store_true", help="lint CSV headers")
    ap.add_argument("paths", nargs="*", help="CSV files")
    args = ap.parse_args()

    if args.lint:
        lint(args.paths)
    else:
        build_template(force=True)
