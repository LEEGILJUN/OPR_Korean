"""Centralized stylesheet and color tokens for the CSAT Prompt Generator UI."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Color tokens
# ---------------------------------------------------------------------------
COLORS = {
    # Backgrounds
    "bg_app": "#f0f2f5",
    "bg_card": "#ffffff",
    "bg_card_primary": "#f8faff",
    "bg_input": "#fbfcfe",
    "bg_sidebar": "#f7f8fb",
    "bg_toolbar": "#ffffff",
    "bg_hover": "#eef1f6",

    # Borders
    "border_default": "#d4dae3",
    "border_focus": "#4f7cff",
    "border_primary_card": "#b9d0ff",
    "border_section": "#e2e8f0",
    "border_sidebar": "#e5e9f0",

    # Text
    "text_primary": "#1a202c",
    "text_secondary": "#4a5568",
    "text_muted": "#718096",
    "text_hint": "#a0aec0",
    "text_on_accent": "#ffffff",

    # Accent
    "accent": "#3b82f6",
    "accent_hover": "#2563eb",
    "accent_light": "#eff6ff",

    # Status
    "success": "#10b981",
    "success_bg": "#ecfdf5",
    "success_border": "#a7f3d0",
    "warning": "#f59e0b",
    "warning_bg": "#fffbeb",
    "warning_border": "#fde68a",
    "danger": "#ef4444",
    "danger_bg": "#fef2f2",
    "danger_border": "#fecaca",
    "danger_text": "#b91c1c",

    # Toast
    "toast_bg": "#1e293b",
    "toast_text": "#f8fafc",
}


def build_stylesheet() -> str:
    """Return the full application QSS stylesheet."""
    c = COLORS
    return f"""
    /* ============ Global ============ */
    QMainWindow {{
        background: {c["bg_app"]};
    }}
    QWidget#rootWidget {{
        background: {c["bg_app"]};
    }}
    * {{
        font-family: -apple-system, "Malgun Gothic", "맑은 고딕", "Apple SD Gothic Neo",
                     "Segoe UI", "Noto Sans KR", sans-serif;
    }}

    /* ============ Toolbar ============ */
    QFrame#toolbarFrame {{
        background: {c["bg_toolbar"]};
        border: 1px solid {c["border_default"]};
        border-radius: 14px;
    }}

    /* ============ Sidebar ============ */
    QWidget#sidebarPanel {{
        background: {c["bg_sidebar"]};
        border: 1px solid {c["border_sidebar"]};
        border-radius: 16px;
    }}
    QScrollArea#sidebarScroll {{
        background: transparent;
        border: none;
    }}
    QScrollArea#sidebarScroll > QWidget > QWidget {{
        background: transparent;
    }}

    /* ============ Section Cards ============ */
    QFrame#sectionCard {{
        background: {c["bg_card"]};
        border: 1px solid {c["border_section"]};
        border-radius: 14px;
    }}
    QFrame#primarySectionCard {{
        background: {c["bg_card_primary"]};
        border: 1px solid {c["border_primary_card"]};
        border-radius: 14px;
    }}

    /* ============ Labels ============ */
    QLabel {{
        color: {c["text_primary"]};
        font-size: 14px;
    }}
    QLabel#appTitle {{
        color: {c["text_primary"]};
        font-size: 20px;
        font-weight: 700;
    }}
    QLabel#appSubtitle {{
        color: {c["text_secondary"]};
        font-size: 13px;
    }}
    QLabel#sectionTitle {{
        color: {c["text_primary"]};
        font-size: 15px;
        font-weight: 700;
    }}
    QLabel#sectionHint {{
        color: {c["text_muted"]};
        font-size: 12px;
    }}
    QLabel#fieldLabel {{
        color: {c["text_primary"]};
        font-size: 13px;
        font-weight: 600;
    }}
    QLabel#descriptionBox {{
        background: {c["accent_light"]};
        color: {c["text_secondary"]};
        border: 1px solid {c["border_primary_card"]};
        border-radius: 10px;
        padding: 10px 12px;
        font-size: 13px;
    }}
    QLabel#tokenCounter {{
        color: {c["text_muted"]};
        font-size: 12px;
        padding: 4px 8px;
    }}

    /* ============ Inputs ============ */
    QPlainTextEdit, QComboBox, QSpinBox {{
        background: {c["bg_input"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border_default"]};
        border-radius: 10px;
        padding: 8px 10px;
        font-size: 14px;
        selection-background-color: #cfe0ff;
    }}
    QComboBox, QSpinBox {{
        min-height: 38px;
    }}
    QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
        border: 1.5px solid {c["border_focus"]};
        background: {c["bg_card"]};
    }}
    QPlainTextEdit#outputEditor {{
        background: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border_section"]};
        border-radius: 12px;
        padding: 14px;
        font-size: 13px;
    }}

    /* ============ Buttons ============ */
    QPushButton {{
        background: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border_default"]};
        border-radius: 10px;
        padding: 8px 14px;
        font-size: 13px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background: {c["bg_hover"]};
    }}
    QPushButton:disabled {{
        color: {c["text_hint"]};
        background: {c["bg_app"]};
        border-color: {c["border_section"]};
    }}

    /* Primary action — generate */
    QPushButton#generateButton {{
        background: {c["accent"]};
        color: {c["text_on_accent"]};
        border: none;
        border-radius: 12px;
        padding: 12px 28px;
        font-size: 15px;
        font-weight: 700;
        min-height: 44px;
    }}
    QPushButton#generateButton:hover {{
        background: {c["accent_hover"]};
    }}
    QPushButton#generateButton:disabled {{
        background: #94a3b8;
        color: #cbd5e1;
    }}

    /* Secondary */
    QPushButton#secondaryButton {{
        background: {c["bg_card"]};
        color: {c["accent"]};
        border: 1px solid {c["accent"]};
        padding: 7px 12px;
        font-size: 13px;
    }}
    QPushButton#secondaryButton:hover {{
        background: {c["accent_light"]};
    }}

    /* Danger */
    QPushButton#dangerButton {{
        color: {c["danger_text"]};
        background: {c["danger_bg"]};
        border: 1px solid {c["danger_border"]};
        font-size: 12px;
        padding: 6px 10px;
    }}
    QPushButton#dangerButton:hover {{
        background: #fee2e2;
    }}

    /* Icon-style small button */
    QPushButton#iconButton {{
        background: transparent;
        border: none;
        padding: 4px 8px;
        font-size: 13px;
        min-height: 28px;
    }}
    QPushButton#iconButton:hover {{
        background: {c["bg_hover"]};
        border-radius: 8px;
    }}

    /* ============ Checkboxes ============ */
    QCheckBox {{
        color: {c["text_primary"]};
        font-size: 13px;
        spacing: 8px;
        padding: 4px 0;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 1.5px solid {c["border_default"]};
        background: {c["bg_card"]};
    }}
    QCheckBox::indicator:checked {{
        background: {c["accent"]};
        border-color: {c["accent"]};
    }}

    /* ============ Tooltip ============ */
    QToolTip {{
        background: {c["toast_bg"]};
        color: {c["toast_text"]};
        border: none;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 13px;
    }}

    /* ============ ToolButton (help) ============ */
    QToolButton[helpButton="true"] {{
        background: {c["bg_hover"]};
        color: {c["text_muted"]};
        border: 1px solid {c["border_default"]};
        border-radius: 12px;
        font-weight: 700;
        font-size: 12px;
    }}
    QToolButton[helpButton="true"]:hover {{
        background: {c["accent_light"]};
        color: {c["accent"]};
        border-color: {c["accent"]};
    }}

    /* ============ StatusBar ============ */
    QStatusBar {{
        background: {c["bg_toolbar"]};
        color: {c["text_muted"]};
        border-top: 1px solid {c["border_section"]};
        font-size: 12px;
        padding: 2px 8px;
    }}

    /* ============ Splitter ============ */
    QSplitter::handle {{
        background: {c["border_section"]};
        margin: 0 4px;
    }}
    QSplitter::handle:horizontal {{
        width: 3px;
    }}

    /* ============ Scrollbar (minimal) ============ */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 4px 0;
    }}
    QScrollBar::handle:vertical {{
        background: #c4c9d4;
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: #a0a8b8;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        height: 0;
    }}
    """
