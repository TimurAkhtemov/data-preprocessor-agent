from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from ..models import Severity
from ..visualization.schemas import ChartSpec


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AgentFinding(StrictModel):
    title: str = Field(min_length=1, max_length=250)
    severity: Severity
    summary: str = Field(
        min_length=1,
        max_length=2500,
        description="Concise interpretation consistent with every computed observation; acknowledge unanswered question parts and exceptions. Never infer subgroup patterns from overall statistics.",
    )
    evidence: list[str] = Field(
        min_length=1,
        max_length=12,
        description="Only observations supported by successful Python outputs. Preserve exact group labels, counts and denominators. Chart claims must match chart scope.",
    )
    recommended_action: str = Field(min_length=1, max_length=1500)
    confidence: float = Field(ge=0, le=1)
    related_columns: list[str] = Field(max_length=30)
    source: Literal["agent"] = "agent"


class RunPython(StrictModel):
    action: Literal["run_python"]
    reason: str = Field(min_length=1, max_length=500)
    code: str = Field(
        min_length=1,
        max_length=8000,
        description="Python statements only. df, pd, np, stats already exist. NO imports, print, lambda or apply. Assign output to result. Example: result = df.groupby('group')['value'].mean()",
    )


class RequestChart(StrictModel):
    action: Literal["request_chart"]
    reason: str = Field(min_length=1, max_length=500)
    chart: ChartSpec


class Finish(StrictModel):
    action: Literal["finish"]
    finding: AgentFinding


Action = Annotated[RunPython | RequestChart | Finish, Field(discriminator="action")]
ACTION_ADAPTER = TypeAdapter(Action)
ACTION_SCHEMA = ACTION_ADAPTER.json_schema()


class InvestigationRequest(StrictModel):
    question: str = Field(min_length=3, max_length=2000)
    finding_id: str | None = None
