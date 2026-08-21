from __future__ import annotations

from dataclasses import dataclass, field


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
    answer_layout: str = "문항 바로 뒤에 해설"
    exam_mode: str = "csat"
    output_type: str = "question_set"
    curriculum_context: str = ""
    section_counts: dict[str, int] = field(default_factory=dict)


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
    """Difficulty guidance for one target level within an exam mode."""

    label: str
    target_band: str
    summary: str
    guidance: list[str]
    mode: str = "csat"


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
    is_manual: bool = False


@dataclass(slots=True)
class GenerationRun:
    """A past generation recorded for one passage."""

    timestamp: str
    category: str
    version: str
    difficulty: str
    question_types: list[str]
    anchor: str


@dataclass(slots=True)
class EvaluationMode:
    """One way of checking generated questions."""

    mode_id: str
    label: str
    description: str
    strip_answers: bool
    instruction: str
    criteria: list[str]
    output_format: list[str]


@dataclass(slots=True)
class EvaluationRequest:
    """Input for building a verification prompt from pasted-back output."""

    generated_output: str
    passage: str
    example_text: str
    category: str
    difficulty: str
    question_style: str
    mode: EvaluationMode


@dataclass(slots=True)
class ExamMode:
    """Whether the material targets the CSAT or a school's own exam."""

    mode_id: str
    label: str
    description: str
    context_label: str
    context_help: str
    guidance: list[str]


@dataclass(slots=True)
class QuestionSection:
    """One question format inside an output type, with its own count."""

    key: str
    label: str
    default: int
    minimum: int
    maximum: int


@dataclass(slots=True)
class OutputType:
    """What kind of document the prompt should produce."""

    type_id: str
    label: str
    description: str
    includes_questions: bool
    needs_passage: bool
    structure: list[str]
    instructions: list[str]
    categories: list[str]  # 비어 있으면 모든 출제 영역에서 사용 가능
    count_applies_to: str = ""  # 비어 있으면 문항 수 설정이 전체 문항 수를 뜻한다
    question_sections: list[QuestionSection] = field(default_factory=list)
