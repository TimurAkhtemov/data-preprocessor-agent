"""Independent profiler and chart regression checks against the PRD."""

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from dataset_investigator.config import Settings
from dataset_investigator.data.loader import DatasetError, load_dataset
from dataset_investigator.data.profiler import profile_dataset
from dataset_investigator.visualization.schemas import ChartSpec
from dataset_investigator.visualization.validation import build_chart


def profile(frame, **settings):
    return profile_dataset(frame, "review.csv", Settings(_env_file=None, **settings))


@pytest.mark.parametrize("stored_as_datetime", [False, True])
def test_centuries_apart_dates_have_a_span_without_overflow(stored_as_datetime):
    values = ["1700-01-01", "2200-01-01"]
    if stored_as_datetime:
        values = pd.to_datetime(values)
    result = profile(pd.DataFrame({"date": values})).columns[0]
    expected = (
        datetime(2200, 1, 1, tzinfo=timezone.utc) - datetime(1700, 1, 1, tzinfo=timezone.utc)
    ).days
    assert result.inferred_type == "datetime"
    assert result.datetime_stats.span_days == expected
    assert result.datetime_stats.parsed_count == 2


def test_chart_keeps_null_and_literal_missing_label_separate():
    frame = pd.DataFrame({"x": [1, 2, 3], "source": [None, "(missing)", "A"]})
    chart = build_chart(
        ChartSpec(type="histogram", x="x", color="source", title="Sources"),
        frame,
        profile(frame),
    )
    assert len(chart["series"]) == 3
    assert sorted(sum(series["y"]) for series in chart["series"]) == [1, 1, 1]
    assert len({series["name"] for series in chart["series"]}) == 3


def test_coalesced_line_means_are_weighted_by_observations():
    # The first adjacent bin combines one zero with one hundred 100s.
    frame = pd.DataFrame(
        {
            "x": list(range(1000)) + [1] * 99,
            "y": [0, 100] + [0] * 998 + [100] * 99,
        }
    )
    chart = build_chart(
        ChartSpec(type="line", x="x", y="y", title="Mean by position"),
        frame,
        profile(frame),
    )
    assert len(chart["series"][0]["y"]) == 500
    assert chart["series"][0]["y"][0] == pytest.approx(10000 / 101)


def test_csv_nul_bytes_are_not_silently_truncated(tmp_path):
    path = tmp_path / "nul.csv"
    path.write_bytes(b"label,value\nhello\x00discarded,1\n")
    with pytest.raises(DatasetError):
        load_dataset(path, ".csv")


def test_sampling_preserves_exact_counts_and_marks_distribution_findings():
    frame = pd.DataFrame({"state": ["NY", "ny", "NY ", None] * 100})
    result = profile(frame, large_dataset_row_threshold=200, profile_sample_rows=100)
    assert result.sampled and result.sample_size == 100
    assert result.row_count == 400
    assert result.missing_cells == 100
    assert result.duplicate_rows == 396
    assert result.columns[0].unique_count == 3
    categories = {finding.category: finding for finding in result.findings}
    assert categories["duplicates"].evidence["basis"] == "Full dataset"
    assert categories["missingness"].evidence["basis"] == "Full dataset"
    assert "100 rows" in categories["categorical_consistency"].evidence["basis"]
    chart = build_chart(ChartSpec(type="missingness", title="Missing values"), frame, result)
    assert not chart["sampled"]
    assert chart["series"][0]["x"] == [25]
    assert "sample" not in chart["note"].lower()


def test_nonfinite_only_numeric_column_and_chart_are_json_safe():
    frame = pd.DataFrame({"x": [np.inf, -np.inf, np.nan]})
    result = profile(frame)
    stats = result.columns[0].numeric_stats
    assert stats.count == 0 and stats.non_finite_count == 2
    assert stats.min is None and stats.mean is None
    chart = build_chart(ChartSpec(type="histogram", x="x", title="All nonfinite"), frame, result)
    json.dumps(result.model_dump(), allow_nan=False)
    json.dumps(chart, allow_nan=False)
    assert chart["series"][0]["x"] == []


def test_shared_histogram_bins_conserve_group_counts_without_mutation():
    frame = pd.DataFrame(
        {"value": [1, 2, 3, 4, 100, None], "source": ["A", "A", "B", "B", "B", "A"]}
    )
    original = frame.copy(deep=True)
    chart = build_chart(
        ChartSpec(type="histogram", x="value", color="source", title="Distribution"),
        frame,
        profile(frame),
    )
    assert chart["series"][0]["x"] == chart["series"][1]["x"]
    assert {series["name"]: sum(series["y"]) for series in chart["series"]} == {
        "A": 2,
        "B": 3,
    }
    pd.testing.assert_frame_equal(frame, original)


def test_nested_parquet_is_rejected_with_useful_error(tmp_path):
    path = tmp_path / "nested.parquet"
    pq.write_table(pa.table({"items": [[1, 2], [3]]}), path)
    with pytest.raises(DatasetError, match="flat tabular Parquet") as error:
        load_dataset(path, ".parquet")
    assert error.value.code == "UNSUPPORTED_COLUMNS"


@pytest.mark.parametrize("content", [b"a,b\n1\n", b",b\n1,2\n", b"a,b\n1,2,3\n"])
def test_bad_csv_header_and_ragged_rows_are_rejected(tmp_path, content):
    path = tmp_path / "bad.csv"
    path.write_bytes(content)
    with pytest.raises(DatasetError):
        load_dataset(path, ".csv")


def test_profile_and_charts_preserve_uploaded_bytes_and_dataframe(tmp_path):
    path = tmp_path / "immutable.csv"
    content = b"value,source\n1,A\n2,A\n3,B\n999,B\n"
    path.write_bytes(content)
    frame = load_dataset(path, ".csv")
    original = frame.copy(deep=True)
    result = profile(frame)
    for chart_type in ["histogram", "box", "bar"]:
        build_chart(ChartSpec(type=chart_type, x="value", title="Test"), frame, result)
    assert path.read_bytes() == content
    pd.testing.assert_frame_equal(frame, original)
