from __future__ import annotations

import json
from pathlib import Path

from .file_utils import current_timestamp, passage_fingerprint, user_data_root
from .models import GenerationRun, PromptRequest, VariationPlan


class HistoryStoreError(RuntimeError):
    """Readable error for generation history persistence issues."""


class GenerationHistoryStore:
    """Remember what was already generated for a passage so later rounds can differ.

    The app only builds prompts — it never sees the questions the LLM produced.
    So a run records what was *requested* (question types, rotation anchor), which
    is enough to keep later rounds off the ground earlier rounds already covered.
    """

    MAX_RUNS_PER_PASSAGE = 20
    MAX_PASSAGES = 200

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or user_data_root() / "generation_history.json"

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------

    def passage_key(self, passage: str) -> str:
        """Return a stable short key for a passage, ignoring whitespace noise."""
        return passage_fingerprint(passage)

    def load_runs(self, passage: str, category: str) -> list[GenerationRun]:
        """Return past runs for this passage and category, oldest first."""
        entries = self._load_entries()
        key = self.passage_key(passage)
        runs = entries.get(key, [])
        return [run for run in runs if run.category == category]

    def round_number(self, passage: str, category: str) -> int:
        """Return the round number the next generation would be (1-based)."""
        return len(self.load_runs(passage, category)) + 1

    def record(self, request: PromptRequest, plan: VariationPlan) -> None:
        """Append a run for this passage. Never raises — history is best-effort."""
        try:
            entries = self._load_entries()
            key = self.passage_key(request.passage)
            runs = entries.setdefault(key, [])
            runs.append(
                GenerationRun(
                    timestamp=current_timestamp(),
                    category=request.category,
                    version=request.version,
                    difficulty=request.difficulty,
                    question_types=[qt.name for qt in plan.assigned_types],
                    anchor=plan.anchor.label,
                )
            )
            entries[key] = runs[-self.MAX_RUNS_PER_PASSAGE :]
            self._write_entries(entries)
        except (OSError, HistoryStoreError):
            # A broken history file must never block prompt generation.
            pass

    def clear_passage(self, passage: str) -> None:
        """Forget every run recorded for one passage."""
        entries = self._load_entries()
        entries.pop(self.passage_key(passage), None)
        self._write_entries(entries)

    def clear_all(self) -> None:
        """Forget every recorded run."""
        self._write_entries({})

    # -------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------

    def _load_entries(self) -> dict[str, list[GenerationRun]]:
        if not self.path.exists():
            return {}

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # Corrupted history is discarded rather than surfaced to the user.
            return {}

        raw_entries = payload.get("entries", [])
        if not isinstance(raw_entries, list):
            return {}

        result: dict[str, list[GenerationRun]] = {}
        for item in raw_entries:
            if not isinstance(item, dict):
                continue
            key = str(item.get("passage_key", "")).strip()
            raw_runs = item.get("runs", [])
            if not key or not isinstance(raw_runs, list):
                continue
            runs = [self._build_run(raw_run) for raw_run in raw_runs]
            result[key] = [run for run in runs if run is not None]
        return result

    def _build_run(self, raw_run: object) -> GenerationRun | None:
        if not isinstance(raw_run, dict):
            return None
        question_types = raw_run.get("question_types", [])
        if not isinstance(question_types, list):
            question_types = []
        return GenerationRun(
            timestamp=str(raw_run.get("timestamp", "")),
            category=str(raw_run.get("category", "")),
            version=str(raw_run.get("version", "")),
            difficulty=str(raw_run.get("difficulty", "")),
            question_types=[str(name) for name in question_types if str(name).strip()],
            anchor=str(raw_run.get("anchor", "")),
        )

    def _write_entries(self, entries: dict[str, list[GenerationRun]]) -> None:
        trimmed = list(entries.items())[-self.MAX_PASSAGES :]
        payload = {
            "entries": [
                {
                    "passage_key": key,
                    "runs": [
                        {
                            "timestamp": run.timestamp,
                            "category": run.category,
                            "version": run.version,
                            "difficulty": run.difficulty,
                            "question_types": run.question_types,
                            "anchor": run.anchor,
                        }
                        for run in runs
                    ],
                }
                for key, runs in trimmed
            ]
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise HistoryStoreError(
                f"생성 이력을 저장하지 못했습니다.\n경로: {self.path}\n오류: {exc}"
            ) from exc
