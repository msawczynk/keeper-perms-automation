keeper‑perms‑automation
=======================

A zero‑trust, audit‑friendly workflow for granting granular team permissions
to Keeper records, driven entirely by a version‑controlled CSV inside Keeper
itself.

## highlights

* **single‑source CSV** – admins tweak rights in Excel, no JSON knowledge needed
* **immutable audit trail** – every CSV version and automation log lands back
  in Keeper (`Metadata History/` and `Automation Logs/`)
* **dry‑run / reconcile** – preview changes or nightly drift checks
* **pre‑commit lint** – blocks bad encodings or header drift before it merges
* **no external storage** – whole state lives in your vault

## quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# write a fresh template for admins
python cli.py template

# admin edits template in Excel …

# preview the effects
python cli.py dry-run --csv perms/template.csv

# apply live
python cli.py apply --csv perms/template.csv
```

All configuration (folder UIDs, team codes, immutability flag) is done via
environment variables – see `keeper_auto/config.py` for details.

