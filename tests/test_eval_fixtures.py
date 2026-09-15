"""Offline integrity/profile checks; live Qwen evaluations are explicitly opt-in."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from dataset_investigator.config import Settings
from dataset_investigator.data.loader import load_dataset
from dataset_investigator.data.profiler import profile_dataset

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "examples/evaluation"
SOURCES = json.loads((DIRECTORY / "sources.json").read_text())["datasets"]


@pytest.mark.parametrize("source", SOURCES, ids=lambda source: source["id"])
def test_attributed_fixture_integrity_and_profile(source):
    raw = (DIRECTORY / "raw" / source["raw_file"]).read_bytes()
    prepared = DIRECTORY / "prepared" / (source["id"] + ".csv")
    assert hashlib.sha256(raw).hexdigest() == source["raw_sha256"]
    assert hashlib.sha256(prepared.read_bytes()).hexdigest() == source["prepared_sha256"]
    assert len(raw) < 500_000 and source["attribution"] and source["license_url"]
    df = load_dataset(prepared, ".csv")
    p = profile_dataset(df, prepared.name, Settings(_env_file=None))
    assert [p.row_count, p.column_count] == [source["rows"], source["columns"]]
    assert p.missing_cells == int(df.isna().sum().sum())
    assert p.duplicate_rows == int(df.duplicated().sum())
    assert p.sampled is False


def test_format_preparation_preserves_original_values():
    raw_wine = pd.read_csv(DIRECTORY / "raw/winequality-red.csv", sep=";")
    pd.testing.assert_frame_equal(raw_wine, pd.read_csv(DIRECTORY / "prepared/wine_red.csv"))
    assert (DIRECTORY / "raw/penguins.csv").read_bytes() == (
        DIRECTORY / "prepared/penguins.csv"
    ).read_bytes()
    iris = pd.read_csv(DIRECTORY / "raw/iris.data", header=None)
    prepared = pd.read_csv(DIRECTORY / "prepared/iris.csv", header=None, skiprows=1)
    pd.testing.assert_frame_equal(iris, prepared)
