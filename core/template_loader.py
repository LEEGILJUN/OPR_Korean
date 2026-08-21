from __future__ import annotations

from collections import OrderedDict
import json
from pathlib import Path

from .file_utils import config_root, templates_root, user_data_root
from .models import DifficultyProfile, EvaluationMode, QuestionType, RotationAnchor


class TemplateLoadError(RuntimeError):
    """Readable error for missing or invalid template selections."""


class CategorySaveError(RuntimeError):
    """Readable error for user category persistence issues."""


class TemplateLoader:
    """Load templates from the external templates directory."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or templates_root()
        self.categories = OrderedDict(
            [
                ("문학", "literature.txt"),
                ("현대시", "modern_poetry.txt"),
                ("현대소설", "modern_novel.txt"),
                ("고전시가", "classical_poetry.txt"),
                ("고전소설", "classical_novel.txt"),
                ("독서", "reading.txt"),
                ("문법", "grammar.txt"),
                ("언어와 매체", "language_media.txt"),
                ("화법과 작문", "speech_writing.txt"),
            ]
        )
        self.versions = OrderedDict(
            [
                ("기본형", "basic.txt"),
                ("고급형", "advanced.txt"),
                ("Ultimate형", "ultimate.txt"),
            ]
        )
        # Fallbacks keep older environments usable even if version files are missing.
        self.version_fallbacks = {
            "기본형": (
                "기본형 프롬프트로 작성하라.\n"
                "- 간결하고 실용적으로 작성한다.\n"
                "- 과도한 중간 절차 설명 없이 바로 문항 생성에 집중한다."
            ),
            "고급형": (
                "고급형 프롬프트로 작성하라.\n"
                "- 문항 설계 전에 핵심 평가 포인트를 정리한다.\n"
                "- 각 문항마다 정답 근거와 오답 설계 이유를 구조적으로 제시한다."
            ),
            "Ultimate형": (
                "Ultimate형 프롬프트로 작성하라.\n"
                "- 해석 범위를 엄격히 통제하고 지문 근거 중심으로 판단한다.\n"
                "- 깊은 추론을 거쳐 문항을 설계하되 최종 결과만 정제해 제시한다.\n"
                "- 자체 점검을 수행해 모호한 선지와 중복 해석 가능성을 줄인다."
            ),
        }
        self.modules = OrderedDict(
            [
                ("Anchor Setting 포함", "anchor.txt"),
                ("CoT 포함", "cot.txt"),
                ("Self-Correction 포함", "self_correction.txt"),
                ("오답 유형 라벨링 포함", "distractor_labeling.txt"),
                ("난이도 미세조정 포함", "difficulty_control.txt"),
            ]
        )
        self.user_categories_path = user_data_root() / "user_categories.json"
        self.difficulty_profiles_path = config_root() / "difficulty_profiles.json"
        self.category_starters_path = config_root() / "category_starter_templates.json"
        self.question_types_path = config_root() / "question_types.json"
        self.rotation_anchors_path = config_root() / "rotation_anchors.json"
        self.evaluation_criteria_path = config_root() / "evaluation_criteria.json"

    def category_names(self) -> list[str]:
        names = list(self.categories.keys())
        user_categories = self._load_user_categories(allow_missing=True)
        return [*names, *[name for name in user_categories.keys() if name not in self.categories]]

    def version_names(self) -> list[str]:
        return list(self.versions.keys())

    def module_names(self) -> list[str]:
        return list(self.modules.keys())

    def difficulty_names(self) -> list[str]:
        return [profile.label for profile in self.load_difficulty_profiles()]

    def load_common_template(self) -> str:
        return self._read_text(self.root / "common.txt")

    def load_category_template(self, category_name: str) -> str:
        if category_name in self.categories:
            return self._read_text(self.root / self._lookup(self.categories, category_name, "카테고리"))

        user_categories = self._load_user_categories(allow_missing=True)
        if category_name in user_categories:
            return user_categories[category_name].strip()

        available = ", ".join(self.category_names())
        raise TemplateLoadError(
            f"카테고리 '{category_name}' 에 해당하는 템플릿이 없습니다.\n사용 가능 항목: {available}"
        )

    def load_version_template(self, version_name: str) -> str:
        file_name = self._lookup(self.versions, version_name, "프롬프트 버전")
        path = self.root / "versions" / file_name
        if path.exists():
            return self._read_text(path)
        return self.version_fallbacks.get(version_name, "")

    def load_module_template(self, module_name: str) -> str:
        file_name = self._lookup(self.modules, module_name, "선택 모듈")
        return self._read_text(self.root / "modules" / file_name)

    def load_difficulty_profiles(self) -> list[DifficultyProfile]:
        path = self.difficulty_profiles_path
        if not path.exists():
            raise TemplateLoadError(f"난이도 설정 파일을 찾을 수 없습니다.\n경로: {path}")

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise TemplateLoadError(
                f"난이도 설정 파일 형식이 올바르지 않습니다.\n경로: {path}\n오류: {exc}"
            ) from exc

        profiles = payload.get("profiles")
        if not isinstance(profiles, list):
            raise TemplateLoadError(f"난이도 설정 형식이 올바르지 않습니다.\n경로: {path}")

        result: list[DifficultyProfile] = []
        for item in profiles:
            if not isinstance(item, dict):
                raise TemplateLoadError("난이도 프로필 항목 형식이 올바르지 않습니다.")
            guidance = item.get("guidance", [])
            if not isinstance(guidance, list) or not all(isinstance(line, str) for line in guidance):
                raise TemplateLoadError("난이도 guidance 항목은 문자열 배열이어야 합니다.")
            result.append(
                DifficultyProfile(
                    label=str(item.get("label", "")).strip(),
                    target_band=str(item.get("target_band", "")).strip(),
                    summary=str(item.get("summary", "")).strip(),
                    guidance=[line.strip() for line in guidance if str(line).strip()],
                )
            )

        labels = [profile.label for profile in result if profile.label]
        if len(labels) != len(set(labels)):
            raise TemplateLoadError("난이도 프로필 이름이 중복됩니다.")
        return result

    def load_difficulty_profile(self, difficulty_name: str) -> DifficultyProfile:
        for profile in self.load_difficulty_profiles():
            if profile.label == difficulty_name:
                return profile
        available = ", ".join(self.difficulty_names())
        raise TemplateLoadError(
            f"난이도 '{difficulty_name}' 에 해당하는 설정이 없습니다.\n사용 가능 항목: {available}"
        )

    def load_category_starters(self) -> OrderedDict[str, str]:
        path = self.category_starters_path
        if not path.exists():
            return OrderedDict()

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise TemplateLoadError(
                f"출제영역 시작 템플릿 파일 형식이 올바르지 않습니다.\n경로: {path}\n오류: {exc}"
            ) from exc

        starters = payload.get("starters", [])
        if not isinstance(starters, list):
            raise TemplateLoadError(f"출제영역 시작 템플릿 형식이 올바르지 않습니다.\n경로: {path}")

        result: OrderedDict[str, str] = OrderedDict()
        for item in starters:
            if not isinstance(item, dict):
                raise TemplateLoadError("출제영역 시작 템플릿 항목 형식이 올바르지 않습니다.")
            name = str(item.get("name", "")).strip()
            template_text = str(item.get("template", "")).strip()
            if name and template_text:
                result[name] = template_text
        return result

    def load_question_types(self, category_name: str) -> list[QuestionType]:
        """Return the question types available for a category.

        User-defined categories have no dedicated list, so they fall back to the
        generic set. A missing config file falls back to an empty list, which
        simply disables type assignment rather than breaking generation.
        """
        payload = self._read_json(self.question_types_path, "문항 유형 설정 파일")
        if payload is None:
            return []

        types_by_category = payload.get("types", {})
        if not isinstance(types_by_category, dict):
            raise TemplateLoadError(
                f"문항 유형 설정 형식이 올바르지 않습니다.\n경로: {self.question_types_path}"
            )

        raw_types = types_by_category.get(category_name)
        if not isinstance(raw_types, list) or not raw_types:
            raw_types = payload.get("default", [])
        if not isinstance(raw_types, list):
            return []

        result: list[QuestionType] = []
        for item in raw_types:
            if not isinstance(item, dict):
                raise TemplateLoadError("문항 유형 항목 형식이 올바르지 않습니다.")
            name = str(item.get("name", "")).strip()
            focus = str(item.get("focus", "")).strip()
            if name:
                result.append(QuestionType(name=name, focus=focus))
        return result

    def load_rotation_anchors(self) -> list[RotationAnchor]:
        """Return the per-round anchors that shift passage coverage between runs."""
        payload = self._read_json(self.rotation_anchors_path, "회차 앵커 설정 파일")
        if payload is None:
            return []

        anchors = payload.get("anchors", [])
        if not isinstance(anchors, list):
            raise TemplateLoadError(
                f"회차 앵커 설정 형식이 올바르지 않습니다.\n경로: {self.rotation_anchors_path}"
            )

        result: list[RotationAnchor] = []
        for item in anchors:
            if not isinstance(item, dict):
                raise TemplateLoadError("회차 앵커 항목 형식이 올바르지 않습니다.")
            label = str(item.get("label", "")).strip()
            instruction = str(item.get("instruction", "")).strip()
            if label and instruction:
                result.append(RotationAnchor(label=label, instruction=instruction))
        return result

    def load_evaluation_modes(self) -> list[EvaluationMode]:
        """Return the ways generated questions can be checked."""
        payload = self._read_json(self.evaluation_criteria_path, "검증 설정 파일")
        if payload is None:
            raise TemplateLoadError(
                f"검증 설정 파일을 찾을 수 없습니다.\n경로: {self.evaluation_criteria_path}"
            )

        modes = payload.get("modes", [])
        if not isinstance(modes, list) or not modes:
            raise TemplateLoadError(
                f"검증 설정 형식이 올바르지 않습니다.\n경로: {self.evaluation_criteria_path}"
            )

        result: list[EvaluationMode] = []
        for item in modes:
            if not isinstance(item, dict):
                raise TemplateLoadError("검증 모드 항목 형식이 올바르지 않습니다.")
            criteria = item.get("criteria", [])
            output_format = item.get("output_format", [])
            if not isinstance(criteria, list) or not isinstance(output_format, list):
                raise TemplateLoadError("검증 모드의 criteria와 output_format은 배열이어야 합니다.")
            label = str(item.get("label", "")).strip()
            if not label:
                continue
            result.append(
                EvaluationMode(
                    mode_id=str(item.get("id", "")).strip(),
                    label=label,
                    description=str(item.get("description", "")).strip(),
                    strip_answers=bool(item.get("strip_answers", False)),
                    instruction=str(item.get("instruction", "")).strip(),
                    criteria=[str(line).strip() for line in criteria if str(line).strip()],
                    output_format=[str(line).strip() for line in output_format if str(line).strip()],
                )
            )
        if not result:
            raise TemplateLoadError("사용 가능한 검증 모드가 없습니다.")
        return result

    def evaluation_mode_labels(self) -> list[str]:
        return [mode.label for mode in self.load_evaluation_modes()]

    def load_evaluation_mode(self, label: str) -> EvaluationMode:
        for mode in self.load_evaluation_modes():
            if mode.label == label:
                return mode
        available = ", ".join(self.evaluation_mode_labels())
        raise TemplateLoadError(
            f"검증 모드 '{label}' 을 찾을 수 없습니다.\n사용 가능 항목: {available}"
        )

    def _read_json(self, path: Path, label: str) -> dict | None:
        """Read an optional JSON config. Returns None when the file is absent."""
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise TemplateLoadError(
                f"{label} 형식이 올바르지 않습니다.\n경로: {path}\n오류: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise TemplateLoadError(f"{label} 형식이 올바르지 않습니다.\n경로: {path}")
        return payload

    def add_user_category(self, name: str, template_text: str) -> None:
        normalized_name = name.strip()
        normalized_template = template_text.strip()
        if not normalized_name:
            raise CategorySaveError("출제영역 이름은 비워둘 수 없습니다.")
        if not normalized_template:
            raise CategorySaveError("출제영역 지시문은 비워둘 수 없습니다.")
        if normalized_name in self.categories:
            raise CategorySaveError(
                f"기본 출제영역과 이름이 겹칩니다: {normalized_name}\n다른 이름을 사용해 주세요."
            )

        user_categories = self._load_user_categories(allow_missing=True)
        if normalized_name in user_categories:
            raise CategorySaveError(
                f"같은 이름의 사용자 출제영역이 이미 있습니다: {normalized_name}"
            )

        user_categories[normalized_name] = normalized_template
        self._write_user_categories(user_categories)

    def remove_user_category(self, name: str) -> None:
        if name in self.categories:
            raise CategorySaveError("기본 출제영역은 삭제할 수 없습니다.")

        user_categories = self._load_user_categories(allow_missing=True)
        if name not in user_categories:
            raise CategorySaveError("삭제할 사용자 출제영역을 찾을 수 없습니다.")

        del user_categories[name]
        self._write_user_categories(user_categories)

    def is_user_category(self, name: str) -> bool:
        if name in self.categories:
            return False
        user_categories = self._load_user_categories(allow_missing=True)
        return name in user_categories

    def _load_user_categories(self, *, allow_missing: bool) -> OrderedDict[str, str]:
        path = self.user_categories_path
        if not path.exists():
            if allow_missing:
                return OrderedDict()
            raise TemplateLoadError(f"사용자 출제영역 파일을 찾을 수 없습니다.\n경로: {path}")

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise TemplateLoadError(
                f"사용자 출제영역 파일 형식이 올바르지 않습니다.\n경로: {path}\n오류: {exc}"
            ) from exc

        categories = payload.get("categories", [])
        if not isinstance(categories, list):
            raise TemplateLoadError(f"사용자 출제영역 설정 형식이 올바르지 않습니다.\n경로: {path}")

        result: OrderedDict[str, str] = OrderedDict()
        for item in categories:
            if not isinstance(item, dict):
                raise TemplateLoadError("사용자 출제영역 항목 형식이 올바르지 않습니다.")
            name = str(item.get("name", "")).strip()
            template_text = str(item.get("template", "")).strip()
            if not name or not template_text:
                raise TemplateLoadError("사용자 출제영역에는 name과 template이 모두 필요합니다.")
            result[name] = template_text
        return result

    def _write_user_categories(self, categories: OrderedDict[str, str]) -> None:
        payload = {
            "categories": [
                {"name": name, "template": template_text}
                for name, template_text in categories.items()
            ]
        }
        try:
            self.user_categories_path.parent.mkdir(parents=True, exist_ok=True)
            self.user_categories_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise CategorySaveError(
                f"사용자 출제영역 저장에 실패했습니다.\n경로: {self.user_categories_path}\n오류: {exc}"
            ) from exc

    def _read_text(self, path: Path) -> str:
        if not path.exists():
            raise TemplateLoadError(
                f"템플릿 파일을 찾을 수 없습니다.\n경로: {path}"
            )
        return path.read_text(encoding="utf-8").strip()

    def _lookup(
        self,
        mapping: OrderedDict[str, str],
        key: str,
        label: str,
    ) -> str:
        if key not in mapping:
            available = ", ".join(mapping.keys())
            raise TemplateLoadError(
                f"{label} '{key}' 에 해당하는 템플릿이 없습니다.\n사용 가능 항목: {available}"
            )
        return mapping[key]
