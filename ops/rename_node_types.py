"""Canvas node types were `zpf/<kind>` until 2026-10-13 and are `phantra/<kind>`.

The type is stored inside every saved graph (`workflows.graph_json`, and the
node states beside it), so a graph saved before the rename names types the
runner no longer knows. This rewrites them in place. Report by default;
--write to act, in one transaction. Re-runnable: a second run finds nothing.

    set -a && source .env && set +a
    venv/bin/python -m ops.rename_node_types [--write]
"""
import os
import sys

import psycopg

OLD, NEW = '"zpf/', '"phantra/'
COLUMNS = (("workflows", "graph_json"), ("workflows", "states_json"))


def main(argv: list[str]) -> int:
    write = "--write" in argv
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL is not set: export it from .env first", file=sys.stderr)
        return 2
    with psycopg.connect(dsn) as conn:
        if not write:
            conn.execute("SET TRANSACTION READ ONLY")
        for table, column in COLUMNS:
            n = conn.execute(
                f'SELECT count(*) FROM public."{table}" WHERE "{column}"::text LIKE %s',
                (f"%{OLD}%",)).fetchone()[0]
            print(f"{table}.{column}: {n} row(s) name a zpf/ node type")
            if write and n:
                conn.execute(
                    f'UPDATE public."{table}" SET "{column}" = replace("{column}"::text, %s, %s)'
                    f' WHERE "{column}"::text LIKE %s', (OLD, NEW, f"%{OLD}%"))
        if write:
            conn.commit()
            print("written")
        else:
            print("report only: pass --write to rewrite them")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
