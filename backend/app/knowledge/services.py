from __future__ import annotations

import json
from pathlib import Path
from typing import Literal
from uuid import uuid4

from app.domain.contracts import Evidence, Incident, Recommendation, StrictContract


class KnowledgeMatch(StrictContract):
    schema_version: Literal["knowledge_match.v1"]
    document_id: str
    title: str
    excerpt: str
    score: float


class PriorIncidentMatch(StrictContract):
    schema_version: Literal["prior_incident_match.v1"]
    document_id: str
    title: str
    excerpt: str
    score: float


class KnowledgeRepository:
    def __init__(self, runbooks_path: str | Path, incident_records_path: str | Path | None = None) -> None:
        self.runbooks_path = Path(runbooks_path)
        self.incident_records_path = Path(incident_records_path) if incident_records_path is not None else self.runbooks_path.parent / "incidents"

    def search(self, query: str, limit: int = 3) -> list[KnowledgeMatch]:
        terms = {term.lower() for term in query.split() if len(term) > 2}
        matches: list[KnowledgeMatch] = []
        for path in sorted(self.runbooks_path.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            score = sum(content.lower().count(term) for term in terms)
            if score:
                matches.append(KnowledgeMatch(
                    schema_version="knowledge_match.v1",
                document_id="runbook-schema-drift" if path.stem == "schema_drift_response" else path.stem.replace("_", "-"),
                    title=content.splitlines()[0].removeprefix("# ").strip(),
                    excerpt=content[:500].strip(),
                    score=float(score),
                ))
        return sorted(matches, key=lambda match: (-match.score, match.document_id))[:limit]

    def search_prior_incidents(self, query: str, limit: int = 3) -> list[PriorIncidentMatch]:
        terms = {term.lower() for term in query.split() if len(term) > 2}
        matches: list[PriorIncidentMatch] = []
        for path in sorted(self.incident_records_path.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            searchable = json.dumps(payload, sort_keys=True).lower()
            score = sum(searchable.count(term) for term in terms)
            if not score:
                continue
            excerpt = " ".join(
                str(payload.get(field, "")).strip()
                for field in ("summary", "root_cause", "impact", "resolution")
                if payload.get(field)
            )
            matches.append(PriorIncidentMatch(
                schema_version="prior_incident_match.v1",
                document_id=str(payload.get("document_id", path.stem)),
                title=str(payload.get("title", path.stem.replace("_", " "))),
                excerpt=excerpt[:700],
                score=float(score),
            ))
        return sorted(matches, key=lambda match: (-match.score, match.document_id))[:limit]


class RecommendationService:
    def __init__(self, recommendation_path: str | Path, knowledge_repository: KnowledgeRepository) -> None:
        self.recommendation_path = Path(recommendation_path)
        self.knowledge_repository = knowledge_repository

    def recommend(self, incident: Incident, evidence: list[Evidence]) -> Recommendation:
        payload = json.loads(self.recommendation_path.read_text(encoding="utf-8"))
        recommendation = Recommendation.model_validate(payload)
        if recommendation.incident_id != incident.id or recommendation.mode is not incident.mode:
            raise ValueError("recommendation does not match incident context")
        evidence_ids = {item.id for item in evidence}
        if not set(recommendation.evidence_ids).issubset(evidence_ids):
            raise ValueError("recommendation cites unavailable evidence")
        matches = self.knowledge_repository.search(f"{incident.summary} schema drift recovery", limit=3)
        if not matches or recommendation.runbook_ids[0] not in {match.document_id for match in matches}:
            raise ValueError("recommendation has no matching runbook citation")
        return recommendation.model_copy(update={"id": recommendation.id or f"rec-{uuid4().hex}"})
