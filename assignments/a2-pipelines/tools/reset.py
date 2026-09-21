"""`make reset`: delete everything under data/. GIVEN. Run `make data` afterward."""

import os
import shutil
from pathlib import Path

DATA = Path(os.environ.get("PIPELINE_DATA_DIR", "data")).resolve()
for child in DATA.iterdir() if DATA.exists() else []:
    shutil.rmtree(child) if child.is_dir() else child.unlink()
print(f"emptied {DATA}")
