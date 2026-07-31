from __future__ import annotations

from app.domain.contracts import Evidence, Incident, RuntimeMode
from app.decision.contracts import DecisionResult
from app.knowledge.services import RecommendationService


class FixtureDecisionAdapter:
    def __init__(self, recommendation_service: RecommendationService) -> None:
        self.recommendation_service = recommendation_service

    def decide(self, incident: Incident, evidence: list[Evidence]) -> DecisionResult:
        return DecisionResult(
            schema_version="decision_result.v1",
            recommendation=self.recommendation_service.recommend(incident, evidence),
            adapter_mode=RuntimeMode.FIXTURE,
            fallback_reason="No live CoCo adapter is configured; deterministic fixture recommendation selected.",
        )
