"""Explicit, bounded download of three public evaluation fixtures; never used by the app."""

import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "examples" / "evaluation"
SOURCES = [
    {
        "id": "iris",
        "url": "https://archive.ics.uci.edu/ml/machine-learning-databases/iris/iris.data",
        "source": "https://archive.ics.uci.edu/dataset/53/iris",
        "attribution": "Fisher, R. (1936). Iris. UCI Machine Learning Repository. DOI: 10.24432/C56C76.",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "raw_file": "iris.data",
        "change": "Added descriptive column headers; omitted the trailing blank record. No corrections to original values.",
        "rows": 150,
        "columns": 5,
    },
    {
        "id": "penguins",
        "url": "https://raw.githubusercontent.com/allisonhorst/palmerpenguins/main/inst/extdata/penguins.csv",
        "source": "https://allisonhorst.github.io/palmerpenguins/",
        "attribution": "Palmer Station LTER data collected by Kristen Gorman and colleagues; palmerpenguins package by Allison Horst, Alison Hill and Kristen Gorman (2020). Gorman et al. (2014), PLOS ONE 9(3): e90081. DOI: 10.1371/journal.pone.0090081.",
        "license": "CC0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "raw_file": "penguins.csv",
        "change": "None. Prepared CSV is an exact copy of the package's simplified dataset.",
        "rows": 344,
        "columns": 8,
    },
    {
        "id": "wine_red",
        "url": "https://archive.ics.uci.edu/ml/machine-learning-databases/wine-quality/winequality-red.csv",
        "source": "https://archive.ics.uci.edu/dataset/186/wine+quality",
        "attribution": "Cortez, P., Cerdeira, A., Almeida, F., Matos, T., & Reis, J. (2009). Wine Quality. UCI Machine Learning Repository. DOI: 10.24432/C56S3T.",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "raw_file": "winequality-red.csv",
        "change": "Re-serialized semicolon-separated records as comma-separated CSV for the app's standard CSV loader. Headers and cell values unchanged.",
        "rows": 1599,
        "columns": 12,
    },
]


def main():
    (DEST / "raw").mkdir(parents=True, exist_ok=True)
    (DEST / "prepared").mkdir(parents=True, exist_ok=True)
    previous_path = DEST / "sources.json"
    previous = (
        {s["id"]: s for s in json.loads(previous_path.read_text())["datasets"]}
        if previous_path.exists()
        else {}
    )
    manifest = []
    with httpx.Client(timeout=30, follow_redirects=True, trust_env=False) as client:
        for source in SOURCES:
            data = bytearray()
            with client.stream("GET", source["url"]) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes(8192):
                    data.extend(chunk)
                    if len(data) > 500_000:
                        raise ValueError("Download exceeds the 500 KB per-source evaluation limit.")
            digest = hashlib.sha256(data).hexdigest()
            if source["id"] in previous and digest != previous[source["id"]]["raw_sha256"]:
                raise ValueError(
                    f"Upstream bytes changed for {source['id']}; review the source before updating the pinned fixture."
                )
            (DEST / "raw" / source["raw_file"]).write_bytes(data)
            text = bytes(data).decode("utf-8")
            records = list(
                csv.reader(
                    io.StringIO(text),
                    delimiter=";" if source["id"] == "wine_red" else ",",
                )
            )
            records = [row for row in records if row]
            if source["id"] == "iris":
                records.insert(
                    0,
                    [
                        "sepal_length_cm",
                        "sepal_width_cm",
                        "petal_length_cm",
                        "petal_width_cm",
                        "species",
                    ],
                )
            assert len(records) - 1 == source["rows"] and len(records[0]) == source["columns"]
            prepared = DEST / "prepared" / (source["id"] + ".csv")
            if source["id"] == "penguins":
                prepared.write_bytes(data)
            else:
                with prepared.open("w", newline="") as stream:
                    csv.writer(stream).writerows(records)
            manifest.append(
                {
                    **source,
                    "raw_bytes": len(data),
                    "raw_sha256": digest,
                    "prepared_sha256": hashlib.sha256(prepared.read_bytes()).hexdigest(),
                }
            )
            print(f"{source['id']}: {len(data):,} bytes, {source['rows']} × {source['columns']}")
    previous_path.write_text(
        json.dumps(
            {
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "datasets": manifest,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
