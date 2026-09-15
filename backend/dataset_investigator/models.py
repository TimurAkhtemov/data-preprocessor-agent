from typing import Any, Literal

from pydantic import BaseModel, Field

Severity = Literal["high", "medium", "low"]


class NumericStats(BaseModel):
    count: int
    min: float | None
    max: float | None
    mean: float | None
    median: float | None
    std: float | None
    q1: float | None
    q3: float | None
    iqr: float | None
    p01: float | None
    p99: float | None
    skewness: float | None
    zero_count: int
    negative_count: int
    non_finite_count: int
    outlier_count: int
    outlier_ratio: float
    extreme_outlier_count: int
    extreme_outlier_ratio: float
    lower: float | None
    upper: float | None
    lower_extreme: float | None
    upper_extreme: float | None


class CategoricalStats(BaseModel):
    top_values: list[dict[str, Any]]
    blank_string_count: int
    average_length: float
    max_length: int
    most_common_ratio: float
    normalized_unique_count: int
    raw_unique_count: int
    normalization_collisions: list[dict[str, Any]]


class DatetimeStats(BaseModel):
    earliest: str | None
    latest: str | None
    span_days: float | None
    parsed_count: int


class ColumnProfile(BaseModel):
    name: str
    inferred_type: str
    pandas_dtype: str
    non_null_count: int
    missing_count: int
    missing_ratio: float
    unique_count: int
    unique_ratio: float
    sample_values: list[Any]
    distribution_count: int
    most_common_ratio: float = 0
    stored_as_text: bool = False
    numeric_stats: NumericStats | None = None
    categorical_stats: CategoricalStats | None = None
    datetime_stats: DatetimeStats | None = None


class ProfilerFinding(BaseModel):
    id: str
    severity: Severity
    category: str
    title: str
    description: str
    columns: list[str]
    evidence: dict[str, Any]
    source: Literal["profiler"] = "profiler"


class DatasetProfile(BaseModel):
    file_name: str
    row_count: int
    column_count: int
    memory_bytes: int
    duplicate_rows: int
    duplicate_ratio: float
    missing_cells: int
    missing_ratio: float
    sampled: bool
    sample_size: int | None
    duration_seconds: float = 0
    columns: list[ColumnProfile]
    findings: list[ProfilerFinding] = Field(default_factory=list)
