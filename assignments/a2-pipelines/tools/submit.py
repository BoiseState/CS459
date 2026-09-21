"""`make submit`: build submission.zip for Canvas. GIVEN.

Includes your code. Leaves out data/, caches, and virtual envs.
"""

import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"data", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules"}
SKIP_FILES = {"submission.zip", ".DS_Store"}

out = REPO / "submission.zip"
n = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(REPO.rglob("*")):
        rel = p.relative_to(REPO)
        if any(part in SKIP_DIRS for part in rel.parts) or rel.name in SKIP_FILES or not p.is_file():
            continue
        z.write(p, str(rel)); n += 1

print(f"wrote {out.name}: {n} files, {out.stat().st_size / 1024:.0f} KB")
print("Upload submission.zip and your PDF to Canvas.")
