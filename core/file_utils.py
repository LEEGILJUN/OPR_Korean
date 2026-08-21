from __future__ import annotations

from datetime import datetime
import hashlib
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


def passage_fingerprint(passage: str) -> str:
    """Return a stable short key for a passage, ignoring whitespace differences."""
    normalized = re.sub(r"\s+", " ", passage).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


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


def parse_export_content(content: str) -> dict[str, str]:
    """Read back a saved .txt/.md archive into its labelled parts.

    Only fields that are actually present are returned, so a hand-edited file or
    an archive written by an older version still restores what it can.
    """
    result: dict[str, str] = {}

    # Metadata lines: "카테고리: 독서" (txt) or "- 카테고리: 독서" (md).
    meta_keys = {
        "카테고리": "category",
        "프롬프트 버전": "version",
        "난이도": "difficulty",
        "문항 수": "question_count",
    }
    for line in content.splitlines():
        stripped = line.lstrip("-# ").strip()
        for label, key in meta_keys.items():
            prefix = f"{label}:"
            if stripped.startswith(prefix) and key not in result:
                result[key] = stripped[len(prefix):].strip()

    # Body blocks: "[지문]" (txt) or "## 지문" (md).
    body_labels = {"지문": "passage", "보기": "example_text"}
    lines = content.splitlines()
    current_key: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if current_key and current_key not in result:
            text = "\n".join(buffer).strip()
            if text and text != "없음":
                result[current_key] = text

    for line in lines:
        heading = _match_export_heading(line)
        if heading is not None:
            flush()
            buffer = []
            current_key = body_labels.get(heading)
            continue
        if current_key:
            buffer.append(line)
    flush()

    return result


def _match_export_heading(line: str) -> str | None:
    """Return the heading name for an archive section line, else None."""
    stripped = line.strip()
    match = re.match(r"^\[(.+)\]$", stripped)
    if match:
        return match.group(1).strip()
    match = re.match(r"^#{1,6}\s+(.+)$", stripped)
    if match:
        return match.group(1).strip()
    return None


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
