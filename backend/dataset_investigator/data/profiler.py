import logging
import math
import re
import time
import warnings

import numpy as np
import pandas as pd
from pandas.api import types as ptypes

from ..config import Settings
from ..models import CategoricalStats, ColumnProfile, DatasetProfile, DatetimeStats, NumericStats
from .heuristics import detect_findings

log = logging.getLogger(__name__)


def scalar(value):
    if isinstance(value, (np.integer, np.bool_)):
        return value.item()
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(value) else None
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return str(value)
    return value if isinstance(value, (str, int, bool)) else str(value)[:200]


def to_dates(series: pd.Series) -> pd.Series:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pd.to_datetime(series, errors="coerce", format="mixed", utc=True)


def infer_type(series: pd.Series, name: str, unique_ratio: float, rows: int) -> str:
    values = series.dropna()
    if values.empty:
        return "unknown"
    text = ptypes.is_object_dtype(series.dtype) or ptypes.is_string_dtype(series.dtype)
    id_name = bool(re.search(r"(^id$|_id$|^id_|uuid|_number$|_key$)", name.lower()))
    if rows >= 50 and unique_ratio >= 0.98 and id_name and not ptypes.is_float_dtype(series.dtype):
        return "identifier-like"
    if ptypes.is_bool_dtype(series.dtype):
        return "boolean"
    if ptypes.is_numeric_dtype(series.dtype):
        return "numeric"
    if ptypes.is_datetime64_any_dtype(series.dtype):
        return "datetime"
    if text:
        strings = values.astype(str).str.strip()
        if strings.str.lower().isin({"true", "false", "yes", "no"}).all():
            return "boolean"
        if pd.to_numeric(strings, errors="coerce").notna().mean() > 0.9:
            return "numeric"
        # Require date-like structure so arbitrary identifiers aren't parsed as timestamps.
        date_shape = (
            strings.str.contains(
                r"(?:\d{1,4}[-/]\d{1,2}[-/]\d{1,4}|\d{1,2}:\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[ ,.-]+\d)",
                regex=True,
            ).mean()
            > 0.9
        )
        if date_shape and to_dates(strings).notna().mean() > 0.9:
            return "datetime"
        if (
            rows >= 50
            and unique_ratio >= 0.98
            and strings.str.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}").mean() > 0.9
        ):
            return "identifier-like"
    return "categorical"


def numeric_stats(series: pd.Series) -> NumericStats:
    numbers = pd.to_numeric(series, errors="coerce").dropna()
    finite = numbers[np.isfinite(numbers)].astype(float)
    n = len(finite)
    q = finite.quantile([0.01, 0.25, 0.5, 0.75, 0.99])
    p01, q1, median, q3, p99 = map(float, q)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    le, ue = q1 - 3 * iqr, q3 + 3 * iqr
    outliers = int(((finite < lower) | (finite > upper)).sum())
    extreme = int(((finite < le) | (finite > ue)).sum())
    return NumericStats(
        count=n,
        min=scalar(finite.min()),
        max=scalar(finite.max()),
        mean=scalar(finite.mean()),
        median=scalar(median),
        std=scalar(finite.std()),
        q1=scalar(q1),
        q3=scalar(q3),
        iqr=scalar(iqr),
        p01=scalar(p01),
        p99=scalar(p99),
        skewness=scalar(finite.skew()),
        zero_count=int((finite == 0).sum()),
        negative_count=int((finite < 0).sum()),
        non_finite_count=len(numbers) - n,
        outlier_count=outliers,
        outlier_ratio=outliers / max(n, 1),
        extreme_outlier_count=extreme,
        extreme_outlier_ratio=extreme / max(n, 1),
        lower=scalar(lower),
        upper=scalar(upper),
        lower_extreme=scalar(le),
        upper_extreme=scalar(ue),
    )


def categorical_stats(series: pd.Series) -> CategoricalStats:
    strings = series.dropna().astype(str)
    counts = strings.value_counts()
    raw = pd.Series(strings.unique(), dtype="string")
    normalized = raw.str.strip().str.lower().str.replace(r"\s+", " ", regex=True)
    pairs = pd.DataFrame({"raw": raw, "normalized": normalized})
    collisions = pairs[pairs.normalized.duplicated(keep=False)]
    groups = []
    for key, group in collisions.groupby("normalized", sort=True):
        if len(groups) >= 10:
            break
        groups.append(
            {
                "normalized": str(key)[:200],
                "raw_values": group.raw.str.slice(0, 200).head(10).tolist(),
                "variant_count": len(group),
            }
        )
    return CategoricalStats(
        top_values=[{"value": str(k)[:200], "count": int(v)} for k, v in counts.head(10).items()],
        blank_string_count=int(strings.str.strip().eq("").sum()),
        average_length=float(strings.str.len().mean()) if len(strings) else 0,
        max_length=int(strings.str.len().max()) if len(strings) else 0,
        most_common_ratio=float(counts.iloc[0] / len(strings)) if len(strings) else 0,
        normalized_unique_count=int(normalized.nunique()),
        raw_unique_count=len(raw),
        normalization_collisions=groups,
    )


def profile_dataset(df: pd.DataFrame, file_name: str, settings: Settings) -> DatasetProfile:
    start = time.perf_counter()
    rows = len(df)
    sample = (
        df.sample(min(rows, settings.profile_sample_rows), random_state=42)
        if rows > settings.large_dataset_row_threshold
        else df
    )
    columns = []
    for name in df.columns:
        full, series = df[name], sample[name]
        non_null, unique = int(full.notna().sum()), int(full.nunique())
        ratio = unique / max(non_null, 1)
        kind = infer_type(series, name, ratio, rows)
        counts = full.value_counts()
        column = ColumnProfile(
            name=name,
            inferred_type=kind,
            pandas_dtype=str(full.dtype),
            non_null_count=non_null,
            missing_count=rows - non_null,
            missing_ratio=(rows - non_null) / rows,
            unique_count=unique,
            unique_ratio=ratio,
            sample_values=[scalar(v) for v in series.dropna().head(5)],
            distribution_count=len(series),
            most_common_ratio=int(counts.iloc[0]) / max(non_null, 1) if len(counts) else 0,
            stored_as_text=ptypes.is_object_dtype(full.dtype) or ptypes.is_string_dtype(full.dtype),
        )
        if kind == "numeric":
            column.numeric_stats = numeric_stats(series)
        if column.stored_as_text or kind in {"categorical", "boolean"}:
            column.categorical_stats = categorical_stats(series)
        if kind == "datetime":
            dates = to_dates(series).dropna()
            column.datetime_stats = DatetimeStats(
                earliest=str(dates.min()) if len(dates) else None,
                latest=str(dates.max()) if len(dates) else None,
                span_days=(
                    dates.max().to_pydatetime() - dates.min().to_pydatetime()
                ).total_seconds()
                / 86400
                if len(dates)
                else None,
                parsed_count=len(dates),
            )
        columns.append(column)
    duplicates = int(df.duplicated().sum())
    missing = sum(c.missing_count for c in columns)
    profile = DatasetProfile(
        file_name=file_name,
        row_count=rows,
        column_count=len(df.columns),
        memory_bytes=int(df.memory_usage(deep=True).sum()),
        duplicate_rows=duplicates,
        duplicate_ratio=duplicates / rows,
        missing_cells=missing,
        missing_ratio=missing / (rows * len(df.columns)),
        sampled=sample is not df,
        sample_size=len(sample) if sample is not df else None,
        columns=columns,
    )
    profile.findings = detect_findings(profile)
    profile.duration_seconds = round(time.perf_counter() - start, 3)
    log.info(
        "Profile completed: rows=%d columns=%d duration=%.3fs",
        rows,
        len(columns),
        profile.duration_seconds,
    )
    return profile
