# Keeper Per﻿ms Automation

> Granular, auditable, **CSV‑driven** access control for Keeper Security records – zero external state, 100 % tracked inside the vault.

---

\## 📑 Table of Contents

1. [Why this project?](#why-this-project)
2. [Key capabilities](#key-capabilities)
3. [Architecture](#architecture)
4. [Folder layout](#folder-layout)
5. [Quick start](#quick-start)
6. [Configuration](#configuration)
7. [Workflow details](#workflow-details)
8. [Pre‑commit & linting](#pre‑commit--linting)
9. [CI / CD](#ci--cd)
10. [Security model](#security-model)
11. [Troubleshooting](#troubleshooting)
12. [Contributing](#contributing)
13. [Roadmap](#roadmap)
14. [License](#license)

---

\## Why this project?
Keeper’s native sharing UI is excellent for ad‑hoc tasks but **doesn’t scale** when you manage hundreds of records across teams, environments and compliance zones. This repo delivers:

* A **single source of truth (CSV)** admins can edit in Excel without JSON or SDK knowledge.
* **Immutable audit trail** – every CSV and automation log is itself a Keeper record.
* **Idempotent scripts** – safe to re‑run, safe to roll back.
* **Dry‑run + reconcile** – detect drift *before* it bites.

---

\## Key capabilities

| Feature                    | How it works                                                                                           |
| -------------------------- | ------------------------------------------------------------------------------------------------------ |
| Template generator         | `python cli.py template` writes a UTF‑8 CSV with locked headers.                                       |
| Base64 fingerprint         | Each Keeper record stores its CSV row in a custom field `perms` for traceability.                      |
| Read‑only / Read‑write ACL | Columns contain `RO` / `RW`, translated into Keeper folder permissions.                                |
| Immutable mode             | Old records are never overwritten; successors are created and the chain is linked via `superseded_by`. |
| Structured logs            | Gzipped JSON, uploaded to `Automation Logs/`.                                                          |
| Drift control              | `cli.py reconcile` compares vault vs CSV and exits non‑zero on mismatch, ideal for nightly CI.         |

---

\## Architecture

```text
keeper-perms-automation/
│
├── perms/                ← CSV input & archived versions
│   ├── template.csv       (generated)
│   └── versions/          (empty; Keeper receives copies)
│
├── keeper_auto/          ← Python package
│   ├── template.py        (build_template & header‑lint)
│   ├── importer.py        (apply_csv / dry‑run)
│   ├── validate.py        (reconcile)
│   ├── keeper_client.py   (thin Commander wrapper)
│   ├── csv_schema.py      (pydantic validation)
│   ├── logger.py          (structured JSON)
│   └── config.py          (env‑driven settings)
│
├── cli.py                ← unified entry point
├── requirements.txt      ← runtime deps
├── .pre-commit-config.yaml
└── README.md             ← you are here
```

> **Commander version**: Tested against Keeper Commander 17.x. Older versions may lack required APIs.

---

\## Quick start

```bash
# 1. Install Python 3.12 & Keeper Commander
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Export minimal config (or add to .env)
export KPR_VAULT="user@example.com"   # Keeper login email
export KPR_DEVICE="DevOps‑Laptop"     # arbitrary device name
export META_FOLDER_UID="_abc123"      # UID of Metadata History/
export LOG_FOLDER_UID="_def456"       # UID of Automation Logs/

# 3. Generate a fresh template
python cli.py template

# 4. Admin fills in perms/template.csv in Excel (UTF‑8!)

# 5. Preview changes – *no writes yet*
python cli.py dry-run --csv perms/template.csv

# 6. Apply live
python cli.py apply  --csv perms/template.csv
```

\### Nightly reconcile in cron/Jenkins

```bash
0 2 * * * cd /opt/keeper-perms-automation && source .venv/bin/activate && python cli.py reconcile || \ \
  curl -X POST https://hooks.slack.com/services/… -d 'Automation drift detected!'
```

---

\## Configuration

| Variable            | Default                | Purpose                                                                      |
| ------------------- | ---------------------- | ---------------------------------------------------------------------------- |
| `KPR_VAULT`         |  –                     | Keeper login (email).                                                        |
| `KPR_DEVICE`        |  ""                    | Device name for Commander registration.                                      |
| `TEAM_CODES`        | `TBE-KT,Remoteservice` | Comma‑separated list of ACL columns after the fixed headers.                 |
| `META_FOLDER_UID`   | required               | UID where CSV versions are uploaded.                                         |
| `LOG_FOLDER_UID`    | required               | UID where logs are uploaded.                                                 |
| `IMMUTABLE_RECORDS` | `1`                    | `1` → create successor records; `0` → in‑place update (less audit‑friendly). |

Place them in your CI secret store or a local `.env` loaded via direnv.

---

\## Workflow details

1. **Template generation** – `template.py` writes headers `record_uid,title,subfolders,<team‑codes…>`.
2. **Admin editing** – use Excel dropdowns `RO` / `RW`, save *UTF‑8* CSV.
3. **Importer**

   1. Validates rows with pydantic.
   2. Base64‑encodes the entire row → `wanted_hash`.
   3. Compares with existing `perms` field.
   4. Writes or skips accordingly (idempotent).
4. **Immutable mode** – if enabled, original record becomes historical; new record UID is stored in `superseded_by`.
5. **Artifacts** – The processed CSV and a compressed JSON log are uploaded back into Keeper.

\### CSV header lock
A custom pre‑commit hook blocks merges when the header order drifts. Run `pre‑commit install` once.

---

\## Pre‑commit & linting

```bash
pre-commit install
pre-commit run --all-files
```

Hooks included:

* End‑of‑file fixer / trailing whitespace / UTF‑8 check.
* `csv-header-lock` – ensures every CSV checked in uses the canonical header.

---

\## CI / CD

| Stage                    | Purpose                         | Typical tools                   |
| ------------------------ | ------------------------------- | ------------------------------- |
| Format & lint            | `pre‑commit run`                | GitHub Actions, GitLab CI       |
| Unit tests (TBD)         | pytest                          | ‘‘                              |
| Dry‑run                  | `python cli.py dry-run --csv …` | depends                         |
| Live apply (manual gate) | `python cli.py apply …`         | GitHub Actions + “Approve” step |
| Reconcile (scheduled)    | `cli.py reconcile`              | cron / Jenkins                  |

---

\## Security model

* **No external storage** – CSV + logs are vaulted back to Keeper, encrypted client‑side.
* **Principle of least privilege** – service user only needs *folder‑level manage* rights for the three automation folders and *share* rights for target records.
* **Secrets** – login creds and folder UIDs live in CI secret vault; never stored in code.
* **Auditability** – every change is a new record or a diff in `Automation Logs/`.

---

\## Troubleshooting

| Symptom                              | Cause                  | Fix                                                         |
| ------------------------------------ | ---------------------- | ----------------------------------------------------------- |
| `UnicodeDecodeError` on CSV          | Excel saved as ANSI    | Save as UTF‑8 or run through `iconv -f cp1252 -t utf8`.     |
| `header mismatch` pre‑commit failure | Column order changed   | Re‑generate template or revert stray column.                |
| `vault throttled (HTTP 429)`         | Huge batch apply       | Run importer with smaller CSV chunks; script is idempotent. |
| `mismatch` in reconcile              | Manual change in vault | Re‑run importer or adjust CSV, then commit.                 |

---

\## Contributing

1. Fork & create feature branch.
2. Enable pre‑commit.
3. Write / update tests (coming soon).
4. Open PR – CI must be green and at least one reviewer approval.
5. Squash & merge.

---

\## Roadmap

* [ ] Unit test harness via pytest + moto‑style Keeper mock.
* [ ] GitHub Action template.
* [ ] Swap CSV parser for `pandas` + type hints once pyarrow is stable.
* [ ] Optional YAML input.
* [ ] API server variant (FastAPI) for self‑service portals.

---

\## License
This project is licensed under the **MIT License** – see `LICENSE` for details.
