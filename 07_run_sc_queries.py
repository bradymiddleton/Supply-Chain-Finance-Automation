"""
Middleton Finance Suite — Supply Chain Edition
Script 07: Run Supply Chain SQL Analysis Queries

Executes 06_sc_queries.sql against all three supply chain databases
and prints formatted results to console.

Usage:
    python 07_run_sc_queries.py

Prerequisites:
    Run 05_generate_sc_data.py first to build the databases.
"""

import sqlite3, re, os, pandas as pd

DB_DIR   = "sc_databases"
SQL_FILE = "06_sc_queries.sql"

pd.set_option("display.max_columns", 20)
pd.set_option("display.max_rows",    50)
pd.set_option("display.width",       120)
pd.set_option("display.float_format", "{:,.2f}".format)

DB_MAP = {
    "SECTION 5": f"{DB_DIR}/demand_planning.db",
    "SECTION 6": f"{DB_DIR}/inventory.db",
    "SECTION 7": f"{DB_DIR}/cogs_margin.db",
    "SECTION 8": None,
}

SECTION_8_DB = {
    "8A": f"{DB_DIR}/demand_planning.db",
    "8B": f"{DB_DIR}/inventory.db",
    "8C": f"{DB_DIR}/cogs_margin.db",
}

SECTION_LABELS = {
    "SECTION 5": "SECTION 5 — Demand Planning & Forecast Accuracy  [demand_planning.db]",
    "SECTION 6": "SECTION 6 — Inventory Health & Holding Cost       [inventory.db]",
    "SECTION 7": "SECTION 7 — COGS & Gross Margin Analysis          [cogs_margin.db]",
    "SECTION 8": "SECTION 8 — Cross-Database Snapshots              [all three DBs]",
}

def run_query(db_path, sql, label):
    if not os.path.exists(db_path):
        print(f"  ✗ Database not found: {db_path} — run 05_generate_sc_data.py first.")
        return
    try:
        conn = sqlite3.connect(db_path)
        df   = pd.read_sql(sql.strip(), conn)
        conn.close()
        print(f"\n{label}")
        print("─" * 72)
        print(df.to_string(index=False) if not df.empty else "  (no rows)")
    except Exception as e:
        print(f"  ✗ {label} — {e}")

def parse_sql(path):
    with open(path) as f: raw = f.read()
    pat = re.compile(r"--\s+(\d[A-Z])\.\s+(.+?)\n(.*?)(?=--\s+\d[A-Z]\.|-- ─|$)", re.DOTALL)
    queries = []
    for m in pat.finditer(raw):
        sql = re.sub(r"--[^\n]*", "", m.group(3)).strip()
        if sql:
            queries.append({"code": m.group(1), "label": f"Query {m.group(1)}: {m.group(2).strip()}",
                            "section": f"SECTION {m.group(1)[0]}", "sql": sql})
    return queries

def main():
    print("\n" + "="*72)
    print("  Middleton Finance Suite — Supply Chain SQL Runner")
    print("="*72)
    if not os.path.exists(SQL_FILE):
        print(f"\n✗ {SQL_FILE} not found."); return
    queries = parse_sql(SQL_FILE)
    print(f"\n  Found {len(queries)} queries across 4 sections.\n")
    current = None
    for q in queries:
        if q["section"] != current:
            current = q["section"]
            print(f"\n{'='*72}\n  {SECTION_LABELS.get(current, current)}\n{'='*72}")
        db = SECTION_8_DB.get(q["code"]) if q["section"]=="SECTION 8" else DB_MAP.get(q["section"])
        if db: run_query(db, q["sql"], q["label"])
    print(f"\n{'='*72}\n  All queries complete.\n{'='*72}\n")

if __name__ == "__main__":
    main()
