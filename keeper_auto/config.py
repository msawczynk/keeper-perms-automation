
from pathlib import Path
import os

# CSV templates land here
TEMPLATE_PATH = Path(os.getenv("KPR_TEMPLATE", "perms") ).expanduser() / "template.csv"
