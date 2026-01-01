import os
import csv
import math
import random
from datetime import datetime, timedelta
from typing import List, Tuple

import pandas as pd


def random_name(rng: random.Random) -> str:
    first = rng.choice([
        "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Chris", "Sam",
        "Jamie", "Lee", "Robin", "Avery", "Parker", "Quinn", "Drew",
    ])
    last = rng.choice([
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis",
        "Garcia", "Rodriguez", "Wilson", "Martinez", "Anderson", "Taylor",
    ])
    name = f"{first} {last}"
    # Random casing and whitespace noise
    if rng.random() < 0.25:
        name = name.upper()
    if rng.random() < 0.25:
        name = name.lower()
    if rng.random() < 0.25:
        name = f"  {name}  "
    return name


def random_email(name: str, rng: random.Random) -> str:
    providers = ["example.com", "mail.com", "sample.org", "test.net"]
    base = name.replace(" ", ".").strip().lower()
    email = f"{base}@{rng.choice(providers)}"
    # Noise: missing at, spaces, uppercase
    roll = rng.random()
    if roll < 0.05:
        email = email.replace("@", "")  # invalid
    elif roll < 0.10:
        email = email.replace(".", " ")  # spaces
    if rng.random() < 0.2:
        email = email.upper()
    if rng.random() < 0.2:
        email = f" {email} "
    return email


def random_date(rng: random.Random) -> str:
    start = datetime(2020, 1, 1)
    d = start + timedelta(days=rng.randint(0, 5 * 365))
    # Mixed formats
    fmt = rng.choice([
        "%Y-%m-%d",  # 2024-03-17
        "%d/%m/%Y",  # 17/03/2024
        "%m-%d-%Y",  # 03-17-2024
        "%Y/%m/%d",  # 2024/03/17
    ])
    s = d.strftime(fmt)
    # Occasional invalid month/day
    if rng.random() < 0.01:
        s = s.replace("-03-", "-13-") if "-03-" in s else s
    return s


def random_category(rng: random.Random) -> str:
    base = rng.choice(["Retail", "retail", "ONLINE", "Wholesale", "wholesale", "e-comm", "E-Commerce"])  # inconsistent labels
    if rng.random() < 0.2:
        base = f" {base} "
    return base


def random_score(rng: random.Random) -> str:
    # Mostly 0-100, some outliers, some strings
    roll = rng.random()
    if roll < 0.75:
        val = rng.randint(0, 100)
        return str(val) if rng.random() < 0.3 else val  # mixed type
    if roll < 0.85:
        return rng.choice(["NA", "", "null", "abc"])  # bad strings
    # Outliers
    return rng.randint(300, 5000)


def random_amount(rng: random.Random) -> str:
    amt = rng.uniform(5, 2000)
    # Mixed representation
    if rng.random() < 0.5:
        return f"${amt:,.2f}"  # with currency + commas
    if rng.random() < 0.2:
        return f" {amt:.0f} "  # integer string with spaces
    return round(amt, 2)


def generate_rows(n: int, seed: int) -> List[dict]:
    rng = random.Random(seed)
    rows = []
    for i in range(1, n + 1):
        name = random_name(rng)
        email = random_email(name, rng)
        date = random_date(rng)
        score = random_score(rng)
        amount = random_amount(rng)
        category = random_category(rng)

        row = {
            "id": i,
            "name": name,
            "email": email,
            "date": date,
            "score": score,
            "amount": amount,
            "category": category,
        }

        # Inject missing values
        for key in ["name", "email", "date", "score"]:
            if rng.random() < 0.03:
                row[key] = "" if rng.random() < 0.5 else None

        rows.append(row)

        # Sprinkle duplicates (about 1%)
        if rng.random() < 0.01:
            rows.append(row.copy())
    return rows


def write_csv(rows: List[dict], out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate synthetic CSV with data quality issues")
    parser.add_argument("--rows", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default="data/noisy_20k.csv")
    args = parser.parse_args()

    rows = generate_rows(args.rows, args.seed)
    write_csv(rows, args.out)

    # Quick summary to stdout
    df = pd.read_csv(args.out)
    print(f"Wrote {len(df):,} rows to {args.out}")
    print("Columns:", list(df.columns))
    print("Sample:\n", df.head(3).to_string(index=False))


if __name__ == "__main__":
    main() 