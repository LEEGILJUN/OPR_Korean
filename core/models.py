from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PromptRequest:
    """Input values collected from the GUI."""

    passage: str
    example_text: str
    category: str
    version: str
    selected_modules: list[str]
    question_count: int
    difficulty: str
    question_style: str
    set_style: str
    scoring_scheme: str


@dataclass(slots=True)
class PromptExportData:
    """Structured payload used for copying metadata-aware prompt archives."""

    title: str
    timestamp: str
    category: str
    version: str
    difficulty: str
    question_count: int
    selected_options: list[str]
    passage: str
    example_text: str
    generated_prompt: str


@dataclass(slots=True)
class PromptPreset:
    """Preset configuration for common CSAT prompt generation workflows."""

    preset_id: str
    label: str
    description: str
    category: str
    version: str
    difficulty: str
    question_count: int
    modules: list[str]
    question_style: str = "객관식 5지선다"
    set_style: str = "지문 세트형(수능형)"
    scoring_scheme: str = "수능형 2점·3점 혼합"
    is_user_defined: bool = False


@dataclass(slots=True)
class DifficultyProfile:
    """Difficulty guidance derived from CSAT grade-target intent."""

    label: str
    target_band: str
    summary: str
    guidance: list[str]


@dataclass(slots=True)
class QuestionType:
    """A CSAT question type used to spread coverage across generated items."""

    name: str
    focus: str


@dataclass(slots=True)
class RotationAnchor:
    """Per-round steering that shifts which part of the passage gets targeted."""

    label: str
    instruction: str


@dataclass(slots=True)
class VariationPlan:
    """Diversity plan for one generation round of a given passage."""

    round_number: int
    assigned_types: list[QuestionType]
    anchor: RotationAnchor
    excluded_types: list[str]


@dataclass(slots=True)
class GenerationRun:
    """A past generation recorded for one passage."""

    timestamp: str
    category: str
    version: str
    difficulty: str
    question_types: list[str]
    anchor: str
