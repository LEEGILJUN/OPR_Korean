"""Headless smoke test: loaders, prompt builder, and window construction.

Run with:  .venv/bin/python tools/smoke_test.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.evaluation_builder import EvaluationBuilder
from core.history_store import GenerationHistoryStore
from core.models import EvaluationRequest, PromptRequest
from core.preset_loader import PresetLoader
from core.prompt_builder import PromptBuilder
from core.template_loader import TemplateLoader


def check_loaders() -> TemplateLoader:
    loader = TemplateLoader()

    categories = loader.category_names()
    assert categories, "카테고리 목록이 비어 있습니다."
    for name in categories:
        assert loader.load_category_template(name).strip(), f"빈 카테고리 템플릿: {name}"

    for name in loader.version_names():
        assert loader.load_version_template(name).strip(), f"빈 버전 템플릿: {name}"

    for name in loader.module_names():
        assert loader.load_module_template(name).strip(), f"빈 모듈 템플릿: {name}"

    difficulties = loader.difficulty_names()
    assert difficulties, "난이도 프로필이 비어 있습니다."

    assert loader.load_common_template().strip(), "common.txt 가 비어 있습니다."
    loader.load_category_starters()

    print(f"  카테고리 {len(categories)}개, 버전 {len(loader.version_names())}개, "
          f"모듈 {len(loader.module_names())}개, 난이도 {len(difficulties)}개")
    return loader


def check_presets() -> None:
    presets = PresetLoader().load_presets()
    assert presets, "프리셋이 비어 있습니다."
    print(f"  프리셋 {len(presets)}개: {', '.join(p.label for p in presets)}")


def check_builder(loader: TemplateLoader) -> None:
    builder = PromptBuilder(loader)
    for category in loader.category_names():
        request = PromptRequest(
            passage="테스트용 지문입니다.",
            example_text="테스트용 보기입니다.",
            category=category,
            version="고급형",
            selected_modules=loader.module_names(),
            question_count=2,
            difficulty=loader.difficulty_names()[0],
            question_style="객관식 5지선다",
            set_style="지문 세트형(수능형)",
            scoring_scheme="수능형 2점·3점 혼합",
        )
        prompt = builder.build(request)
        assert "## 1) 작업 목표" in prompt, f"섹션 조립 실패: {category}"
        assert "@@TITLE:" not in prompt, f"섹션 마커가 남아 있습니다: {category}"
    print("  모든 카테고리에 대해 프롬프트 조립 성공")


def check_variation(loader: TemplateLoader) -> None:
    """Round 2 on the same passage must not repeat round 1's question types."""
    builder = PromptBuilder(loader)
    for category in loader.category_names():
        assert loader.load_question_types(category), f"문항 유형이 비어 있습니다: {category}"
    assert loader.load_rotation_anchors(), "회차 앵커가 비어 있습니다."

    with tempfile.TemporaryDirectory() as tmp:
        store = GenerationHistoryStore(Path(tmp) / "history.json")
        request = PromptRequest(
            passage="검증용 지문입니다. 두 번째 문단입니다.",
            example_text="",
            category="독서",
            version="고급형",
            selected_modules=[],
            question_count=3,
            difficulty=loader.difficulty_names()[0],
            question_style="객관식 5지선다",
            set_style="지문 세트형(수능형)",
            scoring_scheme="수능형 2점·3점 혼합",
        )

        rounds: list[list[str]] = []
        for expected_round in (1, 2, 3):
            runs = store.load_runs(request.passage, request.category)
            plan = builder.plan_variation(request, runs)
            assert plan is not None, "변주 계획이 생성되지 않았습니다."
            assert plan.round_number == expected_round, (
                f"회차가 어긋납니다: {plan.round_number} != {expected_round}"
            )
            assert len(plan.assigned_types) == request.question_count, "유형 배분 개수 불일치"

            names = [qt.name for qt in plan.assigned_types]
            assert len(set(names)) == len(names), f"한 회차 안에 유형이 중복됩니다: {names}"

            prompt = builder.build(request, plan)
            assert "문항 구성 설계" in prompt, "변주 섹션이 프롬프트에 없습니다."
            if expected_round > 1:
                assert "중복 회피" in prompt, "2회차 이상인데 중복 회피 지침이 없습니다."

            rounds.append(names)
            store.record(request, plan)

        assert not set(rounds[0]) & set(rounds[1]), (
            f"1회차와 2회차 유형이 겹칩니다: {rounds[0]} / {rounds[1]}"
        )
        print(f"  1회차 {rounds[0]}")
        print(f"  2회차 {rounds[1]}")
        print(f"  3회차 {rounds[2]}")


def check_output_types(loader: TemplateLoader) -> None:
    """Every output type must build, and analysis-only ones must drop question talk."""
    builder = PromptBuilder(loader)
    modes = loader.load_exam_modes()
    assert modes, "시험 모드가 비어 있습니다."

    for mode in modes:
        names = loader.difficulty_names(mode.mode_id)
        assert names, f"난이도 목록이 비어 있습니다: {mode.label}"

    csat = loader.difficulty_names("csat")
    school = loader.difficulty_names("school")
    assert not set(csat) & set(school), "수능/내신 난이도 축이 섞였습니다."

    for output_type in loader.load_output_types():
        request = PromptRequest(
            passage="검증용 지문입니다. 둘째 문단입니다.",
            example_text="",
            category="현대시",
            version="고급형",
            selected_modules=["CoT 포함"],
            question_count=5,
            difficulty=school[0],
            question_style="객관식·단답형·서술형 혼합",
            set_style="독립 문항형",
            scoring_scheme="균등 배점",
            exam_mode=modes[-1].label,
            output_type=output_type.label,
            curriculum_context="[비상] 국어2 Ⅰ. 단원명",
        )
        plan = builder.plan_variation(request, [])
        prompt = builder.build(request, plan)

        assert "산출물 구성" in prompt, f"산출물 구성 섹션 없음: {output_type.label}"
        assert output_type.label in prompt, f"산출물 이름 누락: {output_type.label}"
        assert "교과 연계" in prompt, f"교과 연계 섹션 없음: {output_type.label}"

        if output_type.includes_questions:
            assert "문항 구성 설계" in prompt, f"문항 배분 없음: {output_type.label}"
            # 문항 → 해설 → 문항 → 해설 순서. 예전에는 해설을 끝에 모으라고 했다.
            assert "번갈아" in prompt, f"문항·해설 교차 배치 지시 없음: {output_type.label}"
            assert "몰아서 배치하지 마라" in prompt, (
                f"해설 몰아쓰기 금지 지시 없음: {output_type.label}"
            )
            for stale in ("해설은 문항 뒤에 따로 모아라", "정답과 해설 — 문항 번호별로"):
                assert stale not in prompt, (
                    f"교차 배치와 충돌하는 옛 지시가 남아 있습니다: {output_type.label} / {stale}"
                )
        else:
            assert "문항 구성 설계" not in prompt, (
                f"해제 전용인데 문항 배분이 들어갔습니다: {output_type.label}"
            )
            assert "문항은 만들지 마라" in prompt, f"문항 금지 지시 없음: {output_type.label}"

    print(f"  시험 모드 {len(modes)}개 (수능 {len(csat)}단계 / 내신 {len(school)}단계)")
    print(f"  산출물 유형 {len(loader.load_output_types())}개 모두 조립 성공")
    print("  문항·해설 교차 배치 지시 확인")


def check_evaluation(loader: TemplateLoader) -> None:
    """Blind mode must not leak the answer key; other modes must keep it."""
    builder = EvaluationBuilder(loader)
    modes = loader.load_evaluation_modes()
    assert modes, "검증 모드가 비어 있습니다."

    generated = """## 1-B 후보 목록
1. 2문단의 한정 조건
2. 3문단 인과 관계

## 문항

1. 윗글의 내용과 일치하지 않는 것은?
① 첫째 선지입니다.
② 둘째 선지입니다.
③ 셋째 선지입니다.

정답: ②
해설: 2문단에서 확인된다.
출제 의도: 세부 정보 확인

2. 윗글의 논지를 200자 내외로 서술하시오.

모범 답안: 핵심 개념을 언급하면 만점
"""
    leak_markers = ["정답:", "해설:", "출제 의도", "모범 답안", "후보 목록"]

    for mode in modes:
        request = EvaluationRequest(
            generated_output=generated,
            passage="검증용 원본 지문입니다.",
            example_text="",
            category="독서",
            difficulty=loader.difficulty_names()[0],
            question_style="객관식 5지선다",
            mode=mode,
        )
        prompt = builder.build(request)
        assert "검증 목표" in prompt, f"검증 목표 섹션 없음: {mode.label}"
        assert "원본 지문" in prompt, f"원본 지문 섹션 없음: {mode.label}"

        if mode.strip_answers:
            leaked = [marker for marker in leak_markers if marker in prompt]
            assert not leaked, f"블라인드 모드에 정답이 누출되었습니다: {leaked}"
            assert "① 첫째 선지입니다." in prompt, "블라인드 모드에서 선지가 사라졌습니다."
            assert "서술하시오" in prompt, "블라인드 모드에서 서술형 문항이 사라졌습니다."
        else:
            assert "정답: ②" in prompt, f"검토 모드인데 정답이 빠졌습니다: {mode.label}"

    print(f"  검증 모드 {len(modes)}개: " + ", ".join(m.mode_id for m in modes))
    print("  블라인드 모드 정답 누출 없음, 검토 모드 정답 보존 확인")


def check_window() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window.windowTitle(), "윈도우 제목이 비어 있습니다."
    assert not window.preset_load_error_message, window.preset_load_error_message
    print(f"  MainWindow 생성 성공: {window.windowTitle()}")
    del window
    del app


def main() -> int:
    print("[1/7] 템플릿 로더")
    loader = check_loaders()
    print("[2/7] 프리셋 로더")
    check_presets()
    print("[3/7] 프롬프트 빌더")
    check_builder(loader)
    print("[4/7] 문항 다양성 (유형 배분 + 회차 이력)")
    check_variation(loader)
    print("[5/7] 산출물 유형 · 시험 모드")
    check_output_types(loader)
    print("[6/7] 생성 결과 검증 (정답 제거 + 검증 프롬프트)")
    check_evaluation(loader)
    print("[7/7] GUI 생성 (offscreen)")
    check_window()
    print("\n모든 확인 통과.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
