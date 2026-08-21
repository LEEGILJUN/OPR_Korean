"""Usage guide dialog — explains the three-step workflow inside the app."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .styles import COLORS


class GuideDialog(QDialog):
    """Scrollable walkthrough built from config/user_guide.json."""

    def __init__(self, guide: dict, parent: QWidget | None = None, *, show_dismiss: bool = False) -> None:
        super().__init__(parent)
        self.guide = guide
        self._dismiss_checkbox: QCheckBox | None = None

        self.setWindowTitle(guide.get("title", "사용 방법"))
        self.setMinimumSize(720, 620)
        self.setStyleSheet(self._stylesheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_body(), 1)
        layout.addWidget(self._build_footer(show_dismiss))

    # -------------------------------------------------------------------
    # Public
    # -------------------------------------------------------------------

    def dismissed_forever(self) -> bool:
        """True when the user asked not to see this on startup again."""
        return bool(self._dismiss_checkbox and self._dismiss_checkbox.isChecked())

    # -------------------------------------------------------------------
    # Sections
    # -------------------------------------------------------------------

    def _build_header(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("guideHeader")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(28, 22, 28, 18)
        layout.setSpacing(8)

        title = QLabel(self.guide.get("title", "사용 방법"))
        title.setObjectName("guideTitle")
        layout.addWidget(title)

        intro = self.guide.get("intro", "")
        if intro:
            intro_label = QLabel(intro)
            intro_label.setObjectName("guideIntro")
            intro_label.setWordWrap(True)
            layout.addWidget(intro_label)

        return frame

    def _build_body(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 20, 28, 24)
        layout.setSpacing(18)

        for step in self.guide.get("steps", []):
            layout.addWidget(self._build_step_card(step))

        shortcuts = self.guide.get("shortcuts", [])
        if shortcuts:
            layout.addWidget(self._build_section_label("단축키"))
            layout.addWidget(self._build_shortcut_card(shortcuts))

        faq = self.guide.get("faq", [])
        if faq:
            layout.addWidget(self._build_section_label("자주 묻는 질문"))
            for item in faq:
                layout.addWidget(self._build_faq_card(item))

        layout.addStretch(1)
        scroll.setWidget(container)
        return scroll

    def _build_step_card(self, step: dict) -> QWidget:
        card = QFrame()
        card.setObjectName("guideStepCard")
        outer = QHBoxLayout(card)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(14)

        badge = QLabel(str(step.get("number", "")))
        badge.setObjectName("guideStepBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(30, 30)
        outer.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)

        column = QVBoxLayout()
        column.setSpacing(7)

        title = QLabel(step.get("title", ""))
        title.setObjectName("guideStepTitle")
        title.setWordWrap(True)
        column.addWidget(title)

        for line in step.get("body", []):
            bullet = QLabel(f"·  {line}")
            bullet.setObjectName("guideBody")
            bullet.setWordWrap(True)
            column.addWidget(bullet)

        tip = step.get("tip", "")
        if tip:
            tip_label = QLabel(tip)
            tip_label.setObjectName("guideTip")
            tip_label.setWordWrap(True)
            column.addWidget(tip_label)

        outer.addLayout(column, 1)
        return card

    def _build_shortcut_card(self, shortcuts: list) -> QWidget:
        card = QFrame()
        card.setObjectName("guideCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(7)

        for item in shortcuts:
            row = QHBoxLayout()
            row.setSpacing(12)
            keys = QLabel(item.get("keys", ""))
            keys.setObjectName("guideKeys")
            keys.setFixedWidth(130)
            row.addWidget(keys)
            action = QLabel(item.get("action", ""))
            action.setObjectName("guideBody")
            row.addWidget(action, 1)
            layout.addLayout(row)

        return card

    def _build_faq_card(self, item: dict) -> QWidget:
        card = QFrame()
        card.setObjectName("guideCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)

        question = QLabel(item.get("q", ""))
        question.setObjectName("guideQuestion")
        question.setWordWrap(True)
        layout.addWidget(question)

        answer = QLabel(item.get("a", ""))
        answer.setObjectName("guideBody")
        answer.setWordWrap(True)
        layout.addWidget(answer)

        return card

    def _build_section_label(self, text: str) -> QWidget:
        label = QLabel(text)
        label.setObjectName("guideSectionLabel")
        return label

    def _build_footer(self, show_dismiss: bool) -> QWidget:
        frame = QFrame()
        frame.setObjectName("guideFooter")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(28, 14, 28, 16)
        layout.setSpacing(12)

        if show_dismiss:
            self._dismiss_checkbox = QCheckBox("다음부터 시작할 때 열지 않기")
            layout.addWidget(self._dismiss_checkbox)

        layout.addStretch(1)

        close_button = QPushButton("닫기")
        close_button.setObjectName("guidePrimaryButton")
        close_button.setDefault(True)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        return frame

    # -------------------------------------------------------------------
    # Styling
    # -------------------------------------------------------------------

    def _stylesheet(self) -> str:
        c = COLORS
        return f"""
        QDialog {{ background: {c['bg_app']}; }}

        QScrollArea {{ background: {c['bg_app']}; border: none; }}
        QScrollArea > QWidget > QWidget {{ background: {c['bg_app']}; }}

        #guideHeader {{
            background: {c['bg_card']};
            border-bottom: 1px solid {c['border_section']};
        }}
        #guideTitle {{
            font-size: 20px;
            font-weight: 700;
            color: {c['text_primary']};
        }}
        #guideIntro {{
            font-size: 13px;
            color: {c['text_secondary']};
            line-height: 150%;
        }}

        #guideStepCard {{
            background: {c['bg_card']};
            border: 1px solid {c['border_section']};
            border-radius: 10px;
        }}
        #guideCard {{
            background: {c['bg_card']};
            border: 1px solid {c['border_section']};
            border-radius: 10px;
        }}
        #guideStepBadge {{
            background: {c['accent']};
            color: {c['text_on_accent']};
            border-radius: 15px;
            font-size: 14px;
            font-weight: 700;
        }}
        #guideStepTitle {{
            font-size: 15px;
            font-weight: 700;
            color: {c['text_primary']};
        }}
        #guideSectionLabel {{
            font-size: 15px;
            font-weight: 700;
            color: {c['text_primary']};
            padding-top: 6px;
        }}
        #guideQuestion {{
            font-size: 13px;
            font-weight: 700;
            color: {c['text_primary']};
        }}
        #guideBody {{
            font-size: 13px;
            color: {c['text_secondary']};
            line-height: 152%;
        }}
        #guideTip {{
            font-size: 12px;
            color: {c['text_secondary']};
            background: {c['accent_light']};
            border-left: 3px solid {c['accent']};
            border-radius: 4px;
            padding: 8px 10px;
            line-height: 150%;
        }}
        #guideKeys {{
            font-size: 12px;
            font-weight: 700;
            color: {c['text_primary']};
            background: {c['bg_hover']};
            border: 1px solid {c['border_default']};
            border-radius: 5px;
            padding: 3px 8px;
        }}

        #guideFooter {{
            background: {c['bg_card']};
            border-top: 1px solid {c['border_section']};
        }}
        QCheckBox {{ font-size: 12px; color: {c['text_secondary']}; }}
        #guidePrimaryButton {{
            background: {c['accent']};
            color: {c['text_on_accent']};
            border: none;
            border-radius: 6px;
            padding: 8px 22px;
            font-size: 13px;
            font-weight: 600;
        }}
        #guidePrimaryButton:hover {{ background: {c['accent_hover']}; }}
        """
