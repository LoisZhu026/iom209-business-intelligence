"""Prepare the local Bistro XLSX input from the group-stage enriched dataset."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "data" / "raw" / "the_bistro_data_final.xlsx"
REQUIRED_COLUMNS = {
    "Order ID",
    "Customer ID",
    "Order Date",
    "Category",
    "Item",
    "Price",
    "Quantity",
    "Order Total",
}


def read_source(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError("Source must be a CSV or Excel file.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the local sales input required by the IOM209 pipeline."
    )
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    data = read_source(args.source)
    missing = sorted(REQUIRED_COLUMNS.difference(data.columns))
    if missing:
        raise ValueError(f"Source is missing required columns: {', '.join(missing)}")
    if len(data) != 17_534:
        raise ValueError(f"Expected 17,534 rows, found {len(data):,}.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    data.to_excel(args.output, index=False)
    print(f"Prepared {len(data):,} rows at {args.output}")


if __name__ == "__main__":
    main()
