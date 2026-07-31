from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, wait
from time import monotonic

from app.domain.contracts import RuntimeMode
from app.skills.contracts import ContextSkill, SkillContext, SkillResult, SkillStatus


class SkillCoordinator:
    def __init__(self, skills: list[ContextSkill], timeout_seconds: float = 5.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.skills = skills
        self.timeout_seconds = timeout_seconds

    def collect(self, context: SkillContext) -> list[SkillResult]:
        executor = ThreadPoolExecutor(max_workers=max(1, len(self.skills)))
        futures: dict[Future[SkillResult], ContextSkill] = {
            executor.submit(self._collect_one, skill, context): skill for skill in self.skills
        }
        results: dict[str, SkillResult] = {}
        deadline = monotonic() + self.timeout_seconds
        pending = set(futures)
        while pending:
            remaining = max(0.0, deadline - monotonic())
            done, pending = wait(pending, timeout=remaining)
            for future in done:
                skill = futures[future]
                try:
                    result = future.result()
                except Exception:
                    result = self._unavailable(skill, "skill execution failed")
                results[skill.name.value] = result
            if not done:
                break
        for future in pending:
            skill = futures[future]
            future.cancel()
            results[skill.name.value] = self._unavailable(skill, "skill timed out")
        executor.shutdown(wait=False, cancel_futures=True)
        return [results[skill.name.value] for skill in sorted(self.skills, key=lambda item: item.name.value)]

    @staticmethod
    def _collect_one(skill: ContextSkill, context: SkillContext) -> SkillResult:
        return SkillResult.model_validate(skill.collect(context))

    @staticmethod
    def _unavailable(skill: ContextSkill, reason: str) -> SkillResult:
        return SkillResult(
            schema_version="skill_result.v1",
            skill_name=skill.name,
            status=SkillStatus.UNAVAILABLE,
            adapter_mode=skill.adapter_mode if skill.adapter_mode else RuntimeMode.FIXTURE,
            degradation_reason=reason,
        )
