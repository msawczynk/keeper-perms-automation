import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = BASE_DIR / "perms" / "template.csv"

# comma‑separated list of team columns that appear after the fixed headers
TEAM_CODES = os.getenv("TEAM_CODES", "TBE-KT,Remoteservice").split(",")

# Keeper folder UIDs – override in production
META_FOLDER_UID = os.getenv("META_FOLDER_UID", "<metadata_folder_uid>")
LOG_FOLDER_UID  = os.getenv("LOG_FOLDER_UID", "<log_folder_uid>")

# operational behaviour
IMMUTABLE_RECORDS = bool(int(os.getenv("IMMUTABLE_RECORDS", "1")))
