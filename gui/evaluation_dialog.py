"""Verification dialog — paste generated questions back in and pick a check."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class EvaluationDialog(QDialog):
    """A room of its own for step 3.

    Verification used to live in a third splitter pane, where it competed for
    vertical space with the passage and the result and ended up cramped. It is a
    separate stage of the workflow, so it gets a separate window.
    """

    def __init__(
        self,
        mode_labels: list[str],
        describe_mode: Callable[[str], str],
        parent: QWidget | None = None,
        initial_text: str = "",
        initial_mode: str = "",
    ) -> None:
        super().__init__(parent)
        self._describe_mode = describe_mode

        self.setWindowTitle("생성 결과 검증")
        self.setMinimumSize(760, 620)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 16)
        layout.setSpacing(12)

        title = QLabel("생성 결과 검증")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        hint = QLabel(
            "LLM이 만들어 준 문항을 그대로 붙여 넣으세요. 분석 단계나 해설이 섞여 있어도 괜찮습니다.\n"
            "만들어진 검증 프롬프트는 반드시 새 대화창에서 실행하세요. "
            "문항을 만든 대화창에서 검증하면 모델이 자기가 쓴 근거에 이끌려 결함을 놓칩니다."
        )
        hint.setObjectName("sectionHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        mode_label = QLabel("검증 방식")
        mode_label.setObjectName("fieldLabel")
        mode_row.addWidget(mode_label)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(mode_labels)
        if initial_mode:
            index = self.mode_combo.findText(initial_mode)
            if index >= 0:
                self.mode_combo.setCurrentIndex(index)
        self.mode_combo.currentTextChanged.connect(self._update_description)
        mode_row.addWidget(self.mode_combo, 1)
        layout.addLayout(mode_row)

        self.description_label = QLabel("")
        self.description_label.setObjectName("sectionHint")
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label)

        self.input_edit = QPlainTextEdit()
        self.input_edit.setPlaceholderText(
            "LLM이 생성한 문항을 여기에 붙여 넣으세요..."
        )
        self.input_edit.setPlainText(initial_text)
        self.input_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.input_edit, 1)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("dialogDivider")
        layout.addWidget(divider)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        clear_button = QPushButton("붙여넣기 지우기")
        clear_button.setObjectName("iconButton")
        clear_button.clicked.connect(self.input_edit.clear)
        button_row.addWidget(clear_button)
        button_row.addStretch(1)

        cancel_button = QPushButton("취소")
        cancel_button.setObjectName("secondaryButton")
        cancel_button.clicked.connect(self.reject)
        button_row.addWidget(cancel_button)

        self.build_button = QPushButton("검증 프롬프트 생성")
        self.build_button.setObjectName("generateButton")
        self.build_button.setDefault(True)
        self.build_button.clicked.connect(self.accept)
        button_row.addWidget(self.build_button)

        layout.addLayout(button_row)

        self._update_description(self.mode_combo.currentText())
        self.input_edit.setFocus()

    # -------------------------------------------------------------------
    # Public
    # -------------------------------------------------------------------

    def selected_mode(self) -> str:
        return self.mode_combo.currentText().strip()

    def pasted_text(self) -> str:
        return self.input_edit.toPlainText().strip()

    # -------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------

    def _update_description(self, mode_label: str) -> None:
        self.description_label.setText(self._describe_mode(mode_label.strip()))
