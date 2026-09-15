"""Bounded, JSON-safe tool output. Never repr an entire dataset or arbitrary object."""

import itertools
import json
import math
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

MAX_TEXT = 12_000
MAX_ROWS = 50
MAX_COLUMNS = 20


def safe_value(value, depth=0):
    if depth > 4:
        return "[nested value truncated]"
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, np.generic):
        return safe_value(value.item(), depth + 1)
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, (int, bool)):
        return value
    if isinstance(value, str):
        return value[:500] + ("… [truncated]" if len(value) > 500 else "")
    if isinstance(value, complex):
        return {"real": safe_value(value.real), "imag": safe_value(value.imag)}
    if isinstance(
        value, (pd.Timestamp, pd.Timedelta, pd.Interval, pd.Period, date, datetime, timedelta)
    ):
        return str(value)
    if isinstance(value, pd.Categorical):
        value = pd.Series(value)
    if isinstance(value, pd.Series):
        value = value.to_frame(name=str(value.name) if value.name is not None else "value")
    if isinstance(value, pd.DataFrame):
        rows, columns = value.shape
        head = value.iloc[:MAX_ROWS, :MAX_COLUMNS]
        return {
            "type": "DataFrame",
            "shape": [rows, columns],
            "columns": [str(c)[:200] for c in head.columns],
            "index": [safe_value(i, depth + 1) for i in head.index],
            "data": [
                [safe_value(v, depth + 1) for v in row]
                for row in head.itertuples(index=False, name=None)
            ],
            "truncated": rows > MAX_ROWS or columns > MAX_COLUMNS,
        }
    if isinstance(value, dict):
        result = {
            str(k)[:120]: safe_value(v, depth + 1) for k, v in itertools.islice(value.items(), 50)
        }
        if len(value) > 50:
            result["[truncated]"] = f"First 50 of {len(value)} entries"
        return result
    if isinstance(value, np.ndarray):
        return {
            "shape": list(value.shape),
            "values": safe_value(value.reshape(-1)[:50].tolist(), depth + 1),
            "truncated": value.size > 50,
        }
    if isinstance(value, (list, tuple, set)):
        result = [safe_value(v, depth + 1) for v in itertools.islice(value, 50)]
        if len(value) > 50:
            result.append(f"[First 50 of {len(value)} items]")
        return result
    if isinstance(value, Exception):
        return {"exception": type(value).__name__, "message": str(value)[:1000]}
    return f"[{type(value).__name__}; return a scalar, dict, list, Series or DataFrame]"


def serialize_result(value) -> str:
    if isinstance(value, pd.Categorical):
        value = pd.Series(value)
    if isinstance(value, pd.Series):
        value = value.to_frame(name=str(value.name) if value.name is not None else "value")
    if isinstance(value, pd.DataFrame):
        rows, columns = value.shape
        head = value.iloc[:MAX_ROWS, :MAX_COLUMNS]
        payload = {
            "type": "DataFrame",
            "shape": [rows, columns],
            "columns": [str(c)[:200] for c in head.columns],
            "index": [safe_value(i) for i in head.index],
            "data": [
                [safe_value(v) for v in row] for row in head.itertuples(index=False, name=None)
            ],
            "truncated": rows > MAX_ROWS or columns > MAX_COLUMNS,
        }
        prefix = f"DataFrame: {rows} rows × {columns} columns."
        if payload["truncated"]:
            prefix += f" Result truncated to first {min(rows, MAX_ROWS)} rows and {min(columns, MAX_COLUMNS)} columns."
        output = prefix + "\n" + json.dumps(payload, ensure_ascii=False, allow_nan=False)
    elif isinstance(value, str):
        output = value[: MAX_TEXT + 1]
    else:
        output = json.dumps(safe_value(value), ensure_ascii=False, allow_nan=False)
    if len(output) > MAX_TEXT:
        suffix = "\n[Output truncated at 12,000 characters]"
        output = output[: MAX_TEXT - len(suffix)] + suffix
    return output
