#!/usr/bin/env python
import argparse, sys
from keeper_auto import template, importer, validate

def main():
    ap = argparse.ArgumentParser(description="Keeper perms automation CLI")
    ap.add_argument("cmd", choices=["template", "apply", "dry-run", "reconcile"])
    ap.add_argument("--csv", help="path to CSV")
    args = ap.parse_args()

    if args.cmd == "template":
        template.build_template(force=True)
    elif args.cmd == "apply":
        if not args.csv: sys.exit("need --csv")
        importer.apply_csv(args.csv, dry=False)
    elif args.cmd == "dry-run":
        if not args.csv: sys.exit("need --csv")
        importer.apply_csv(args.csv, dry=True)
    elif args.cmd == "reconcile":
        validate.run()
    else:
        ap.print_help()

if __name__ == "__main__":
    main()
