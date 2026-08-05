from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


class CocoCliError(RuntimeError):
    """Raised when the local CoCo CLI cannot produce a usable response."""


class CocoCliClient:
    def __init__(
        self,
        *,
        command: str = "cortex",
        workdir: str | Path | None = None,
        connection: str | None = None,
        timeout_seconds: float = 45.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.command = command
        self.workdir = str(workdir) if workdir else None
        self.connection = connection
        self.timeout_seconds = timeout_seconds

    def prompt_json(self, prompt: str, *, required_keys: set[str]) -> dict[str, Any]:
        output = self._run(prompt)
        for candidate in self._json_candidates(output):
            try:
                value = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict) and required_keys.issubset(value):
                return value
        raise CocoCliError("CoCo returned no valid structured response.")

    def _run(self, prompt: str) -> str:
        args = [self.command]
        if self.connection:
            args.extend(["--connection", self.connection])
        if self.workdir:
            args.extend(["--workdir", self.workdir])
        args.extend(["--sql-read-only", "--allowed-tools", "SQL", "--print", prompt, "--output-format", "stream-json"])
        try:
            completed = subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise CocoCliError(f"CoCo CLI unavailable: {type(error).__name__}.") from error
        if completed.returncode != 0:
            raise CocoCliError(f"CoCo CLI exited with status {completed.returncode}.")
        return completed.stdout

    @staticmethod
    def _json_candidates(output: str) -> list[str]:
        candidates: list[str] = []
        for line in output.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            CocoCliClient._collect_strings(event, candidates)
            if isinstance(event, dict):
                candidates.append(json.dumps(event))
        candidates.append(output)
        for start, character in enumerate(output):
            if character != "{":
                continue
            decoder = json.JSONDecoder()
            try:
                _, end = decoder.raw_decode(output[start:])
            except json.JSONDecodeError:
                continue
            candidates.append(output[start:start + end])
        return list(reversed(candidates))

    @staticmethod
    def _collect_strings(value: Any, candidates: list[str]) -> None:
        if isinstance(value, str):
            if "{" in value and "}" in value:
                candidates.append(value)
            return
        if isinstance(value, dict):
            for nested in value.values():
                CocoCliClient._collect_strings(nested, candidates)
            return
        if isinstance(value, list):
            for nested in value:
                CocoCliClient._collect_strings(nested, candidates)
