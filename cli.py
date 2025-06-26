
#!/usr/bin/env python3
"""Command‑line wrapper for the permissions automation toolkit."""

import argparse, sys
from keeper_auto import template

def main(argv=None):
    ap = argparse.ArgumentParser(prog="cli.py")
    ap.add_argument("cmd", choices=["template", "apply", "dry-run", "reconcile"])
    ap.add_argument("--csv", help="Path to a permissions CSV to process")
    ap.add_argument("--folder", help="Folder UID to scope the template")
    args = ap.parse_args(argv)

    if args.cmd == "template":
        template.build_template(folder_uid=args.folder, force=True)
    else:
        print("TODO: other commands not yet implemented")

if __name__ == "__main__":
    main()
