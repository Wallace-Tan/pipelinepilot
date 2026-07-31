from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class RedactionMatch:
    pattern: str
    path: str


@dataclass(frozen=True)
class RedactionResult:
    sanitized_payload: Any
    matches: tuple[RedactionMatch, ...]

    @property
    def counts(self) -> dict[str, int]:
        return {
            pattern: sum(match.pattern == pattern for match in self.matches)
            for pattern in sorted({match.pattern for match in self.matches})
        }


class RedactionService:
    _email = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
    _card = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
    _identifier = re.compile(r"\b(?:customer|account|member|order)[_-]?(?:id|number)\s*[:=]\s*[A-Z0-9_-]+\b", re.IGNORECASE)

    def __init__(self, patterns: Iterable[str] = ("email", "card", "identifier")) -> None:
        self.patterns = frozenset(patterns)
        unknown = self.patterns - {"email", "card", "identifier"}
        if unknown:
            raise ValueError(f"Unsupported redaction patterns: {sorted(unknown)}")

    def redact(self, payload: Any) -> RedactionResult:
        matches: list[RedactionMatch] = []

        def sanitize(value: Any, path: str) -> Any:
            if isinstance(value, dict):
                return {key: sanitize(item, f"{path}.{key}") for key, item in value.items()}
            if isinstance(value, list):
                return [sanitize(item, f"{path}[{index}]") for index, item in enumerate(value)]
            if isinstance(value, tuple):
                return tuple(sanitize(item, f"{path}[{index}]") for index, item in enumerate(value))
            if not isinstance(value, str):
                return value
            sanitized = value
            for pattern, expression, token in self._expressions():
                def replace(match: re.Match[str]) -> str:
                    matches.append(RedactionMatch(pattern=pattern, path=path))
                    return token

                sanitized = expression.sub(replace, sanitized)
            return sanitized

        return RedactionResult(sanitized_payload=sanitize(payload, "$"), matches=tuple(matches))

    def _expressions(self) -> tuple[tuple[str, re.Pattern[str], str], ...]:
        expressions = {
            "email": (self._email, "[REDACTED_EMAIL]"),
            "card": (self._card, "[REDACTED_CARD]"),
            "identifier": (self._identifier, "[REDACTED_IDENTIFIER]"),
        }
        return tuple((name, *expressions[name]) for name in ("email", "card", "identifier") if name in self.patterns)
