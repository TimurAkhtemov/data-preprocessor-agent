import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pandas as pd
import pytest

from dataset_investigator.agent.investigator import investigate
from dataset_investigator.agent.parser import parse_action
from dataset_investigator.agent.schemas import Finish, RequestChart, RunPython
from dataset_investigator.config import Settings
from dataset_investigator.data.profiler import profile_dataset

FINDING = {
    "title": "Source B has extreme observations",
    "severity": "medium",
    "summary": "Observed a source-specific pattern; its cause is unconfirmed.",
    "evidence": ["The maximum in source B is 999."],
    "recommended_action": "Inspect how B encodes unknown values.",
    "confidence": 0.8,
    "related_columns": ["value", "source"],
}
PYTHON = {
    "action": "run_python",
    "reason": "Compute maxima by source.",
    "code": 'result = df.groupby("source")["value"].max()',
}
CHART = {
    "action": "request_chart",
    "reason": "Compare the group distributions.",
    "chart": {
        "type": "histogram",
        "x": "value",
        "color": "source",
        "title": "Value by source",
    },
}
FINISH = {"action": "finish", "finding": FINDING}


@pytest.mark.parametrize(
    "value,kind", [(PYTHON, RunPython), (CHART, RequestChart), (FINISH, Finish)]
)
def test_parser_valid(value, kind):
    assert isinstance(parse_action(json.dumps(value)), kind)
    assert isinstance(parse_action("```json\n" + json.dumps(value) + "\n```"), kind)


@pytest.mark.parametrize(
    "value",
    [
        "bad json",
        '{"action":"shell"}',
        '{"action":"run_python","reason":"test"}',
        json.dumps({"action": "finish", "finding": {**FINDING, "confidence": 1.1}}),
        json.dumps(
            {
                "action": "run_python",
                "reason": "x",
                "code": "result=1",
                "thinking": "hidden",
            }
        ),
    ],
)
def test_parser_invalid(value):
    with pytest.raises(ValueError):
        parse_action(value)


@pytest.fixture
def session_state(tmp_path):
    df = pd.DataFrame({"value": [1, 2, 999], "source": ["A", "A", "B"]})
    snapshot = tmp_path / "data.parquet"
    df.to_parquet(snapshot)
    session = SimpleNamespace(
        df=df,
        snapshot=snapshot,
        profile=profile_dataset(df, "test.csv", Settings(_env_file=None)),
        active_id="test",
    )
    state = {
        "investigation_id": "test",
        "question": "Investigate values",
        "status": "running",
        "trace": [],
        "charts": [],
        "final_finding": None,
        "steps_remaining": 5,
        "error": None,
    }
    return session, state


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    async def chat(self, messages, finish_only=False):
        self.calls.append((list(messages), finish_only))
        value = next(self.responses)
        return value if isinstance(value, str) else json.dumps(value)


async def test_real_python_chart_finish_workflow(session_state):
    session, state = session_state
    client = FakeClient([PYTHON, CHART, FINISH])
    await investigate(state, session, client, Settings(_env_file=None))
    assert state["status"] == "completed", state
    assert len(state["trace"]) == 2 and len(state["charts"]) == 1
    assert "999" in state["trace"][0]["result_summary"]
    assert state["final_finding"]["source"] == "agent"
    assert session.active_id is None
    assert "999" in client.calls[1][0][-1]["content"]


async def test_five_actions_then_summary_only(session_state, monkeypatch):
    session, state = session_state
    monkeypatch.setattr(
        "dataset_investigator.agent.investigator.execute_python",
        AsyncMock(return_value={"ok": True, "summary": "999"}),
    )
    client = FakeClient([PYTHON] * 5 + [FINISH])
    await investigate(state, session, client, Settings(_env_file=None))
    assert state["status"] == "completed"
    assert len(state["trace"]) == 5 and state["steps_remaining"] == 0
    assert len(client.calls) == 6 and client.calls[-1][1]


async def test_forced_summary_rejects_another_tool(session_state, monkeypatch):
    session, state = session_state
    executor = AsyncMock(return_value={"ok": True, "summary": "999"})
    monkeypatch.setattr("dataset_investigator.agent.investigator.execute_python", executor)
    await investigate(state, session, FakeClient([PYTHON] * 6), Settings(_env_file=None))
    assert state["status"] == "failed" and executor.await_count == 5


async def test_one_repair_for_entire_investigation(session_state, monkeypatch):
    session, state = session_state
    monkeypatch.setattr(
        "dataset_investigator.agent.investigator.execute_python",
        AsyncMock(return_value={"ok": True, "summary": "999"}),
    )
    client = FakeClient(["bad", PYTHON, "bad again"])
    await investigate(state, session, client, Settings(_env_file=None))
    assert state["status"] == "failed" and len(client.calls) == 3
    assert state["error"]["code"] == "MALFORMED_MODEL_RESPONSE"


async def test_repair_failure_terminates(session_state):
    session, state = session_state
    client = FakeClient(["bad", "still bad"])
    await investigate(state, session, client, Settings(_env_file=None))
    assert state["status"] == "failed" and len(client.calls) == 2


async def test_three_execution_failures_stop(session_state, monkeypatch):
    session, state = session_state
    monkeypatch.setattr(
        "dataset_investigator.agent.investigator.execute_python",
        AsyncMock(return_value={"ok": False, "error": "Code rejected"}),
    )
    await investigate(state, session, FakeClient([PYTHON] * 3), Settings(_env_file=None))
    assert state["error"]["code"] == "EXECUTION_FAILURES" and len(state["trace"]) == 3


async def test_cannot_finish_without_computed_evidence(session_state):
    session, state = session_state
    await investigate(state, session, FakeClient([FINISH] * 5), Settings(_env_file=None))
    assert state["status"] == "failed" and state["final_finding"] is None
    assert state["error"]["code"] == "NO_EVIDENCE"


async def test_invalid_chart_is_returned_for_correction(session_state):
    session, state = session_state
    bad = {**CHART, "chart": {**CHART["chart"], "x": "missing_column"}}
    await investigate(
        state,
        session,
        FakeClient([bad, PYTHON, CHART, FINISH]),
        Settings(_env_file=None),
    )
    assert state["status"] == "completed"
    assert "Chart rejected" in state["trace"][0]["error"]
