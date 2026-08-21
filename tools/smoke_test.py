"""Headless smoke test: loaders, prompt builder, and window construction.

Run with:  .venv/bin/python tools/smoke_test.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.history_store import GenerationHistoryStore
from core.models import PromptRequest
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
    print("[1/5] 템플릿 로더")
    loader = check_loaders()
    print("[2/5] 프리셋 로더")
    check_presets()
    print("[3/5] 프롬프트 빌더")
    check_builder(loader)
    print("[4/5] 문항 다양성 (유형 배분 + 회차 이력)")
    check_variation(loader)
    print("[5/5] GUI 생성 (offscreen)")
    check_window()
    print("\n모든 확인 통과.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
