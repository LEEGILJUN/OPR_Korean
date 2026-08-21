from __future__ import annotations

from datetime import datetime
import os
import re
import sys
from pathlib import Path

from .models import PromptExportData


def resource_root() -> Path:
    """Return the base path for bundled resources."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def templates_root() -> Path:
    """Return the templates directory path."""
    return resource_root() / "templates"


def config_root() -> Path:
    """Return the config directory path."""
    return resource_root() / "config"


def user_data_root() -> Path:
    """Return a writable directory for local user data."""
    if sys.platform.startswith("win"):
        base_dir = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base_dir / "CSATPromptGenerator"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "CSATPromptGenerator"
    return Path.home() / ".local" / "share" / "CSATPromptGenerator"


def save_text_file(path: Path, content: str) -> None:
    """Save UTF-8 text content to a file."""
    path.write_text(content, encoding="utf-8")


def ensure_file_extension(path: Path, extension: str) -> Path:
    """Append a file extension if the selected path does not already have it."""
    normalized = extension.lower().lstrip(".")
    if path.suffix.lower() == f".{normalized}":
        return path
    return path.with_suffix(f".{normalized}")


def build_default_filename(category: str, version: str, extension: str) -> str:
    """Build a readable default filename for saved prompt archives."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_category = _slugify(category)
    safe_version = _slugify(version)
    return f"csat_prompt_{safe_category}_{safe_version}_{timestamp}.{extension}"


def build_export_content(data: PromptExportData, extension: str) -> str:
    """Render export content for txt or md formats."""
    if extension.lower() == "md":
        return _build_markdown_export(data)
    return _build_text_export(data)


def current_timestamp() -> str:
    """Return a human-readable local timestamp."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _build_text_export(data: PromptExportData) -> str:
    selected_options = ", ".join(data.selected_options) if data.selected_options else "없음"
    example_text = data.example_text.strip() if data.example_text.strip() else "없음"
    parts = [
        f"제목: {data.title}",
        f"생성 시각: {data.timestamp}",
        f"카테고리: {data.category}",
        f"프롬프트 버전: {data.version}",
        f"난이도: {data.difficulty}",
        f"문항 수: {data.question_count}",
        f"선택 옵션: {selected_options}",
        "",
        "[지문]",
        data.passage.strip(),
        "",
        "[보기]",
        example_text,
        "",
        "[최종 생성 프롬프트]",
        data.generated_prompt.strip(),
        "",
    ]
    return "\n".join(parts)


def _build_markdown_export(data: PromptExportData) -> str:
    selected_options = ", ".join(data.selected_options) if data.selected_options else "없음"
    example_text = data.example_text.strip() if data.example_text.strip() else "없음"
    parts = [
        f"# {data.title}",
        "",
        "## 메타데이터",
        f"- 생성 시각: {data.timestamp}",
        f"- 카테고리: {data.category}",
        f"- 프롬프트 버전: {data.version}",
        f"- 난이도: {data.difficulty}",
        f"- 문항 수: {data.question_count}",
        f"- 선택 옵션: {selected_options}",
        "",
        "## 지문",
        data.passage.strip(),
        "",
        "## 보기",
        example_text,
        "",
        "## 최종 생성 프롬프트",
        "~~~text",
        data.generated_prompt.strip(),
        "~~~",
        "",
    ]
    return "\n".join(parts)


def _slugify(value: str) -> str:
    cleaned = re.sub(r"\s+", "_", value.strip())
    cleaned = re.sub(r'[\\/:*?"<>|]+', "", cleaned)
    return cleaned or "prompt"
