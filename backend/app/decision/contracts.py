from __future__ import annotations

from typing import Literal, Protocol

from app.domain.contracts import Evidence, Incident, Recommendation, RuntimeMode, StrictContract


class DecisionResult(StrictContract):
    schema_version: Literal["decision_result.v1"]
    recommendation: Recommendation
    adapter_mode: RuntimeMode
    fallback_reason: str | None = None


class DecisionAdapter(Protocol):
    def decide(self, incident: Incident, evidence: list[Evidence]) -> DecisionResult: ...
