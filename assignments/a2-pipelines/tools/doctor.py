"""`make doctor`: checks the things that actually break. GIVEN. Send me this output if setup fails."""

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import duckdb

DATA = Path(os.environ.get("PIPELINE_DATA_DIR", "data")).resolve()
REPO = Path(__file__).resolve().parent.parent


def main() -> int:
    ok = True

    def check(name, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  {'ok  ' if passed else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")

    print(f"python {platform.python_version()}  duckdb {duckdb.__version__}  {platform.system()} {platform.machine()}")
    print(f"repo   {REPO}")
    print(f"data   {DATA}  ({'inside the container' if os.environ.get('IN_PIPELINE_CONTAINER') else 'native'})")

    check("python is 3.13", sys.version_info[:2] == (3, 13), platform.python_version())
    check("duckdb is the pinned version", duckdb.__version__.startswith("1.5."), duckdb.__version__)

    DATA.mkdir(parents=True, exist_ok=True)
    probe = DATA / "_doctor"
    shutil.rmtree(probe, ignore_errors=True)
    try:
        probe.mkdir()
        (probe / "a").mkdir(); (probe / "a" / "f.txt").write_text("x")
        check("data folder is writable", True)
        os.replace(probe / "a", probe / "b")
        check("a folder can be renamed inside the data folder", (probe / "b" / "f.txt").exists())
        con = duckdb.connect()
        con.execute(f"COPY (SELECT DATE '2026-01-01' AS dt, 1 AS x) TO '{probe}/p' (FORMAT parquet, PARTITION_BY (dt))")
        n = con.execute(f"SELECT count(*) FROM read_parquet('{probe}/p/*/*.parquet', hive_partitioning = true)").fetchone()[0]
        check("duckdb can write and read a partitioned table there", n == 1)
    except Exception as e:
        check("data folder works", False, f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(probe, ignore_errors=True)

    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True, timeout=5)
        sha = sha.stdout.strip() if sha.returncode == 0 else ""
    except Exception:
        sha = ""
    if sha:
        print(f"  ok    git can read this repo (the manifest records the commit)  {sha}")
    else:
        print('  note  git is not visible from here, so run manifests will say git_sha "unknown".')
        print("        That is expected inside the container: the repo's .git sits above the mounted folder.")

    check("make is available", shutil.which("make") is not None)
    has_events = (DATA / "events" / "orders").exists()
    print(f"  {'ok  ' if has_events else 'note'}  events {'are generated' if has_events else 'not generated yet: run `make data` next'}")

    print("\nall checks passed" if ok else "\nSOMETHING FAILED. Copy everything above into an email to me.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
