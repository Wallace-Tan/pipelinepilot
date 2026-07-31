from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.domain.contracts import (
    ActorRole,
    Incident,
    PolicyDecision,
    PolicyDecisionType,
    PolicyDocument,
    RiskLevel,
    RuntimeMode,
)


ROLE_RANK = {
    ActorRole.VIEWER: 0,
    ActorRole.OPERATOR: 1,
    ActorRole.ADMIN: 2,
}


class PolicyEngine:
    def __init__(self, policy: PolicyDocument | None, invalid_reason: str | None = None) -> None:
        self.policy = policy
        self.invalid_reason = invalid_reason

    @classmethod
    def from_path(cls, path: str | Path) -> PolicyEngine:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            policy = PolicyDocument.model_validate(payload)
            if not policy.immutable:
                return cls(None, "policy document must be immutable")
            return cls(policy)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            return cls(None, f"policy document unavailable: {type(error).__name__}")

    def evaluate(
        self,
        incident: Incident,
        action: str,
        actor_role: ActorRole,
        retry_count: int = 0,
    ) -> PolicyDecision:
        if retry_count < 0:
            return self._deny(action, "retry count cannot be negative")
        if self.policy is None:
            return self._deny(action, self.invalid_reason or "policy document unavailable")

        matching_rule = next(
            (
                rule
                for rule in self.policy.rules
                if rule.action == action and rule.environment is incident.mode
            ),
            None,
        )
        if matching_rule is None:
            return self._deny(action, "no policy rule matches this action and environment")
        if ROLE_RANK[actor_role] < ROLE_RANK[matching_rule.minimum_role]:
            return PolicyDecision(
                schema_version="policy_decision.v1",
                id=self._decision_id(),
                policy_version=self.policy.version,
                action=action,
                decision=PolicyDecisionType.DENY,
                risk=matching_rule.risk,
                matched_rule_id=matching_rule.id,
                required_approver_role=matching_rule.required_approver_role,
                reasons=[
                    *matching_rule.reasons,
                    f"Actor role {actor_role.value} does not meet minimum role {matching_rule.minimum_role.value}.",
                ],
            )
        return PolicyDecision(
            schema_version="policy_decision.v1",
            id=self._decision_id(),
            policy_version=self.policy.version,
            action=action,
            decision=matching_rule.decision,
            risk=matching_rule.risk,
            matched_rule_id=matching_rule.id,
            required_approver_role=matching_rule.required_approver_role,
            reasons=matching_rule.reasons,
        )

    def _deny(self, action: str, reason: str) -> PolicyDecision:
        return PolicyDecision(
            schema_version="policy_decision.v1",
            id=self._decision_id(),
            policy_version=self.policy.version if self.policy else "invalid",
            action=action,
            decision=self.policy.default_decision if self.policy else PolicyDecisionType.DENY,
            risk=RiskLevel.CRITICAL,
            reasons=[reason],
        )

    @staticmethod
    def _decision_id() -> str:
        return f"policy-decision-{uuid4().hex}"
