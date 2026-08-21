from __future__ import annotations

from .file_utils import passage_fingerprint
from .models import (
    DifficultyProfile,
    ExamMode,
    GenerationRun,
    OutputType,
    PromptRequest,
    QuestionType,
    RotationAnchor,
    VariationPlan,
)
from .template_loader import TemplateLoader


class PromptBuilder:
    """Build a final prompt by merging common, category, version, and module templates."""

    def __init__(self, template_loader: TemplateLoader | None = None) -> None:
        self.template_loader = template_loader or TemplateLoader()

    def build(self, request: PromptRequest, variation: VariationPlan | None = None) -> str:
        common_template = self.template_loader.load_common_template()
        category_template = self.template_loader.load_category_template(request.category)
        version_template = self._load_version_template(request.version)
        module_templates = self._load_module_templates(request.selected_modules)
        difficulty_profile = self.template_loader.load_difficulty_profile(request.difficulty)
        exam_mode = self._load_exam_mode(request.exam_mode)
        output_type = self._load_output_type(request.output_type)

        # An analysis-only document has no questions, so every question-shaped
        # instruction has to drop out rather than be quietly ignored.
        wants_questions = output_type is None or output_type.includes_questions

        sections = [
            self._build_goal_section(request, difficulty_profile, exam_mode, output_type),
            self._build_curriculum_section(request, exam_mode),
            self._build_common_rules_section(
                common_template, version_template, difficulty_profile, exam_mode, wants_questions
            ),
            self._build_category_section(request.category, category_template),
            self._build_variation_section(variation) if wants_questions else None,
            self._build_modules_section(module_templates) if wants_questions else None,
            self._build_passage_section(request.passage),
            self._build_example_section(request.example_text),
            self._build_document_structure_section(output_type),
            self._build_output_format_section(request, difficulty_profile, output_type),
        ]

        return self._join_sections(sections)

    def _load_exam_mode(self, mode_label: str) -> ExamMode | None:
        if not mode_label.strip():
            return None
        try:
            return self.template_loader.load_exam_mode(mode_label)
        except Exception:
            # An unknown mode should not block generation; the prompt simply
            # falls back to the neutral wording.
            return None

    def _load_output_type(self, type_label: str) -> OutputType | None:
        if not type_label.strip():
            return None
        try:
            return self.template_loader.load_output_type(type_label)
        except Exception:
            return None

    def _build_curriculum_section(
        self, request: PromptRequest, exam_mode: ExamMode | None
    ) -> str | None:
        context = request.curriculum_context.strip()
        if not context:
            return None
        label = (exam_mode.context_label if exam_mode else "") or "교과 연계 정보"
        return self._section(
            "교과 연계",
            [
                f"[{label}] {context}",
                self._bullet_block(
                    "위 교과서와 단원의 학습 목표에 맞추어 설계하라.",
                    "해당 단원에서 다루는 개념과 용어를 우선 사용하라.",
                    "단원 범위를 벗어나는 개념을 새로 도입하지 마라.",
                ),
            ],
        )

    def _build_document_structure_section(self, output_type: OutputType | None) -> str | None:
        if output_type is None or not output_type.structure:
            return None
        blocks = [
            f"[산출물] {output_type.label}",
            "아래 구성을 순서대로 모두 포함하라.\n"
            + "\n".join(f"- {line}" for line in output_type.structure),
        ]
        if output_type.instructions:
            blocks.append(self._bullet_block(*output_type.instructions))
        return self._section("산출물 구성", blocks)

    def plan_variation(
        self,
        request: PromptRequest,
        previous_runs: list[GenerationRun] | None = None,
        manual_types: list[str] | None = None,
    ) -> VariationPlan | None:
        """Decide which question types and passage anchor this round should use.

        Types already spent on this passage are pushed to the back of the queue, so
        repeated runs on the same passage keep landing on fresh ground. Returns None
        when no type list is configured, which leaves the prompt unchanged.

        `manual_types` overrides the automatic assignment — the user picked the types
        by hand, so their choice wins over freshness ordering.
        """
        available = self.template_loader.load_question_types(request.category)
        if not available:
            return None

        runs = previous_runs or []
        round_number = len(runs) + 1

        if manual_types:
            chosen = [qt for name in manual_types for qt in available if qt.name == name]
            assigned = self._take_cycling(chosen, request.question_count)
        else:
            ordered = self._order_types_by_freshness(available, runs, request.passage)
            assigned = self._take_cycling(ordered, request.question_count)

        if not assigned:
            return None

        anchors = self.template_loader.load_rotation_anchors()
        anchor = (
            anchors[(round_number - 1) % len(anchors)]
            if anchors
            else RotationAnchor(label="전체 균형", instruction="지문 전체를 고르게 훑어라.")
        )

        assigned_names = {qt.name for qt in assigned}
        excluded = [
            name
            for name in self._recent_type_names(runs)
            if name not in assigned_names
        ]

        return VariationPlan(
            round_number=round_number,
            assigned_types=assigned,
            anchor=anchor,
            excluded_types=excluded,
            is_manual=bool(manual_types),
        )

    def _order_types_by_freshness(
        self,
        available: list[QuestionType],
        runs: list[GenerationRun],
        passage: str,
    ) -> list[QuestionType]:
        """Sort types so never-used come first, then least-recently-used."""
        # Offset by passage so two different passages in the same category do not
        # both open with the first type on the list.
        offset = int(passage_fingerprint(passage)[:4], 16) % len(available)
        rotated = available[offset:] + available[:offset]

        last_used: dict[str, int] = {}
        for index, run in enumerate(runs):
            for name in run.question_types:
                last_used[name] = index

        # Stable sort: unused types keep their rotated order, used ones trail behind
        # ordered by how long ago they were used.
        return sorted(rotated, key=lambda qt: last_used.get(qt.name, -1))

    def _take_cycling(self, ordered: list[QuestionType], count: int) -> list[QuestionType]:
        """Take `count` types, wrapping around only when the list is exhausted."""
        if count <= 0 or not ordered:
            return []
        result: list[QuestionType] = []
        while len(result) < count:
            remaining = count - len(result)
            result.extend(ordered[:remaining])
        return result

    def _recent_type_names(self, runs: list[GenerationRun], limit: int = 12) -> list[str]:
        """Return distinct type names used in past runs, most recent first."""
        seen: list[str] = []
        for run in reversed(runs):
            for name in run.question_types:
                if name not in seen:
                    seen.append(name)
                if len(seen) >= limit:
                    return seen
        return seen

    def _build_variation_section(self, variation: VariationPlan | None) -> str | None:
        if variation is None:
            return None

        blocks: list[str] = []

        assignment_lines = [
            f"{index}번 문항 — {qt.name}"
            + (f" (평가 대상: {qt.focus})" if qt.focus else "")
            for index, qt in enumerate(variation.assigned_types, start=1)
        ]
        blocks.append(
            "[문항 유형 배분]\n"
            + "\n".join(f"- {line}" for line in assignment_lines)
            + "\n- 위 배분을 반드시 지켜라. 배정된 유형과 다른 유형의 문항으로 대체하지 마라."
            + "\n- 서로 다른 번호의 문항이 사실상 같은 것을 묻고 있다면, 배분을 지키지 못한 것이다."
        )

        blocks.append(
            f"[이번 회차 초점] {variation.anchor.label}\n- {variation.anchor.instruction}"
        )

        if variation.round_number > 1:
            lines = [
                f"[중복 회피] 이 지문으로 문항을 만드는 것은 이번이 {variation.round_number}회차다.",
                "- 이전 회차와 같은 근거 문장, 같은 핵심 어휘, 같은 선지 구조를 반복하지 마라.",
            ]
            if variation.is_manual:
                # The user picked the types on purpose, so only the ground must move.
                lines.append(
                    "- 문항 유형은 위 배분을 그대로 지키되, 지문에서 겨냥하는 지점은 이전 회차와 다르게 잡아라."
                )
            else:
                lines.append("- 이전 회차에서 다루지 않은 지점을 우선 겨냥하라.")
                if variation.excluded_types:
                    lines.append("- 이미 다룬 유형: " + ", ".join(variation.excluded_types))
            blocks.append("\n".join(lines))

        return self._section("문항 구성 설계", blocks)

    def _load_version_template(self, version_name: str) -> str:
        if not version_name.strip():
            return ""
        return self.template_loader.load_version_template(version_name)

    def _load_module_templates(self, module_names: list[str]) -> list[tuple[str, str]]:
        return [
            (module_name, self.template_loader.load_module_template(module_name))
            for module_name in module_names
        ]

    def _build_goal_section(
        self,
        request: PromptRequest,
        difficulty_profile: DifficultyProfile,
        exam_mode: ExamMode | None,
        output_type: OutputType | None,
    ) -> str:
        wants_questions = output_type is None or output_type.includes_questions
        headline = (
            f"아래 지문을 바탕으로 '{output_type.label}'을(를) 작성하라."
            if output_type
            else "아래 지문을 바탕으로 국어과 문항 초안을 설계하라."
        )
        lines = [headline]
        if exam_mode:
            lines.append(f"평가 맥락: {exam_mode.label}")
        lines.append(f"영역: {request.category}")
        lines.append(f"프롬프트 버전: {request.version}")
        if wants_questions:
            lines.append(f"문항 수: {request.question_count}개")
        lines.append(f"난이도: {request.difficulty}")
        lines.append(f"목표 수준: {difficulty_profile.target_band}")
        if wants_questions:
            lines.extend(
                [
                    f"문항 형식: {request.question_style}",
                    f"출제 묶음: {request.set_style}",
                    f"배점 구조: {request.scoring_scheme}",
                ]
            )
        return self._section("작업 목표", [self._bullet_block(*lines)])

    def _build_common_rules_section(
        self,
        common_template: str,
        version_template: str,
        difficulty_profile: DifficultyProfile,
        exam_mode: ExamMode | None,
        wants_questions: bool,
    ) -> str:
        lines = [common_template if wants_questions else self._analysis_only_rules()]
        if exam_mode and exam_mode.guidance:
            lines.append(
                f"[평가 맥락] {exam_mode.label}\n"
                + "\n".join(f"- {line}" for line in exam_mode.guidance)
            )
        if version_template and wants_questions:
            lines.append(self._build_version_guidance_block(version_template))
        lines.append(self._build_difficulty_guidance_block(difficulty_profile))
        return self._section("공통 규칙", lines)

    def _analysis_only_rules(self) -> str:
        """Rules for documents that analyse a work instead of testing on it.

        common.txt is written entirely around question design, so an
        analysis-only output needs its own baseline rather than a filtered one.
        """
        return "\n".join(
            [
                "당신은 한국 국어과 교재와 학습 자료를 작성하는 전문가 AI이다.",
                "객관적 해석 원칙을 지켜, 지문과 보기에서 직접 확인되거나 합리적으로 추론 가능한 내용만 사용하라.",
                "지문 근거를 벗어난 임의의 배경지식 확장, 감상 과잉, 상상적 해석은 피하라.",
                "확정하기 어려운 해석은 단정하지 말고 근거와 함께 여지를 남겨 서술하라.",
                "결과는 모두 한국어로 작성하라.",
                "학생이 그대로 읽고 이해할 수 있는 문장으로 쓰되, 교과 용어는 정확히 사용하라.",
            ]
        )

    def _build_category_section(self, category_name: str, category_template: str) -> str:
        return self._section(
            "영역별 지시",
            [f"[선택 영역] {category_name}", category_template],
        )

    def _build_modules_section(self, module_templates: list[tuple[str, str]]) -> str | None:
        if not module_templates:
            return None

        blocks: list[str] = []
        for module_name, module_text in module_templates:
            blocks.append(f"[{module_name}]\n{module_text}")
        return self._section("추가 모듈", blocks)

    def _build_passage_section(self, passage: str) -> str:
        return self._section("사용자 입력 지문", [passage.strip()])

    def _build_example_section(self, example_text: str) -> str | None:
        cleaned = example_text.strip()
        if not cleaned:
            return None
        return self._section("사용자 입력 보기", [cleaned])

    def _build_output_format_section(
        self,
        request: PromptRequest,
        difficulty_profile: DifficultyProfile,
        output_type: OutputType | None,
    ) -> str:
        if output_type is not None and not output_type.includes_questions:
            return self._section(
                "출력 형식",
                [self._bullet_block(
                    "문항은 만들지 마라.",
                    "각 항목을 소제목으로 구분해 읽기 쉽게 정리하라.",
                    "표로 정리하라고 지시한 항목은 반드시 표 형태로 제시하라.",
                    f"서술 수준은 '{request.difficulty}' 기준에 맞추어라.",
                    f"'{request.difficulty}' 수준은 {difficulty_profile.summary}",
                )],
            )

        lines = self._bullet_block(
            f"총 {request.question_count}개의 문항을 작성하라.",
            "각 문항은 번호를 붙여 구분하라.",
            "문항과 해설을 번갈아 배치하라. 1번 문항 → 1번 해설 → 2번 문항 → 2번 해설 순서다.",
            "해설을 문서 끝에 몰아서 배치하지 마라. 각 문항 바로 아래에 그 문항의 해설이 와야 한다.",
            *self._question_style_guidance(request.question_style),
            *self._set_style_guidance(request.set_style),
            *self._scoring_scheme_guidance(request.scoring_scheme, request.question_count),
            "각 문항마다 문제, 정답, 해설, 출제 의도를 포함하되, 이 넷을 한 덩어리로 묶어라.",
            "문항과 해설의 경계는 '[해설]' 같은 표시나 구분선으로 분명히 드러내라.",
            "오답 선지는 지문 근거를 바탕으로 설계하라.",
            f"전체 결과는 '{request.difficulty}' 난이도 기준에 맞게 조정하라.",
            f"'{request.difficulty}' 난이도는 {difficulty_profile.summary}",
            "출력은 교사용 검토 문서처럼 읽기 쉽게 정리하라.",
        )
        return self._section("출력 형식", [lines])

    def _build_version_guidance_block(self, version_template: str) -> str:
        return "[버전 지침]\n" + version_template.strip()

    def _build_difficulty_guidance_block(self, difficulty_profile: DifficultyProfile) -> str:
        lines = [
            f"[난이도 지침] {difficulty_profile.label}",
            f"- 목표 수준: {difficulty_profile.target_band}",
            f"- 요약: {difficulty_profile.summary}",
            *[f"- {line}" for line in difficulty_profile.guidance],
        ]
        return "\n".join(lines)

    def _question_style_guidance(self, question_style: str) -> list[str]:
        mapping = {
            "객관식 5지선다": [
                "각 객관식 문항은 5개의 선택지를 제시하라.",
                "선택지는 ①~⑤ 형식으로 제시하라.",
            ],
            "객관식 4지선다": [
                "각 객관식 문항은 4개의 선택지를 제시하라.",
                "선택지는 ①~④ 형식으로 제시하라.",
            ],
            "객관식 3지선다": [
                "각 객관식 문항은 3개의 선택지를 제시하라.",
                "선택지는 ①~③ 형식으로 제시하라.",
            ],
            "서술형": [
                "모든 문항은 서술형으로 작성하라.",
                "선택지는 제시하지 말고, 모범 답안 요소와 채점 포인트를 함께 제시하라.",
            ],
            "단답형": [
                "모든 문항은 단답형으로 작성하라.",
                "'~를 찾아 쓰시오' 처럼 지문에서 근거를 직접 찾아 적게 하라.",
                "정답은 지문에 실제로 등장하는 표현이어야 하며, 정답으로 인정되는 표현의 범위를 함께 밝혀라.",
            ],
            "객관식·단답형·서술형 혼합": [
                "세 형식을 섞어 출제하되, 각 문항이 어떤 형식인지 분명히 드러나게 하라.",
                "대략 객관식 6 : 단답형 2 : 서술형 2의 비율로 배분하고, 문항 수가 적으면 객관식을 우선하라.",
                "객관식은 ①~⑤ 형식의 5지선다로 작성하라.",
                "단답형은 '~를 찾아 쓰시오' 처럼 지문에서 근거를 직접 찾아 적게 하고, 정답 인정 범위를 밝혀라.",
                "서술형은 모범 답안과 함께 채점 요소를 항목별로 나누어 제시하라.",
            ],
        }
        return mapping.get(question_style, ["문항 형식은 선택 설정에 맞게 작성하라."])

    def _set_style_guidance(self, set_style: str) -> list[str]:
        mapping = {
            "지문 세트형(수능형)": [
                "가능하면 하나의 지문 또는 보기 묶음 아래에 여러 문항을 배치하는 수능형 세트 구성을 따르라."
            ],
            "독립 문항형": [
                "각 문항은 서로 독립된 문항처럼 작성하라."
            ],
            "혼합형": [
                "세트형 문항과 독립 문항을 혼합하되, 구성 의도를 명확히 드러내라."
            ],
        }
        return mapping.get(set_style, [])

    def _scoring_scheme_guidance(self, scoring_scheme: str, question_count: int) -> list[str]:
        mapping = {
            "수능형 2점·3점 혼합": [
                "배점은 수능형처럼 2점과 3점을 혼합하라.",
                "기본 이해 확인형은 2점, 변별 문항은 3점으로 배정하라.",
            ],
            "균등 배점": [
                "모든 문항은 동일한 배점으로 설정하라."
            ],
            "고난도 3점 중심": [
                "고난도 문항 중심으로 3점 배점을 우선 적용하라."
            ],
        }
        return mapping.get(scoring_scheme, [])

    def _section(self, title: str, blocks: list[str]) -> str:
        cleaned_blocks = [block.strip() for block in blocks if block and block.strip()]
        if not cleaned_blocks:
            return ""
        return f"@@TITLE:{title}\n" + "\n\n".join(cleaned_blocks)

    def _bullet_block(self, *items: str) -> str:
        cleaned_items = [item.strip() for item in items if item and item.strip()]
        return "\n".join(f"- {item}" for item in cleaned_items)

    def _join_sections(self, sections: list[str | None]) -> str:
        rendered: list[str] = []
        ordered_sections = [section.strip() for section in sections if section and section.strip()]
        for index, section in enumerate(ordered_sections, start=1):
            title_line, body = section.split("\n", 1)
            clean_title = title_line.removeprefix("@@TITLE:")
            rendered.append(f"## {index}) {clean_title}\n{body.strip()}")
        return "\n\n".join(rendered).strip() + "\n"
