from __future__ import annotations

import json
from uuid import uuid4

from app.domain.contracts import Evidence, Incident, Recommendation, RuntimeMode
from app.decision.contracts import DecisionResult
from app.integrations.coco import CocoCliClient, CocoCliError
from app.knowledge.services import KnowledgeMatch, KnowledgeRepository, RecommendationService


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


class CocoDecisionAdapter:
    def __init__(
        self,
        client: CocoCliClient,
        knowledge_repository: KnowledgeRepository,
        fallback: FixtureDecisionAdapter,
    ) -> None:
        self.client = client
        self.knowledge_repository = knowledge_repository
        self.fallback = fallback

    def decide(self, incident: Incident, evidence: list[Evidence]) -> DecisionResult:
        try:
            matches = self.knowledge_repository.search(f"{incident.summary} schema drift recovery", limit=3)
            value = self.client.prompt_json(
                self._prompt(incident, evidence, matches),
                required_keys={
                    "cause",
                    "confidence_band",
                    "evidence_ids",
                    "runbook_ids",
                    "recommended_action",
                    "uncertainty",
                },
            )
            recommendation = self._recommendation(incident, evidence, value, {match.document_id for match in matches})
            return DecisionResult(
                schema_version="decision_result.v1",
                recommendation=recommendation,
                adapter_mode=RuntimeMode.LIVE,
            )
        except (CocoCliError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            fallback_result = self.fallback.decide(incident, evidence)
            return fallback_result.model_copy(
                update={
                    "fallback_reason": f"CoCo decision unavailable ({type(error).__name__}); deterministic fixture fallback selected.",
                }
            )

    @staticmethod
    def _recommendation(incident: Incident, evidence: list[Evidence], value: dict, available_runbooks: set[str]) -> Recommendation:
        evidence_ids = [str(item) for item in value["evidence_ids"]]
        runbook_ids = [str(item) for item in value["runbook_ids"]]
        known_evidence = {item.id for item in evidence}
        if not set(evidence_ids).issubset(known_evidence):
            raise ValueError("CoCo cited unavailable evidence")
        if not set(runbook_ids).issubset(available_runbooks):
            raise ValueError("CoCo cited an unavailable runbook")
        return Recommendation(
            schema_version="recommendation.v1",
            id=f"rec-coco-{uuid4().hex}",
            incident_id=incident.id,
            cause=str(value["cause"]),
            confidence_band=value["confidence_band"],
            evidence_ids=evidence_ids,
            runbook_ids=runbook_ids,
            recommended_action=str(value["recommended_action"]),
            uncertainty=str(value["uncertainty"]),
            mode=incident.mode,
        )

    @staticmethod
    def _prompt(incident: Incident, evidence: list[Evidence], matches: list[KnowledgeMatch]) -> str:
        evidence_context = json.dumps(
            [{"id": item.id, "source": item.source.value, "summary": item.summary, "payload": item.sanitized_payload} for item in evidence],
            sort_keys=True,
        )
        runbook_context = json.dumps(
            [{"id": item.document_id, "title": item.title, "excerpt": item.excerpt} for item in matches],
            sort_keys=True,
        )
        return f"""You are the PipelinePilot decision skill. Analyze this sanitized incident using only the supplied evidence and retrieved runbooks.
Do not invent citations. Do not execute tools or recovery. Return exactly one JSON object with these keys:
{{"cause": "root cause", "confidence_band": "low|medium|high", "evidence_ids": ["existing evidence IDs"], "runbook_ids": ["existing runbook IDs"], "recommended_action": "controlled action", "uncertainty": "what remains uncertain"}}
Incident: {incident.id} / {incident.pipeline_name} / {incident.run_id}
Evidence: {evidence_context}
Runbooks: {runbook_context}
"""
