
# Keeper Permissions Automation (PowerShell‑friendly)

This tool exports a **CSV permissions template** straight from your Keeper
vault and lets you map which **teams** should have access to which **records**.

> **Audience:** Windows users who are comfortable opening PowerShell but **do
> not** want to mess with Python internals or environment variables.

---

## 1. prerequisites

| item | how to check | where to get it |
|------|--------------|-----------------|
| Python 3.9 or later | `python --version` | <https://www.python.org/downloads/> |
| pip (comes with Python) | `pip --version` | installed with Python |
| Keeper Commander ≥ 17 | installed automatically below | –

---

## 2. download & install

1. **Download this zip** and **extract** it
   somewhere convenient, e.g. `C:\keeper-perms`.
2. Open **PowerShell**  
   *Start ▶ type “PowerShell” ▶ *Run as Administrator* (optional).*
3. Navigate into the folder:

```powershell
cd C:\keeper-perms
```

4. Install the Python package that talks to Keeper:

```powershell
pip install -r requirements.txt
```

*(If you get “pip is not recognised”, close PowerShell and reopen it after
re‑installing Python.)*

---

## 3. first‑time login (creates the cache)

Run:

```powershell
python .\cli.py template
```

You’ll be prompted:

```
No cached Keeper session found – please authenticate.
Keeper email: you@example.com
Master password: ********
Two‑factor code (leave blank if none):
```

After a successful login you’ll see:

```
✓ Session cached – future runs will skip the login prompts (file: %USERPROFILE%\.config\keeper\commander\automation.json)
✓ CSV template saved to perms\template.csv – 42 records, 5 teams
```

That **automation.json** file holds an encrypted device + refresh token that
Keeper issues. Future commands reuse it silently.

---

## 4. everyday use

```powershell
# regenerate the template for the whole vault
python .\cli.py template

# generate a template scoped to a specific folder UID
python .\cli.py template --folder AAAABBBBCCCC
```

The CSV lives in `perms\template.csv`. Open it in Excel, tick which teams
should get which records, then feed it back in with *apply* (coming soon).

---

## 5. where is the cache?

| OS | path |
|----|------|
| Windows | `%USERPROFILE%\.config\keeper\commander\automation.json` |
| macOS/Linux | `~/.config/keeper/commander/automation.json` |

Delete the file to force a brand‑new login.

---

## 6. troubleshooting

* **Password prompt doesn’t appear?**  
  Make sure you’re running **PowerShell**, not PowerShell ISE.

* **Module not found: keepercommander**  
  Run `pip install -r requirements.txt` again, and confirm you’re using the
  same Python that `python --version` reports.

* **Two‑factor fails**  
  Copy the 6‑digit TOTP code from your authenticator *quickly* – codes expire
  every 30 seconds.

---

## 7. next steps

* `apply` and `dry-run` sub‑commands will process the edited CSV and push
  permissions back to Keeper (work in progress).
