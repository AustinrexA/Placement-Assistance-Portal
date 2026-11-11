import sys
from collectors.csv_importer import import_csv

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/import_csv.py path\\to\\jobs.csv")
        raise SystemExit(2)
    try:
        print(import_csv(sys.argv[1]))
    except Exception as exc:
        print(f"Import failed: {exc}")
        raise SystemExit(1)
