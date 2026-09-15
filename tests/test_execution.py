import json
import time

import numpy as np
import pandas as pd
import pytest

from dataset_investigator.config import Settings
from dataset_investigator.data.serialization import serialize_result
from dataset_investigator.execution.sandbox import execute_python
from dataset_investigator.execution.validator import CodeRejected, validate_code


@pytest.mark.parametrize(
    "code",
    [
        "import os\nresult = 1",
        "import subprocess\nresult = 1",
        "from pathlib import Path\nresult = 1",
        "result = open('/etc/passwd')",
        "result = __import__('os')",
        "result = df.__class__",
        "result = eval('1+1')",
        "result = pd.read_csv('/etc/passwd')",
        "result = df.to_pickle('/tmp/test')",
        "result = np.load('/tmp/test')",
        "result = pd.eval('1+1')",
        "result = df.query('x > 1')",
        "result = df.groupby('source').agg('to_pickle')",
        "method = df.to_dict\nresult = method()",
        "result = df.groupby('source').agg(method)",
        "result = getattr(df, 'to_csv')('/tmp/test')",
        "result = np.ctypeslib",
        "result = df._mgr",
        "result = pd.io",
        "result = df.plot()",
        "f = {'x': len}\nresult = f['x'](df)",
        "pd = df\nresult = pd.shape",
        "result = (lambda: 1)()",
    ],
)
def test_reject_dangerous_or_indirect_code(code):
    with pytest.raises(CodeRejected):
        validate_code(code)


@pytest.mark.parametrize(
    "code",
    [
        'result = df.groupby("category")["value"].mean()',
        'result = df["value"].quantile([0.01, 0.5, 0.99])',
        'result = pd.crosstab(df["state"], df["source_system"])',
        'result = df.assign(normalized=df["state"].str.strip().str.lower()).groupby("normalized")["state"].nunique()',
        'result = df.groupby("source").agg(total=("value", "sum"))',
    ],
)
def test_allow_analytical_examples(code):
    validate_code(code)


@pytest.mark.parametrize(
    "value",
    [
        1,
        3.2,
        np.int64(7),
        np.float64(np.nan),
        np.array([[1, 2], [3, 4]]),
        {"x": [1, 2]},
        ValueError("bad column"),
    ],
)
def test_serialization_basic(value):
    result = serialize_result(value)
    assert len(result) <= 12000
    assert json.loads(result) is not None


def test_serialization_truncation_and_index():
    df = pd.DataFrame(np.ones((100, 30)), columns=[f"c{i}" for i in range(30)])
    result = serialize_result(df)
    assert "100 rows × 30 columns" in result and "truncated" in result
    payload = json.loads(result.split("\n", 1)[1])
    assert len(payload["data"]) == 50 and len(payload["columns"]) == 20
    assert len(serialize_result("x" * 20000)) == 12000
    result = serialize_result(pd.Series([1, 2], index=["A", "B"], name="count"))
    assert '"index": ["A", "B"]' in result


@pytest.fixture
def snapshot(tmp_path):
    path = tmp_path / "snapshot.parquet"
    pd.DataFrame(
        {"value": [1, 2, 999], "source": ["A", "A", "B"], "state": ["NY", "ny", "NY "]}
    ).to_parquet(path, index=False)
    path.chmod(0o400)
    return path


async def test_worker_computes_and_preserves_snapshot(snapshot):
    before = snapshot.read_bytes()
    result = await execute_python(
        'df["value"] = 0\nresult = df["value"].sum()',
        snapshot,
        Settings(_env_file=None),
    )
    assert result["ok"], result
    assert result["summary"] == "0"
    result = await execute_python(
        'result = df.groupby("source")["value"].agg(["count", "median", "max"])',
        snapshot,
        Settings(_env_file=None),
    )
    assert result["ok"], result
    assert "999" in result["summary"]
    assert snapshot.read_bytes() == before


async def test_worker_crosstab_and_normalization(snapshot):
    for code in [
        'result = pd.crosstab(df["state"], df["source"])',
        'result = df.assign(normalized=df["state"].str.strip().str.lower()).groupby("normalized")["state"].nunique()',
    ]:
        result = await execute_python(code, snapshot, Settings(_env_file=None))
        assert result["ok"], result


async def test_worker_error_and_timeout(snapshot):
    error = await execute_python(
        'result = df["does_not_exist"]', snapshot, Settings(_env_file=None)
    )
    assert not error["ok"] and "Available columns" in error["error"]
    start = time.monotonic()
    result = await execute_python(
        "while True:\n    result = 1",
        snapshot,
        Settings(_env_file=None, agent_code_timeout_seconds=1),
    )
    assert not result["ok"] and "timed out" in result["error"]
    assert time.monotonic() - start < 2.5


def test_rejection_reports_all_common_model_protocol_errors():
    code = 'import pandas as pd\nvalue = df.groupby("source").agg(lambda x: len(x))\nprint(value)'
    with pytest.raises(CodeRejected) as error:
        validate_code(code)
    assert all(part in str(error.value) for part in ["imports", "Lambda", "print", "result"])


def test_nested_dataframe_results_preserve_evidence():
    output = serialize_result(
        {"groups": pd.DataFrame({"missing": [6, 5]}, index=["Adelie", "Gentoo"])}
    )
    value = json.loads(output)["groups"]
    assert value["data"] == [[6], [5]]
    assert value["index"] == ["Adelie", "Gentoo"]


async def test_worker_dataframe_to_dict_and_vectorized_missingness(snapshot):
    code = 'analysis = df.assign(missing=df["value"].isna())\nresult = analysis.groupby("source").agg(rows=("value", "size"), missing=("missing", "sum"), rate=("missing", "mean")).to_dict()'
    output = await execute_python(code, snapshot, Settings(_env_file=None))
    assert output["ok"], output
    assert json.loads(output["summary"])["rows"] == {"A": 2, "B": 1}
