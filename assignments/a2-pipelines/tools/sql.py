"""`make sql`: a small DuckDB prompt with the data folder ready to query. GIVEN.

    make sql                                   interactive
    make sql FILE=queries/partition_status.sql  run one file and print the result

Views available (each one is a file or folder under data/):
    runs, models, incident, aggs, orders, deliveries
End a statement with a semicolon. Type .quit to leave, .views to list the views.
"""

import sys
from pathlib import Path

import duckdb

from tests.common import VIEWS, con_with_views


def main() -> int:
    con = con_with_views()
    available = [v for v in VIEWS if con.execute(f"SELECT count(*) FROM duckdb_views() WHERE view_name = '{v}'").fetchone()[0]]

    if len(sys.argv) > 1:
        sql = Path(sys.argv[1]).read_text()
        try:
            con.sql(sql).show(max_rows=200)
        except duckdb.CatalogException as e:
            print(f"{e}\nviews on disk right now: {', '.join(available)}")
            return 1
        return 0

    print(__doc__.strip().splitlines()[0])
    print(f"views: {', '.join(available)}" + (f"   (not yet on disk: {', '.join(v for v in VIEWS if v not in available)})" if len(available) < len(VIEWS) else ""))
    buffer = ""
    while True:
        try:
            line = input("sql> " if not buffer else "...> ")
        except (EOFError, KeyboardInterrupt):
            print(); return 0
        if line.strip() in (".quit", ".exit", "exit", "quit"):
            return 0
        if line.strip() == ".views":
            print(", ".join(available)); continue
        buffer += line + "\n"
        if ";" in line:
            try:
                con.sql(buffer).show(max_rows=60)
            except Exception as e:
                print(f"{type(e).__name__}: {e}")
            buffer = ""


if __name__ == "__main__":
    sys.exit(main())
