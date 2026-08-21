from __future__ import annotations

import json
from pathlib import Path
import re

from .file_utils import config_root, user_data_root
from .models import PromptPreset


class PresetLoadError(RuntimeError):
    """Readable error raised when preset configuration is invalid."""


class PresetSaveError(RuntimeError):
    """Readable error raised when preset persistence fails."""


class PresetLoader:
    """Load prompt presets from an external JSON configuration."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or config_root() / "presets.json"
        self.user_presets_path = user_data_root() / "user_presets.json"
        self.hidden_presets_path = user_data_root() / "hidden_presets.json"

    def load_presets(self) -> list[PromptPreset]:
        bundled_presets = self._load_preset_file(self.config_path, is_user_defined=False)
        user_presets = self._load_preset_file(
            self.user_presets_path,
            is_user_defined=True,
            allow_missing=True,
        )
        hidden_ids = self._load_hidden_preset_ids()

        visible_bundled = [
            preset for preset in bundled_presets if preset.preset_id not in hidden_ids
        ]

        merged: list[PromptPreset] = []
        seen_labels: set[str] = set()
        for preset in [*visible_bundled, *user_presets]:
            if preset.label in seen_labels:
                raise PresetLoadError(f"프리셋 이름이 중복됩니다: {preset.label}")
            seen_labels.add(preset.label)
            merged.append(preset)
        return merged

    def save_user_preset(self, preset: PromptPreset) -> PromptPreset:
        existing_presets = self.load_presets()
        duplicate = next((item for item in existing_presets if item.label == preset.label), None)
        if duplicate is not None:
            raise PresetSaveError(
                f"같은 이름의 프리셋이 이미 있습니다: {preset.label}\n다른 이름으로 저장해 주세요."
            )

        user_presets = self._load_preset_file(
            self.user_presets_path,
            is_user_defined=True,
            allow_missing=True,
        )
        normalized_preset = PromptPreset(
            preset_id=self._build_user_preset_id(preset.label, [*existing_presets, *user_presets]),
            label=preset.label.strip(),
            description=preset.description.strip(),
            category=preset.category,
            version=preset.version,
            difficulty=preset.difficulty,
            question_count=preset.question_count,
            modules=list(preset.modules),
            question_style=preset.question_style,
            set_style=preset.set_style,
            scoring_scheme=preset.scoring_scheme,
            is_user_defined=True,
        )
        user_presets.append(normalized_preset)
        self._write_presets(self.user_presets_path, user_presets)
        self._remove_hidden_preset_id(normalized_preset.preset_id)
        return normalized_preset

    def remove_preset(self, preset: PromptPreset) -> None:
        if preset.is_user_defined:
            user_presets = self._load_preset_file(
                self.user_presets_path,
                is_user_defined=True,
                allow_missing=True,
            )
            remaining = [
                item for item in user_presets if item.preset_id != preset.preset_id
            ]
            if len(remaining) == len(user_presets):
                raise PresetSaveError("삭제할 사용자 프리셋을 찾을 수 없습니다.")
            self._write_presets(self.user_presets_path, remaining)
            return

        hidden_ids = self._load_hidden_preset_ids()
        if preset.preset_id not in hidden_ids:
            hidden_ids.append(preset.preset_id)
        self._write_hidden_preset_ids(hidden_ids)

    def _load_preset_file(
        self,
        path: Path,
        *,
        is_user_defined: bool,
        allow_missing: bool = False,
    ) -> list[PromptPreset]:
        if not path.exists():
            if allow_missing:
                return []
            raise PresetLoadError(
                f"프리셋 설정 파일을 찾을 수 없습니다.\n경로: {path}"
            )

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise PresetLoadError(
                f"프리셋 설정 파일 형식이 올바르지 않습니다.\n경로: {path}\n오류: {exc}"
            ) from exc

        presets_data = payload.get("presets")
        if not isinstance(presets_data, list):
            raise PresetLoadError(
                f"프리셋 설정 형식이 올바르지 않습니다.\n경로: {path}"
            )

        presets: list[PromptPreset] = []
        for item in presets_data:
            presets.append(self._build_preset(item, is_user_defined=is_user_defined))
        return presets

    def _build_preset(self, item: object, *, is_user_defined: bool) -> PromptPreset:
        if not isinstance(item, dict):
            raise PresetLoadError("프리셋 항목 형식이 올바르지 않습니다.")

        required_fields = [
            "id",
            "label",
            "description",
            "category",
            "version",
            "difficulty",
            "question_count",
            "modules",
        ]
        missing = [field for field in required_fields if field not in item]
        if missing:
            raise PresetLoadError(f"프리셋 항목에 필수 필드가 없습니다: {', '.join(missing)}")

        modules = item["modules"]
        if not isinstance(modules, list) or not all(isinstance(module, str) for module in modules):
            raise PresetLoadError("프리셋 modules 항목은 문자열 배열이어야 합니다.")

        question_count = item["question_count"]
        if not isinstance(question_count, int) or question_count < 1:
            raise PresetLoadError("프리셋 question_count는 1 이상의 정수여야 합니다.")

        return PromptPreset(
            preset_id=str(item["id"]),
            label=str(item["label"]),
            description=str(item["description"]),
            category=str(item["category"]),
            version=str(item["version"]),
            difficulty=str(item["difficulty"]),
            question_count=question_count,
            modules=list(modules),
            question_style=str(item.get("question_style", "객관식 5지선다")),
            set_style=str(item.get("set_style", "지문 세트형(수능형)")),
            scoring_scheme=str(item.get("scoring_scheme", "수능형 2점·3점 혼합")),
            is_user_defined=is_user_defined,
        )

    def _load_hidden_preset_ids(self) -> list[str]:
        if not self.hidden_presets_path.exists():
            return []

        try:
            payload = json.loads(self.hidden_presets_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise PresetLoadError(
                f"숨김 프리셋 설정 파일 형식이 올바르지 않습니다.\n경로: {self.hidden_presets_path}\n오류: {exc}"
            ) from exc

        hidden_ids = payload.get("hidden_preset_ids", [])
        if not isinstance(hidden_ids, list) or not all(isinstance(item, str) for item in hidden_ids):
            raise PresetLoadError(
                f"숨김 프리셋 설정 형식이 올바르지 않습니다.\n경로: {self.hidden_presets_path}"
            )
        return hidden_ids

    def _write_presets(self, path: Path, presets: list[PromptPreset]) -> None:
        payload = {
            "presets": [self._serialize_preset(preset) for preset in presets],
        }
        self._write_json(path, payload)

    def _write_hidden_preset_ids(self, hidden_ids: list[str]) -> None:
        payload = {"hidden_preset_ids": hidden_ids}
        self._write_json(self.hidden_presets_path, payload)

    def _write_json(self, path: Path, payload: dict[str, object]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise PresetSaveError(
                f"프리셋 설정을 저장하지 못했습니다.\n경로: {path}\n오류: {exc}"
            ) from exc

    def _serialize_preset(self, preset: PromptPreset) -> dict[str, object]:
        return {
            "id": preset.preset_id,
            "label": preset.label,
            "description": preset.description,
            "category": preset.category,
            "version": preset.version,
            "difficulty": preset.difficulty,
            "question_count": preset.question_count,
            "modules": list(preset.modules),
            "question_style": preset.question_style,
            "set_style": preset.set_style,
            "scoring_scheme": preset.scoring_scheme,
        }

    def _build_user_preset_id(
        self,
        label: str,
        existing_presets: list[PromptPreset],
    ) -> str:
        base_id = self._slugify(label)
        candidate = f"user_{base_id}"
        existing_ids = {preset.preset_id for preset in existing_presets}
        counter = 2
        while candidate in existing_ids:
            candidate = f"user_{base_id}_{counter}"
            counter += 1
        return candidate

    def _remove_hidden_preset_id(self, preset_id: str) -> None:
        hidden_ids = self._load_hidden_preset_ids()
        if preset_id not in hidden_ids:
            return
        self._write_hidden_preset_ids([item for item in hidden_ids if item != preset_id])

    def _slugify(self, value: str) -> str:
        normalized = re.sub(r"\s+", "_", value.strip().lower())
        normalized = re.sub(r"[^0-9a-zA-Z가-힣_]+", "", normalized)
        return normalized or "preset"
