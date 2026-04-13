import csv
import math
from collections import Counter
from pathlib import Path

DATA_PATH = Path("data") / "samples.csv"

# Your schema: timestamp,label + 21 landmarks * (x,y,z) = 63 numbers
EXPECTED_COLS = 2 + (21 * 3)


def is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except Exception:
        return False


def validate_row(row, line_num: int, errors: list):
    if len(row) != EXPECTED_COLS:
        errors.append(f"Line {line_num}: wrong column count {len(row)} (expected {EXPECTED_COLS})")
        return None

    ts = row[0].strip()
    label = row[1].strip()

    if not ts:
        errors.append(f"Line {line_num}: missing timestamp")
    if not label:
        errors.append(f"Line {line_num}: missing label")

    # Validate numeric landmark values
    for i, val in enumerate(row[2:], start=2):
        v = val.strip()
        if v == "":
            errors.append(f"Line {line_num}: empty numeric value at column {i+1}")
            continue
        if not is_number(v):
            errors.append(f"Line {line_num}: non-numeric value '{v}' at column {i+1}")
            continue
        num = float(v)
        if math.isnan(num) or math.isinf(num):
            errors.append(f"Line {line_num}: NaN/Inf at column {i+1}")

    return label if label else None


def main():
    if not DATA_PATH.exists():
        print(f"FAIL: file not found: {DATA_PATH} ❌")
        print("Make sure you recorded samples first (R + labels) to create data/samples.csv")
        raise SystemExit(1)

    errors = []
    label_counts = Counter()
    total_rows = 0
    empty_rows = 0

    with DATA_PATH.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)

        for line_num, row in enumerate(reader, start=1):
            if not row or all(cell.strip() == "" for cell in row):
                errors.append(f"Line {line_num}: Empty row found")
                empty_rows += 1
                continue

            # If a header exists, skip it safely
            if line_num == 1 and row and row[0].lower().strip() in ("timestamp", "time"):
                continue

            total_rows += 1
            label = validate_row(row, line_num, errors)
            if label:
                label_counts[label] += 1

    print("=" * 60)
    print("DATASET VALIDATION REPORT")
    print("=" * 60)
    print(f"File: {DATA_PATH}")
    print(f"Expected columns per row: {EXPECTED_COLS}")
    print(f"Rows read (non-empty): {total_rows}")
    print(f"Empty rows skipped: {empty_rows}")
    print("-" * 60)

    if label_counts:
        print("Label counts:")
        for k, v in label_counts.most_common():
            print(f"  {k}: {v}")
        if len(label_counts) == 1:
            print("WARNING: Only one label exists in the dataset! Try to collect more classes.")
    else:
        print("Label counts: (none)")

    print("-" * 60)

    if errors:
        print(f"FAIL: Found {len(errors)} issues ❌")
        # Print first 25 errors to avoid huge spam
        for e in errors[:25]:
            print(" -", e)
        if len(errors) > 25:
            print(f" ... plus {len(errors) - 25} more")
        raise SystemExit(1)
    else:
        print("PASS: Dataset looks valid ✅")
        raise SystemExit(0)

if __name__ == "__main__":
    main()
