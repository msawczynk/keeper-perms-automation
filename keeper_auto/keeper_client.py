
"""Keeper Commander login helper with persistent session caching.

On first run (no cached device/session), the user is prompted *interactively*
in the shell for their Keeper e‑mail, master password, and (optionally) a
two‑factor code.  The resulting device token + refresh token are stored in
``%APPDATA%\Keeper\commander\automation.json`` on Windows (or the equivalent
XDG path on macOS/Linux).  Subsequent runs re‑use that cache – no prompts.
"""

import os
from pathlib import Path
from getpass import getpass
from keepercommander import api, params      # type: ignore

CONF_PATH = Path(
    os.getenv("KPR_CONF", "~/.config/keeper/commander/automation.json")
).expanduser()

def _prompt_bootstrap():
    print("No cached Keeper session found – please authenticate.")
    user = input("Keeper email: ").strip()
    pwd  = getpass("Master password: ").strip()
    otp  = input("Two‑factor code (leave blank if none): ").strip() or None
    return user, pwd, otp

def _login():
    kp = params.KeeperParams()
    kp.config_filename = str(CONF_PATH)
    # try to load cached session/device
    api.load_settings(kp)

    if kp.session_token:
        try:
            api.sync_down(kp)
            return kp
        except api.CommunicationError:
            # token expired – fall through
            pass

    # interactive bootstrap unless env vars supplied
    user = os.getenv("KPR_USER")
    pwd  = os.getenv("KPR_PASS")
    otp  = os.getenv("KPR_2FA")
    if not (user and pwd):
        user, pwd, otp = _prompt_bootstrap()

    kp.user = user
    kp.password = pwd
    if otp:
        kp.mfa_token = otp

    api.login(kp)
    api.sync_down(kp)
    api.store_settings(kp)
    print(f"✓ Session cached – future runs will skip the login prompts (file: {CONF_PATH})")
    return kp

def get_client():
    """Public helper used by other modules."""
    return _login()
