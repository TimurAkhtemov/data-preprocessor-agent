import numpy as np
import pandas as pd
import pytest

from dataset_investigator.config import Settings
from dataset_investigator.data.loader import DatasetError, load_dataset
from dataset_investigator.data.profiler import profile_dataset


def profile(df, **kwargs):
    return profile_dataset(df, "test.csv", Settings(_env_file=None, **kwargs))


def test_exact_shape_missingness_and_duplicates():
    p = profile(pd.DataFrame({"a": [1, 1, None], "b": ["x", "x", "y"]}))
    assert (p.row_count, p.column_count, p.missing_cells, p.duplicate_rows) == (
        3,
        2,
        1,
        1,
    )
    assert p.missing_ratio == 1 / 6
    assert p.duplicate_ratio == 1 / 3
    assert p.columns[0].non_null_count == 2
    assert {f.category for f in p.findings} >= {"missingness", "duplicates", "constant"}


def test_numeric_statistics_and_infinite_values():
    p = profile(pd.DataFrame({"value": [-1, 0, 1, 2, 3, np.inf]}))
    n = p.columns[0].numeric_stats
    assert (n.min, n.max, n.mean, n.median, n.q1, n.q3, n.iqr) == (-1, 3, 1, 1, 0, 2, 2)
    assert (n.zero_count, n.negative_count, n.non_finite_count) == (1, 1, 1)
    assert n.std == pytest.approx(np.std([-1, 0, 1, 2, 3], ddof=1))
    assert "Infinity" not in p.model_dump_json()


def test_categorical_normalization_does_not_mutate():
    df = pd.DataFrame({"state": ["NY", "ny", "NY ", " New   York", "new york", "  ", None]})
    original = df.copy(deep=True)
    p = profile(df)
    c = p.columns[0].categorical_stats
    assert c.raw_unique_count == 6
    assert c.normalized_unique_count == 3
    assert c.blank_string_count == 1
    assert len(c.normalization_collisions) == 2
    pd.testing.assert_frame_equal(df, original)
    f = next(f for f in p.findings if f.category == "categorical_consistency")
    assert (
        f.id
        == next(
            f
            for f in profile(df).findings
            if f.category == f.category and f.category == "categorical_consistency"
        ).id
    )


def test_identifiers_not_continuous_measurements():
    p = profile(
        pd.DataFrame(
            {
                "customer_id": [f"C{i:04}" for i in range(100)],
                "temperature": np.linspace(1.1, 29.1, 100),
            }
        )
    )
    assert p.columns[0].inferred_type == "identifier-like"
    assert p.columns[1].inferred_type == "numeric"
    assert [f.columns for f in p.findings if f.category == "identifier"] == [["customer_id"]]


def test_constant_near_constant_and_all_null():
    p = profile(pd.DataFrame({"constant": [7] * 100, "near": [1] * 99 + [2], "null": [None] * 100}))
    assert p.columns[2].inferred_type == "unknown"
    assert {(f.category, f.columns[0]) for f in p.findings if f.columns} >= {
        ("constant", "constant"),
        ("constant", "null"),
        ("near_constant", "near"),
    }


def test_numeric_datetime_boolean_text_detection():
    p = profile(
        pd.DataFrame(
            {
                "amount": [str(i) for i in range(99)] + ["unknown"],
                "date": ["2025-01-01"] * 99 + ["bad"],
                "bool": ["true", "false"] * 50,
            }
        )
    )
    assert [c.inferred_type for c in p.columns] == ["numeric", "datetime", "boolean"]
    assert p.columns[1].datetime_stats.earliest.startswith("2025-01-01")
    assert len([f for f in p.findings if f.category == "type_mismatch"]) == 2


def test_skew_and_outliers_are_domain_agnostic():
    p = profile(pd.DataFrame({"measurement": list(range(100)) + [999] * 3}))
    categories = {f.category for f in p.findings}
    assert {"skew", "outliers"} <= categories
    assert p.columns[0].numeric_stats.extreme_outlier_count == 3


def test_sampling_is_deterministic_but_missingness_exact():
    df = pd.DataFrame({"x": list(range(250)) + [None] * 50})
    a = profile(df, large_dataset_row_threshold=200, profile_sample_rows=100)
    b = profile(df, large_dataset_row_threshold=200, profile_sample_rows=100)
    assert a.sampled and a.sample_size == 100
    assert a.missing_cells == 50 and a.row_count == 300
    assert a.columns[0].numeric_stats == b.columns[0].numeric_stats
    assert a.columns[0].distribution_count == 100


@pytest.mark.parametrize(
    "content,code",
    [
        (b"", "EMPTY_FILE"),
        (b"a,b\n", "EMPTY_DATASET"),
        (b"a,b\n1,2,3\n", "MALFORMED_CSV"),
        (b"a,a\n1,2\n", "INVALID_COLUMNS"),
        (b'a,b\n"unterminated,3', "PARSE_FAILED"),
    ],
)
def test_loader_errors(tmp_path, content, code):
    path = tmp_path / "test.csv"
    path.write_bytes(content)
    with pytest.raises(DatasetError) as exc:
        load_dataset(path, ".csv")
    assert exc.value.code == code


def test_csv_encodings_and_parquet(tmp_path):
    for encoding in ["utf-8", "utf-8-sig", "latin-1"]:
        path = tmp_path / "test.csv"
        path.write_bytes("name,age\nRené,42\n".encode(encoding))
        df = load_dataset(path, ".csv")
        assert df.iloc[0]["name"] == "René"
        assert df.columns[0] == "name"
    path = tmp_path / "test.parquet"
    df.to_parquet(path)
    pd.testing.assert_frame_equal(load_dataset(path, ".parquet"), df)
