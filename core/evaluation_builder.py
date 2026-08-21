from __future__ import annotations

import re

from .models import EvaluationMode, EvaluationRequest
from .template_loader import TemplateLoader

# A line that starts a new question item.
QUESTION_START = re.compile(
    r"^\s*(?:"
    r"\d+\s*[.)]"                       # 1.  1)
    r"|[\[\(【]?\s*문항\s*\d+"           # [문항 1]
    r"|[\[\(【]?\s*문제\s*\d+"           # 【문제 1】
    r"|Q\s*\d+"                          # Q1
    r")"
)

# A markdown/section heading ends whatever block was being collected.
SECTION_BREAK = re.compile(r"^\s*(?:#{1,6}\s|={3,}\s*$|-{3,}\s*$)")

# Choice markers — the strongest signal that a block is a real question.
CHOICE_MARKER = re.compile(r"^\s*(?:[\u2460-\u2473]|\(\s*[1-9]\s*\)|[1-9]\s*[.)]\s+\S)")

# A stem that reads like a question or an instruction to answer.
STEM_ENDING = re.compile(r"(?:\?|것은|것을|고르시오|쓰시오|서술하시오|서술하라|설명하라|하라)\s*[.?]?\s*$")

# A line that reveals the answer, rationale, or design intent.
_ANSWER_KEYWORD = (
    r"(?:정답(?:\s*및\s*해설)?|답안|답|해설|풀이|출제\s*의도"
    r"|평가\s*(?:목표|요소|포인트|기준)"
    r"|오답\s*(?:유형|분석|라벨|선지\s*설계)?"
    r"|채점\s*(?:기준|포인트|요소)?|모범\s*답안|근거|난이도|변별(?:도)?|배점\s*근거)"
)

ANSWER_MARKER = re.compile(
    # "정답: ②"  /  "[해설] ..."  /  "**채점 기준**: ..."  /  "- 출제 의도: ..."
    r"^\s*[\[\(【*#>\-\s]*" + _ANSWER_KEYWORD + r"\s*[\]\)】*]*\s*[:：]"
    # a bare bracketed label on its own line: "[정답]"
    r"|^\s*[\[\(【]\s*" + _ANSWER_KEYWORD + r"\s*[\]\)】]\s*$"
)


class EvaluationBuildError(RuntimeError):
    """Readable error for evaluation prompt construction issues."""


class EvaluationBuilder:
    """Build a prompt that checks whether generated questions are actually sound.

    The app never talks to an LLM itself, so verification works the same way
    generation does: the user pastes the model's output back in, the app builds a
    verification prompt, and the user runs that in a *fresh* session.
    """

    def __init__(self, template_loader: TemplateLoader | None = None) -> None:
        self.template_loader = template_loader or TemplateLoader()

    def build(self, request: EvaluationRequest) -> str:
        mode = request.mode
        material = self._prepare_material(request, mode)

        sections = [
            self._build_role_section(request, mode),
            self._build_criteria_section(mode),
            self._build_passage_section(request.passage),
            self._build_example_section(request.example_text),
            self._build_material_section(material, mode),
            self._build_output_format_section(mode),
        ]
        return self._join_sections(sections)

    # -------------------------------------------------------------------
    # Answer stripping
    # -------------------------------------------------------------------

    def extract_question_items(self, text: str) -> str:
        """Keep only question stems and choices, dropping answers and rationale.

        A blind solve is only meaningful if the model cannot see the answer key.
        Generated output usually carries analysis stages, answers, and commentary
        around the items, so everything outside a question block is dropped.
        """
        blocks: list[list[str]] = []
        current: list[str] | None = None

        for line in text.splitlines():
            if QUESTION_START.match(line):
                if current:
                    blocks.append(current)
                current = [line]
                continue
            if current is None:
                continue
            if ANSWER_MARKER.match(line) or SECTION_BREAK.match(line):
                blocks.append(current)
                current = None
                continue
            current.append(line)

        if current:
            blocks.append(current)

        kept = [block for block in blocks if self._looks_like_question(block)]
        cleaned = ["\n".join(block).strip() for block in kept]
        return "\n\n".join(block for block in cleaned if block)

    def _looks_like_question(self, block: list[str]) -> bool:
        """Reject numbered lines that are analysis notes rather than questions.

        Generated output often contains numbered candidate lists and analysis
        items that also start with "1." — those must not reach a blind solve.
        """
        if not block:
            return False
        stem = block[0].strip()
        if not stem:
            return False
        # A block with real choices is a question, whatever the stem looks like.
        if any(CHOICE_MARKER.match(line) for line in block[1:]):
            return True
        # Otherwise accept only stems phrased as a question or an instruction,
        # which is how 서술형 items read.
        return bool(STEM_ENDING.search(stem))

    def _prepare_material(self, request: EvaluationRequest, mode: EvaluationMode) -> str:
        raw = request.generated_output.strip()
        if not raw:
            raise EvaluationBuildError(
                "검증할 생성 결과가 비어 있습니다.\nLLM이 만든 문항을 붙여 넣어 주세요."
            )
        if not mode.strip_answers:
            return raw

        extracted = self.extract_question_items(raw)
        if not extracted:
            raise EvaluationBuildError(
                "붙여 넣은 내용에서 문항을 찾지 못했습니다.\n"
                "문항 번호가 '1.' '1)' '[문항 1]' 같은 형태인지 확인해 주세요.\n"
                "또는 정답과 해설을 직접 지운 뒤 '정밀 검토' 모드를 사용해 주세요."
            )
        return extracted

    # -------------------------------------------------------------------
    # Sections
    # -------------------------------------------------------------------

    def _build_role_section(self, request: EvaluationRequest, mode: EvaluationMode) -> str:
        lines = [mode.instruction, ""]
        lines.append(
            self._bullet_block(
                f"영역: {request.category}",
                f"목표 난이도: {request.difficulty}",
                f"문항 형식: {request.question_style}",
                "이 문항들은 다른 세션에서 생성된 것이다. 잘 만들어졌다고 전제하지 마라.",
                "판단은 아래 지문과 보기에서 직접 확인되는 내용만을 근거로 하라.",
                "결과는 모두 한국어로 작성하라.",
            )
        )
        if mode.strip_answers:
            lines.append(
                "\n정답과 해설은 의도적으로 제거되어 있다. 정답을 추측해 달라는 것이 아니라, "
                "네가 실제로 풀어 보고 어떤 답에 도달하는지를 보려는 것이다."
            )
        return self._section("검증 목표", ["\n".join(lines)])

    def _build_criteria_section(self, mode: EvaluationMode) -> str:
        return self._section(
            "점검 항목",
            [self._bullet_block(*mode.criteria)],
        )

    def _build_passage_section(self, passage: str) -> str | None:
        cleaned = passage.strip()
        if not cleaned:
            return None
        return self._section("원본 지문", [cleaned])

    def _build_example_section(self, example_text: str) -> str | None:
        cleaned = example_text.strip()
        if not cleaned:
            return None
        return self._section("원본 보기", [cleaned])

    def _build_material_section(self, material: str, mode: EvaluationMode) -> str:
        title = "검증 대상 문항 (정답·해설 제거됨)" if mode.strip_answers else "검증 대상 자료"
        return self._section(title, [material])

    def _build_output_format_section(self, mode: EvaluationMode) -> str:
        return self._section("출력 형식", [self._bullet_block(*mode.output_format)])

    # -------------------------------------------------------------------
    # Rendering helpers
    # -------------------------------------------------------------------

    def _section(self, title: str, blocks: list[str]) -> str:
        cleaned = [block.strip() for block in blocks if block and block.strip()]
        if not cleaned:
            return ""
        return f"@@TITLE:{title}\n" + "\n\n".join(cleaned)

    def _bullet_block(self, *items: str) -> str:
        cleaned = [item.strip() for item in items if item and item.strip()]
        return "\n".join(
            item if item.startswith("-") else f"- {item}" for item in cleaned
        )

    def _join_sections(self, sections: list[str | None]) -> str:
        rendered: list[str] = []
        ordered = [section.strip() for section in sections if section and section.strip()]
        for index, section in enumerate(ordered, start=1):
            title_line, body = section.split("\n", 1)
            clean_title = title_line.removeprefix("@@TITLE:")
            rendered.append(f"## {index}) {clean_title}\n{body.strip()}")
        return "\n\n".join(rendered).strip() + "\n"
