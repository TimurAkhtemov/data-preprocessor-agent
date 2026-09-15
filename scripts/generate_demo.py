"""Reproduce the synthetic fixture; no external data or network required."""

import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path

rng = random.Random(42)
rows = []
for i in range(1200):
    source = rng.choices(["A", "B", "C"], weights=[0.45, 0.35, 0.2])[0]
    rows.append(
        {
            "customer_id": f"CUS-{i + 1:05d}",
            "age": max(18, min(82, round(rng.gauss(43, 13)))),
            "state": rng.choice(["NY", "CA", "TX", "WA", "FL", "IL", "ny", "NY "]),
            "income": ""
            if rng.random() < (0.32 if source == "B" else 0.05)
            else round(math.exp(rng.gauss(10.8, 1.05)), 2),
            "source_system": source,
            "signup_date": ""
            if rng.random() < 0.045
            else str(date(2023, 1, 1) + timedelta(days=rng.randrange(1000))),
        }
    )
for i in range(13):
    rows[i].update(age=999, source_system="B")
rows[13].update(age=222, source_system="A")
rows[50]["income"] = 9_500_000
rows += [dict(row) for row in rows[100:112]]
path = Path(__file__).resolve().parents[1] / "examples" / "suspicious_customers.csv"
with path.open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print(f"Wrote {len(rows):,} rows to {path}")
