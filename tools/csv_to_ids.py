"""
Convert a CSV export to an ID list for preparation.

Usage:
  python -m tools.csv_to_ids --csv export.csv --column order_number --out ids.txt
  python -m tools.csv_to_ids --csv export.csv --column ticket_number --out ids.txt
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="CSV file path")
    ap.add_argument("--column", required=True, help="Column name to extract (e.g., order_number or ticket_number)")
    ap.add_argument("--out", required=True, help="Output file path")
    args = ap.parse_args()

    out = Path(args.out)
    rows = []
    with open(args.csv, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            v = (row.get(args.column) or "").strip()
            if v:
                rows.append(v)

    out.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} IDs to {out}")


if __name__ == "__main__":
    main()
