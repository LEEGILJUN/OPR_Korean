"""Reusable custom widgets for the CSAT Prompt Generator."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from PySide6.QtCore import QPropertyAnimation, QTimer, Qt, QEasingCurve
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .styles import COLORS


def create_help_button(help_text: str) -> QToolButton:
    """Create a small info button that shows help text on hover."""
    button = QToolButton()
    button.setText("i")
    button.setProperty("helpButton", True)
    button.setToolTip(help_text)
    button.setCursor(Qt.CursorShape.WhatsThisCursor)
    button.setAutoRaise(False)
    button.setFixedSize(20, 20)
    return button


# ---------------------------------------------------------------------------
# blockSignals context manager
# ---------------------------------------------------------------------------
@contextmanager
def block_signals(widget: QWidget) -> Generator[None, None, None]:
    """Safely block and restore signals on a QWidget."""
    widget.blockSignals(True)
    try:
        yield
    finally:
        widget.blockSignals(False)


# ---------------------------------------------------------------------------
# Toast notification
# ---------------------------------------------------------------------------
class ToastNotification(QFrame):
    """Temporary floating notification widget."""

    def __init__(
        self,
        parent: QWidget,
        message: str,
        kind: str = "info",
        duration_ms: int = 2500,
    ) -> None:
        super().__init__(parent)
        self.setAutoFillBackground(True)

        icons = {"success": "\u2714", "error": "\u2718", "warning": "\u26A0", "info": "\u2139"}
        bg_colors = {
            "success": COLORS["success_bg"],
            "error": COLORS["danger_bg"],
            "warning": COLORS["warning_bg"],
            "info": COLORS["accent_light"],
        }
        border_colors = {
            "success": COLORS["success_border"],
            "error": COLORS["danger_border"],
            "warning": COLORS["warning_border"],
            "info": COLORS["border_primary_card"],
        }
        text_colors = {
            "success": "#065f46",
            "error": COLORS["danger_text"],
            "warning": "#92400e",
            "info": COLORS["accent"],
        }

        bg = bg_colors.get(kind, bg_colors["info"])
        border = border_colors.get(kind, border_colors["info"])
        text_color = text_colors.get(kind, text_colors["info"])
        icon = icons.get(kind, icons["info"])

        self.setStyleSheet(
            f"ToastNotification {{"
            f"  background: {bg}; border: 1px solid {border};"
            f"  border-radius: 10px; padding: 10px 16px;"
            f"}}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"color: {text_color}; font-size: 16px; background: transparent; border: none;")
        layout.addWidget(icon_label)

        text_label = QLabel(message)
        text_label.setStyleSheet(
            f"color: {text_color}; font-size: 13px; font-weight: 600;"
            f" background: transparent; border: none;"
        )
        text_label.setWordWrap(True)
        layout.addWidget(text_label, 1)

        self.adjustSize()
        self.setFixedHeight(self.sizeHint().height())

        QTimer.singleShot(duration_ms, self._fade_out)

    def _fade_out(self) -> None:
        self.hide()
        self.deleteLater()

    def show_at_top(self) -> None:
        """Position the toast at the top-center of its parent and show it."""
        parent = self.parentWidget()
        if parent is None:
            self.show()
            return
        width = min(420, parent.width() - 40)
        self.setFixedWidth(width)
        x = (parent.width() - width) // 2
        self.move(x, 16)
        self.raise_()
        self.show()


# ---------------------------------------------------------------------------
# Collapsible section
# ---------------------------------------------------------------------------
class CollapsibleSection(QWidget):
    """A section header that can show/hide its content on click."""

    def __init__(self, title: str, parent: QWidget | None = None, expanded: bool = True) -> None:
        super().__init__(parent)
        self._expanded = expanded

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header row
        self._header = QFrame()
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.setStyleSheet(
            f"QFrame {{ background: transparent; border: none; padding: 6px 0; }}"
        )
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self._arrow = QLabel("\u25BC" if expanded else "\u25B6")
        self._arrow.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 10px;"
            f" background: transparent; border: none;"
        )
        self._arrow.setFixedWidth(16)
        header_layout.addWidget(self._arrow)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        title_label.setStyleSheet("background: transparent; border: none;")
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)

        self._header.mousePressEvent = lambda e: self.toggle()
        main_layout.addWidget(self._header)

        # Content container
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 8, 0, 0)
        self._content_layout.setSpacing(10)
        self._content.setVisible(expanded)
        main_layout.addWidget(self._content)

    def content_layout(self) -> QVBoxLayout:
        """Return the layout to add child widgets into."""
        return self._content_layout

    def toggle(self) -> None:
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self._arrow.setText("\u25BC" if self._expanded else "\u25B6")

    def set_expanded(self, expanded: bool) -> None:
        if self._expanded != expanded:
            self.toggle()


# ---------------------------------------------------------------------------
# Module checkbox group
# ---------------------------------------------------------------------------
class ModuleCheckboxGroup(QWidget):
    """Compact group of module checkboxes with visible info buttons."""

    def __init__(
        self,
        module_names: list[str],
        help_texts: dict[str, str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.checkboxes: dict[str, QCheckBox] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        for name in module_names:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            cb = QCheckBox(name)
            cb.setToolTip(help_texts.get(name, ""))
            self.checkboxes[name] = cb
            row_layout.addWidget(cb)
            row_layout.addWidget(create_help_button(help_texts.get(name, "")))
            row_layout.addStretch(1)
            layout.addWidget(row)

    def selected_names(self) -> list[str]:
        return [name for name, cb in self.checkboxes.items() if cb.isChecked()]

    def set_checked(self, module_names: list[str]) -> None:
        for name, cb in self.checkboxes.items():
            cb.setChecked(name in module_names)

    def reset(self) -> None:
        for cb in self.checkboxes.values():
            cb.setChecked(False)
