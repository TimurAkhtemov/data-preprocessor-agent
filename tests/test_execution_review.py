"""Independent security and correctness checks for analytical Python execution."""

import asyncio
import json
import time

import numpy as np
import pandas as pd
import psutil
import pytest

from dataset_investigator.config import Settings
from dataset_investigator.data.serialization import (
    MAX_COLUMNS,
    MAX_ROWS,
    MAX_TEXT,
    serialize_result,
)
from dataset_investigator.execution.sandbox import execute_python
from dataset_investigator.execution.validator import CodeRejected, validate_code


@pytest.mark.parametrize(
    "code",
    [
        "import os\nresult = 1",
        "from pathlib import Path\nresult = 1",
        "result = open('probe.txt', 'w')",
        "result = pd.read_pickle('probe.pkl')",
        "result = df.__class__",
        "result = getattr(df, 'to_pickle')",
        "fn = {'read': pd.DataFrame}.get('read')\nresult = fn({'x': [1]})",
    ],
)
def test_validator_rejects_obvious_external_access_and_indirect_calls(code):
    with pytest.raises(CodeRejected):
        validate_code(code)


def test_validator_accepts_prd_style_analysis():
    validate_code(
        "result = (df.assign(clean=df['state'].str.strip().str.lower())"
        ".groupby('clean')['state'].nunique().sort_values(ascending=False).head(20))"
    )


def test_pivot_table_cannot_bypass_aggregation_allowlist_with_starred_arguments():
    code = "args = [['value'], None, None, 'to_pickle']\nresult = df.pivot_table(*args)"
    with pytest.raises(CodeRejected):
        validate_code(code)


@pytest.mark.parametrize(
    "value",
    [
        np.datetime64("2026-09-14"),
        np.timedelta64(3, "D"),
        np.complex128(1 + 2j),
    ],
)
def test_numpy_scalars_have_meaningful_json_safe_serialization(value):
    output = serialize_result(value)
    assert "return a scalar" not in output
    json.loads(output)


def test_exposed_cut_operation_preserves_interval_labels():
    output = serialize_result(pd.cut(pd.Series([1, 2, 3, 4]), bins=2))

    assert "return a scalar" not in output
    assert "(0.997, 2.5]" in output
    assert "(2.5, 4.0]" in output


def test_tabular_and_nested_outputs_are_strictly_bounded():
    frame = pd.DataFrame(
        np.full((MAX_ROWS + 10, MAX_COLUMNS + 5), "x" * 1_000),
        columns=[f"column_{number}" for number in range(MAX_COLUMNS + 5)],
    )
    tabular = serialize_result(frame)
    nested = serialize_result({"values": ["y" * 1_000] * 100})

    assert len(tabular) <= MAX_TEXT
    assert "60 rows × 25 columns" in tabular
    assert "Result truncated to first 50 rows and 20 columns" in tabular
    assert len(nested) <= MAX_TEXT
    assert nested.endswith("[Output truncated at 12,000 characters]")


@pytest.mark.asyncio
async def test_worker_mutation_is_confined_to_the_snapshot_copy(tmp_path):
    snapshot = tmp_path / "snapshot.parquet"
    original = pd.DataFrame({"value": [1, 2, 3], "group": ["A", "A", "B"]})
    original.to_parquet(snapshot, index=False)

    output = await execute_python(
        "df['value'] = 0\nresult = df['value'].sum()",
        snapshot,
        Settings(_env_file=None),
    )

    assert output == {"ok": True, "summary": "0"}
    pd.testing.assert_frame_equal(pd.read_parquet(snapshot), original)


@pytest.mark.asyncio
async def test_wall_clock_timeout_stops_nonterminating_code(tmp_path):
    snapshot = tmp_path / "snapshot.parquet"
    pd.DataFrame({"value": [1]}).to_parquet(snapshot, index=False)
    settings = Settings(_env_file=None, agent_code_timeout_seconds=2)

    started = time.monotonic()
    output = await execute_python("while True:\n    result = 1", snapshot, settings)

    assert output["ok"] is False
    assert "timed out after 2 seconds" in output["error"]
    assert time.monotonic() - started < 3


@pytest.mark.asyncio
async def test_cancelling_execution_reaps_the_worker(tmp_path, monkeypatch):
    snapshot = tmp_path / "snapshot.parquet"
    pd.DataFrame({"value": [1]}).to_parquet(snapshot, index=False)
    real_create_subprocess_exec = asyncio.create_subprocess_exec
    workers = []

    async def capture_worker(*args, **kwargs):
        worker = await real_create_subprocess_exec(*args, **kwargs)
        workers.append(worker)
        return worker

    monkeypatch.setattr(asyncio, "create_subprocess_exec", capture_worker)
    task = asyncio.create_task(
        execute_python("while True:\n    result = 1", snapshot, Settings(_env_file=None))
    )
    for _ in range(100):
        if workers:
            break
        await asyncio.sleep(0.01)
    assert workers

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    worker = workers[0]
    assert worker.returncode is not None
    assert not psutil.pid_exists(worker.pid)


@pytest.mark.asyncio
async def test_memory_limit_rejects_short_lived_peak_above_cap(tmp_path):
    snapshot = tmp_path / "snapshot.parquet"
    pd.DataFrame({"value": [1]}).to_parquet(snapshot, index=False)
    settings = Settings(_env_file=None, worker_memory_mb=320)

    output = await execute_python(
        "result = np.arange(50_000_000, dtype='float64')",
        snapshot,
        settings,
    )

    assert output["ok"] is False
    assert "memory limit" in output["error"] or "resource limit" in output["error"]
