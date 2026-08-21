"""Main application window — redesigned layout with improved UX."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontDatabase, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.file_utils import (
    build_default_filename,
    build_export_content,
    current_timestamp,
    ensure_file_extension,
    parse_export_content,
    save_text_file,
)
from core.app_settings import AppSettings
from core.evaluation_builder import EvaluationBuildError, EvaluationBuilder
from core.history_store import GenerationHistoryStore, HistoryStoreError
from core.models import (
    EvaluationRequest,
    PromptExportData,
    PromptPreset,
    PromptRequest,
    VariationPlan,
)
from core.preset_loader import PresetLoadError, PresetLoader, PresetSaveError
from core.prompt_builder import PromptBuilder
from core.template_loader import CategorySaveError, TemplateLoadError, TemplateLoader

from .evaluation_dialog import EvaluationDialog
from .guide_dialog import GuideDialog
from .styles import apply_theme, build_stylesheet
from .widgets import (
    CollapsibleSection,
    ModuleCheckboxGroup,
    QuestionTypePicker,
    StepIndicator,
    ToastNotification,
    block_signals,
    create_help_button,
)


class MainWindow(QMainWindow):
    """Main application window with redesigned layout."""

    # -------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------

    VERSION_DESCRIPTIONS = {
        "기본형": "빠르게 초안을 뽑는 용도입니다. 결과는 간결하고 바로 복사해 쓰기 좋게 정리됩니다.",
        "고급형": "정답 근거, 오답 설계 이유, 변별 포인트까지 함께 보려는 용도입니다. 교사용 검토에 더 적합합니다.",
        "Ultimate형": "출제 의도, 난이도 조절 이유, 자체 점검까지 포함하는 가장 강한 버전입니다. 완성도 검토용에 가깝습니다.",
    }

    FIELD_HELP_TEXTS = {
        "preset": "자주 사용하는 설정 조합입니다. 적용을 누르면 출제영역, 버전, 난이도, 문항 수, 모듈이 한 번에 채워집니다.",
        "exam_mode": "무엇을 대비하는 자료인지 고릅니다. 수능·모의고사는 1~9등급 축을, 중·고 내신은 기초~최고난도 축을 사용하고 교과 연계 입력란이 열립니다.",
        "output_type": "만들 자료의 형태를 고릅니다. 문항만 만들지, 개념 정리와 작품 해제까지 포함한 학습지를 만들지, 해제만 만들지에 따라 프롬프트가 통째로 달라집니다.",
        "curriculum": "교과서 출판사, 학년, 단원명을 적으면 그 단원의 학습 목표에 맞춰 설계합니다. 예: [비상] 국어2 Ⅰ. 나, 너, 우리가 만나는 길 (1) 문학의 해석과 생활화",
        "category": "출제할 수능 국어 영역 또는 사용자 정의 유형을 고릅니다. 선택한 유형에 따라 분석 지시와 문항 설계 기준이 달라집니다.",
        "version": "프롬프트의 설계 강도를 고릅니다. 기본형은 간결하고, 고급형은 구조화가 강화되며, Ultimate형은 해석 통제와 자기 점검까지 더 강하게 요구합니다.",
        "difficulty": "수능 상대평가 등급 목표를 고릅니다. 1등급은 최상위권 변별용, 9등급은 기초 확인용입니다.",
        "question_count": "한 번에 생성할 문항 수입니다.",
        "question_style": "문항 형식을 고릅니다. 객관식 5지선다는 수능 기본형에 가깝고, 4지선다·3지선다·서술형도 선택할 수 있습니다.",
        "set_style": "문항을 지문 세트형으로 묶을지, 독립 문항으로 낼지 정합니다.",
        "answer_layout": "해설을 어디에 둘지 정합니다. '문항 바로 뒤에'는 검토하기 좋고, '맨 뒤에 모아서'는 학생에게 나눠 줄 시험지로 바로 쓸 수 있습니다.",
        "scoring_scheme": "배점 구조를 정합니다. 수능 국어는 일반적으로 2점·3점 혼합 배점을 사용합니다.",
        "passage": "문항 생성의 기준이 되는 지문입니다. 비워둘 수 없으며, 가장 중요한 입력입니다.",
        "example": "수능 국어에서 말하는 '보기'나 추가 제시문을 넣는 칸입니다. 작품 해설 자료, 비교 자료, 학생 반응, 도표 설명처럼 문항 설계에 함께 참고해야 하는 보조 자료를 입력합니다. 문항의 선택지를 넣는 칸은 아닙니다.",
        "modules": "보조 지시를 추가하는 옵션입니다. 선택한 모듈만 최종 프롬프트에 포함됩니다.",
        "generate": "현재 입력된 지문과 설정을 바탕으로 최종 프롬프트를 생성합니다.",
        "reset": "입력값과 선택 상태, 생성 결과를 모두 초기화합니다.",
        "copy": "생성된 최종 프롬프트 전체를 클립보드에 복사합니다.",
        "save_txt": "생성된 프롬프트와 메타데이터를 UTF-8 .txt 파일로 저장합니다.",
        "save_md": "생성된 프롬프트와 메타데이터를 Markdown 파일로 저장합니다.",
        "add_category": "현재 앱에 없는 새로운 출제영역을 추가합니다.",
        "delete_category": "선택한 사용자 정의 출제영역을 삭제합니다. 기본 제공 출제영역은 삭제할 수 없습니다.",
        "round": "같은 지문으로 몇 번째 생성인지 보여 줍니다. 회차가 올라가면 이전 회차에서 쓰지 않은 문항 유형과 다른 지문 지점을 우선 겨냥하도록 프롬프트가 바뀝니다.",
        "reset_history": "이 지문의 생성 이력을 지웁니다. 지우면 다음 생성이 다시 1회차로 시작합니다.",
        "evaluation": "LLM이 만들어 준 문항을 여기에 그대로 붙여 넣으면, 그 문항이 잘 만들어졌는지 점검하는 '검증 프롬프트'를 만들어 줍니다. 그 프롬프트를 새 대화창에 붙여 넣어 실행하세요.",
        "load": "이전에 저장한 .txt 또는 .md 아카이브에서 지문과 보기를 다시 불러옵니다. 설정은 파일에 기록된 값으로 맞춥니다.",
        "theme": "밝은 화면과 어두운 화면을 전환합니다. 선택은 저장되어 다음 실행에도 유지됩니다.",
        "font_size": "글자 크기를 조절합니다. 80%에서 150%까지 바꿀 수 있습니다.",
        "question_types": "문항마다 어떤 유형을 낼지 정합니다. 자동이면 앱이 서로 다른 유형을 배분하고, 같은 지문을 다시 쓸 때 지난 회차에 쓴 유형을 피합니다. 직접 고르면 선택한 유형만 사용합니다.",
        "evaluation_mode": "무엇을 점검할지 고릅니다. 블라인드 풀이는 정답을 지우고 직접 풀게 해 복수 정답을 잡아내고, 정밀 검토는 근거와 선지 설계를 진단하며, 난이도 점검은 목표 등급에 실제로 맞는지 봅니다.",
    }

    MODULE_HELP_TEXTS = {
        "Anchor Setting 포함": "해석의 기준점이 되는 핵심 표현과 개념을 먼저 고정하도록 요구합니다.",
        "CoT 포함": "문항 설계 전에 단계적 분석과 근거 검토를 강화합니다.",
        "Self-Correction 포함": "초안 작성 후 모호성, 복수 정답 가능성, 해석 위반 여부를 다시 점검합니다.",
        "오답 유형 라벨링 포함": "오답 선지에 오류 유형 라벨을 붙여 설계 의도를 분명하게 만듭니다.",
        "난이도 미세조정 포함": "선택한 등급은 유지한 채, 같은 등급 안에서 선지 간 거리와 변별도를 더 정교하게 맞추게 합니다.",
    }

    APPROX_CHARS_PER_TOKEN = 3.5  # Korean text rough estimate

    # -------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------

    def __init__(self) -> None:
        super().__init__()
        self.template_loader = TemplateLoader()
        self.preset_loader = PresetLoader()
        self.prompt_builder = PromptBuilder(self.template_loader)
        self.history_store = GenerationHistoryStore()
        self.evaluation_builder = EvaluationBuilder(self.template_loader)
        self.app_settings = AppSettings()
        self.presets_by_label: dict[str, PromptPreset] = {}
        self.preset_load_error_message: str = ""
        self.evaluation_load_error_message: str = ""
        self.setup_load_error_message: str = ""
        self.last_generated_request: PromptRequest | None = None
        self.last_generated_prompt: str = ""
        self.last_variation_plan: VariationPlan | None = None
        self.output_kind: str = "prompt"  # "prompt" | "evaluation"
        self.last_evaluation_text: str = ""
        self.last_evaluation_mode: str = ""
        self._preview_timer: QTimer | None = None

        self._build_ui()
        self._setup_shortcuts()
        QTimer.singleShot(0, self._on_startup)

    # ===================================================================
    # UI CONSTRUCTION
    # ===================================================================

    def _build_ui(self) -> None:
        self.setWindowTitle("수능 국어 프롬프트 생성기")
        self.resize(1400, 900)
        self.setMinimumSize(1100, 720)
        apply_theme(str(self.app_settings.get("theme")))

        root = QWidget()
        root.setObjectName("rootWidget")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(16, 14, 16, 10)
        root_layout.setSpacing(12)

        # -- Top toolbar (preset bar) --
        root_layout.addWidget(self._build_toolbar())

        # -- Main content: sidebar | center+output --
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)
        splitter.setChildrenCollapsible(False)

        splitter.addWidget(self._build_sidebar())
        splitter.addWidget(self._build_center_area())

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)
        splitter.setSizes([340, 1040])
        root_layout.addWidget(splitter, 1)

        # -- Bottom action bar (always visible) --
        root_layout.addWidget(self._build_bottom_bar())

        self.setCentralWidget(root)

        status_bar = QStatusBar()
        status_bar.showMessage("지문을 입력한 뒤 프롬프트 생성 버튼을 누르세요.  |  Ctrl+Enter: 생성  |  Ctrl+Shift+C: 복사")
        self.setStatusBar(status_bar)

        self._apply_appearance()
        self._on_exam_mode_changed(self.exam_mode_combo.currentText())
        self._reload_output_types()

    # -------------------------------------------------------------------
    # Toolbar (preset bar at top)
    # -------------------------------------------------------------------

    def _build_toolbar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("toolbarFrame")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        # App title
        title = QLabel("수능 국어 프롬프트 생성기")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        layout.addSpacing(20)

        # Preset section
        layout.addWidget(self._make_field_label("자주 사용하는 설정", self.FIELD_HELP_TEXTS["preset"]))

        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(220)
        self.preset_combo.addItem("직접 설정")
        self.preset_combo.setToolTip(self.FIELD_HELP_TEXTS["preset"])
        self._load_presets_into_ui()
        self.preset_combo.currentTextChanged.connect(self._update_preset_description)
        layout.addWidget(self.preset_combo)

        self.apply_preset_button = QPushButton("적용")
        self.apply_preset_button.setObjectName("secondaryButton")
        self.apply_preset_button.setToolTip("선택한 프리셋 설정을 현재 입력값에 반영합니다.")
        self.apply_preset_button.clicked.connect(self.apply_selected_preset)
        layout.addWidget(self.apply_preset_button)

        self.save_preset_button = QPushButton("+ 프리셋 저장")
        self.save_preset_button.setObjectName("iconButton")
        self.save_preset_button.setToolTip("현재 설정을 새 프리셋으로 저장합니다.")
        self.save_preset_button.clicked.connect(self.save_current_as_preset)
        layout.addWidget(self.save_preset_button)

        self.delete_preset_button = QPushButton("삭제")
        self.delete_preset_button.setObjectName("iconButton")
        self.delete_preset_button.setToolTip("선택한 프리셋을 제거합니다.")
        self.delete_preset_button.clicked.connect(self.delete_selected_preset)
        self.delete_preset_button.setEnabled(False)
        layout.addWidget(self.delete_preset_button)

        layout.addStretch(1)

        # Preset description
        self.preset_description_label = QLabel("자주 사용하는 설정 조합을 빠르게 불러올 수 있습니다.")
        self.preset_description_label.setObjectName("appSubtitle")
        self.preset_description_label.setStyleSheet("border: none;")
        self.preset_description_label.setMaximumWidth(400)
        self.preset_description_label.setWordWrap(True)
        layout.addWidget(self.preset_description_label)

        layout.addSpacing(16)

        self.theme_button = QPushButton("")
        self.theme_button.setObjectName("iconButton")
        self.theme_button.setToolTip(self.FIELD_HELP_TEXTS["theme"])
        self.theme_button.clicked.connect(self.toggle_theme)
        layout.addWidget(self.theme_button)

        self.font_smaller_button = QPushButton("A-")
        self.font_smaller_button.setObjectName("iconButton")
        self.font_smaller_button.setToolTip(self.FIELD_HELP_TEXTS["font_size"])
        self.font_smaller_button.clicked.connect(lambda: self.adjust_font_scale(-10))
        layout.addWidget(self.font_smaller_button)

        self.font_larger_button = QPushButton("A+")
        self.font_larger_button.setObjectName("iconButton")
        self.font_larger_button.setToolTip(self.FIELD_HELP_TEXTS["font_size"])
        self.font_larger_button.clicked.connect(lambda: self.adjust_font_scale(10))
        layout.addWidget(self.font_larger_button)

        self.guide_button = QPushButton("사용 방법")
        self.guide_button.setObjectName("secondaryButton")
        self.guide_button.setToolTip("이 앱을 쓰는 순서와 자주 묻는 질문을 봅니다.  (F1)")
        self.guide_button.clicked.connect(lambda: self.show_user_guide())
        layout.addWidget(self.guide_button)

        return frame

    # -------------------------------------------------------------------
    # Sidebar (settings)
    # -------------------------------------------------------------------

    def _build_sidebar(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("sidebarPanel")

        outer_layout = QVBoxLayout(panel)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("sidebarScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 14, 14, 14)
        content_layout.setSpacing(6)

        # -- Category section --
        purpose_section = CollapsibleSection("무엇을 만들까", expanded=True)
        pl = purpose_section.content_layout()

        pl.addWidget(self._make_field_label("평가 맥락", self.FIELD_HELP_TEXTS["exam_mode"]))
        self.exam_mode_combo = QComboBox()
        self.exam_mode_combo.setToolTip(self.FIELD_HELP_TEXTS["exam_mode"])
        try:
            self.exam_mode_combo.addItems(self.template_loader.exam_mode_labels())
        except TemplateLoadError as exc:
            self.setup_load_error_message = str(exc)
        self.exam_mode_combo.currentTextChanged.connect(self._on_exam_mode_changed)
        pl.addWidget(self.exam_mode_combo)

        pl.addWidget(self._make_field_label("산출물 유형", self.FIELD_HELP_TEXTS["output_type"]))
        self.output_type_combo = QComboBox()
        self.output_type_combo.setToolTip(self.FIELD_HELP_TEXTS["output_type"])
        try:
            self.output_type_combo.addItems(self.template_loader.output_type_labels())
        except TemplateLoadError as exc:
            self.setup_load_error_message = str(exc)
        self.output_type_combo.currentTextChanged.connect(self._on_output_type_changed)
        pl.addWidget(self.output_type_combo)

        self.output_type_description_label = QLabel("")
        self.output_type_description_label.setObjectName("sectionHint")
        self.output_type_description_label.setWordWrap(True)
        pl.addWidget(self.output_type_description_label)

        self.curriculum_label = self._make_field_label("교과 연계", self.FIELD_HELP_TEXTS["curriculum"])
        pl.addWidget(self.curriculum_label)
        self.curriculum_edit = QLineEdit()
        self.curriculum_edit.setPlaceholderText("[비상] 국어2 Ⅰ. 나, 너, 우리가 만나는 길 (1) …")
        self.curriculum_edit.setToolTip(self.FIELD_HELP_TEXTS["curriculum"])
        pl.addWidget(self.curriculum_edit)

        content_layout.addWidget(purpose_section)

        cat_section = CollapsibleSection("출제 영역", expanded=True)
        cl = cat_section.content_layout()

        cl.addWidget(self._make_field_label("출제 영역", self.FIELD_HELP_TEXTS["category"]))
        self.category_combo = QComboBox()
        self.category_combo.addItems(self.template_loader.category_names())
        self.category_combo.setToolTip(self.FIELD_HELP_TEXTS["category"])
        self.category_combo.currentTextChanged.connect(self._update_category_actions)
        cl.addWidget(self.category_combo)

        cat_btn_row = QHBoxLayout()
        cat_btn_row.setSpacing(6)
        self.add_category_button = QPushButton("+ 새 유형")
        self.add_category_button.setObjectName("iconButton")
        self.add_category_button.setToolTip(self.FIELD_HELP_TEXTS["add_category"])
        self.add_category_button.clicked.connect(self.add_custom_category)
        self.delete_category_button = QPushButton("삭제")
        self.delete_category_button.setObjectName("iconButton")
        self.delete_category_button.setToolTip(self.FIELD_HELP_TEXTS["delete_category"])
        self.delete_category_button.clicked.connect(self.delete_selected_category)
        self.delete_category_button.setEnabled(False)
        cat_btn_row.addWidget(self.add_category_button)
        cat_btn_row.addWidget(self.delete_category_button)
        cat_btn_row.addStretch(1)
        cl.addLayout(cat_btn_row)

        content_layout.addWidget(cat_section)

        # -- Version & Difficulty --
        ver_section = CollapsibleSection("버전 & 난이도", expanded=True)
        vl = ver_section.content_layout()

        vl.addWidget(self._make_field_label("프롬프트 버전", self.FIELD_HELP_TEXTS["version"]))
        self.version_combo = QComboBox()
        self.version_combo.addItems(self.template_loader.version_names())
        self.version_combo.setToolTip(self.FIELD_HELP_TEXTS["version"])
        self.version_combo.currentTextChanged.connect(self._update_version_description)
        vl.addWidget(self.version_combo)

        self.version_description_label = QLabel(
            self.VERSION_DESCRIPTIONS.get(self.version_combo.currentText(), "")
        )
        self.version_description_label.setObjectName("sectionHint")
        self.version_description_label.setWordWrap(True)
        vl.addWidget(self.version_description_label)

        vl.addSpacing(4)

        vl.addWidget(self._make_field_label("난이도 수준", self.FIELD_HELP_TEXTS["difficulty"]))
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(self.template_loader.difficulty_names())
        self.difficulty_combo.setToolTip(self.FIELD_HELP_TEXTS["difficulty"])
        vl.addWidget(self.difficulty_combo)

        content_layout.addWidget(ver_section)

        # -- Question settings --
        q_section = CollapsibleSection("문항 설정", expanded=True)
        ql = q_section.content_layout()

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        grid.addWidget(self._make_field_label("문항 수", self.FIELD_HELP_TEXTS["question_count"]), 0, 0)
        self.question_count_spin = QSpinBox()
        self.question_count_spin.setRange(1, 80)
        self.question_count_spin.setValue(1)
        self.question_count_spin.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.question_count_spin.setToolTip(self.FIELD_HELP_TEXTS["question_count"])
        self.question_count_spin.valueChanged.connect(lambda _: self._update_passage_count())
        grid.addWidget(self.question_count_spin, 0, 1)

        grid.addWidget(self._make_field_label("문항 형식", self.FIELD_HELP_TEXTS["question_style"]), 1, 0)
        self.question_style_combo = QComboBox()
        self.question_style_combo.addItems([
            "객관식 5지선다", "객관식 4지선다", "객관식 3지선다",
            "단답형", "서술형", "객관식·단답형·서술형 혼합",
            "빈칸 채우기", "OX 진위 판단",
        ])
        self.question_style_combo.setToolTip(self.FIELD_HELP_TEXTS["question_style"])
        grid.addWidget(self.question_style_combo, 1, 1)

        grid.addWidget(self._make_field_label("출제 묶음", self.FIELD_HELP_TEXTS["set_style"]), 2, 0)
        self.set_style_combo = QComboBox()
        self.set_style_combo.addItems(["지문 세트형(수능형)", "독립 문항형", "혼합형"])
        self.set_style_combo.setToolTip(self.FIELD_HELP_TEXTS["set_style"])
        grid.addWidget(self.set_style_combo, 2, 1)

        grid.addWidget(self._make_field_label("배점 구조", self.FIELD_HELP_TEXTS["scoring_scheme"]), 3, 0)
        self.scoring_scheme_combo = QComboBox()
        self.scoring_scheme_combo.addItems(["수능형 2점·3점 혼합", "균등 배점", "고난도 3점 중심"])
        self.scoring_scheme_combo.setToolTip(self.FIELD_HELP_TEXTS["scoring_scheme"])
        grid.addWidget(self.scoring_scheme_combo, 3, 1)

        grid.addWidget(self._make_field_label("해설 배치", self.FIELD_HELP_TEXTS["answer_layout"]), 4, 0)
        self.answer_layout_combo = QComboBox()
        self.answer_layout_combo.addItems(["문항 바로 뒤에 해설", "해설은 맨 뒤에 모아서"])
        self.answer_layout_combo.setToolTip(self.FIELD_HELP_TEXTS["answer_layout"])
        grid.addWidget(self.answer_layout_combo, 4, 1)

        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 3)
        ql.addLayout(grid)

        self.manual_types_checkbox = QCheckBox("문항 유형 직접 고르기")
        self.manual_types_checkbox.setToolTip(self.FIELD_HELP_TEXTS["question_types"])
        self.manual_types_checkbox.toggled.connect(self._on_manual_types_toggled)
        ql.addWidget(self.manual_types_checkbox)

        self.question_type_hint = QLabel(
            "자동: 문항마다 다른 유형을 배분하고, 회차가 바뀌면 지난 유형을 피합니다."
        )
        self.question_type_hint.setObjectName("sectionHint")
        self.question_type_hint.setWordWrap(True)
        ql.addWidget(self.question_type_hint)

        self.question_type_picker = QuestionTypePicker()
        self.question_type_picker.setVisible(False)
        ql.addWidget(self.question_type_picker)

        content_layout.addWidget(q_section)

        # -- Modules --
        mod_section = CollapsibleSection("추가 모듈", expanded=True)
        ml = mod_section.content_layout()

        ml.addWidget(self._make_field_label("추가 모듈", self.FIELD_HELP_TEXTS["modules"]))
        self.module_group = ModuleCheckboxGroup(
            self.template_loader.module_names(),
            self.MODULE_HELP_TEXTS,
        )
        ml.addWidget(self.module_group)

        content_layout.addWidget(mod_section)

        content_layout.addStretch(1)

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

        self._update_category_actions(self.category_combo.currentText())
        self._update_preset_description(self.preset_combo.currentText())

        return panel

    # -------------------------------------------------------------------
    # Center area (input + output)
    # -------------------------------------------------------------------

    def _build_center_area(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Workflow stages, so the copy-paste round trip is visible up front.
        self.step_indicator = StepIndicator(
            ["지문 · 설정 입력", "프롬프트 생성 → LLM에 붙여넣기", "결과 되붙여넣고 검증"]
        )
        layout.addWidget(self.step_indicator)

        # Vertical splitter: input / output / verification
        self.center_splitter = QSplitter(Qt.Orientation.Vertical)
        self.center_splitter.setHandleWidth(6)
        self.center_splitter.setChildrenCollapsible(False)

        self.center_splitter.addWidget(self._build_input_area())
        self.center_splitter.addWidget(self._build_output_area())

        self.center_splitter.setStretchFactor(0, 4)
        self.center_splitter.setStretchFactor(1, 6)
        self.center_splitter.setSizes([340, 500])

        layout.addWidget(self.center_splitter, 1)
        layout.addWidget(self._build_evaluation_bar())
        return panel

    def _build_evaluation_bar(self) -> QWidget:
        """Slim launcher for step 3 — the work itself happens in a dialog.

        Verification used to be a third splitter pane, where it fought the passage
        and the result for vertical space and got squeezed until its contents
        overlapped. It is a separate stage, so it gets a separate window.
        """
        frame = QFrame()
        frame.setObjectName("toolbarFrame")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(12)

        label = QLabel("③ 생성 결과 검증")
        label.setObjectName("fieldLabel")
        layout.addWidget(label)

        hint = QLabel("LLM이 만든 문항을 붙여 넣으면 잘 만들어졌는지 점검하는 프롬프트를 만들어 드립니다.")
        hint.setObjectName("sectionHint")
        layout.addWidget(hint)
        layout.addStretch(1)

        self.open_evaluation_button = QPushButton("검증 창 열기")
        self.open_evaluation_button.setObjectName("secondaryButton")
        self.open_evaluation_button.setToolTip(self.FIELD_HELP_TEXTS["evaluation"] + "  (Ctrl+E)")
        self.open_evaluation_button.clicked.connect(self.build_evaluation_prompt)
        layout.addWidget(self.open_evaluation_button)

        return frame

    def _build_input_area(self) -> QWidget:
        card = QFrame()
        card.setObjectName("primarySectionCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(8)
        header.addWidget(self._make_section_title_with_help("지문 입력", self.FIELD_HELP_TEXTS["passage"]))
        header.addStretch(1)

        self.passage_hint_label = QLabel("문항의 기준이 되는 지문을 입력하세요. 가장 중요한 입력입니다.")
        self.passage_hint_label.setObjectName("sectionHint")
        header.addWidget(self.passage_hint_label)

        self.passage_count_label = QLabel("")
        self.passage_count_label.setObjectName("tokenCounter")
        header.addWidget(self.passage_count_label)

        self.round_label = QLabel("")
        self.round_label.setObjectName("sectionHint")
        self.round_label.setToolTip(self.FIELD_HELP_TEXTS["round"])
        header.addWidget(self.round_label)

        self.reset_history_button = QPushButton("이력 초기화")
        self.reset_history_button.setObjectName("iconButton")
        self.reset_history_button.setToolTip(self.FIELD_HELP_TEXTS["reset_history"])
        self.reset_history_button.clicked.connect(self.reset_passage_history)
        self.reset_history_button.setVisible(False)
        header.addWidget(self.reset_history_button)

        layout.addLayout(header)

        # Passage
        self.passage_edit = QPlainTextEdit()
        self.passage_edit.setPlaceholderText("문항 생성에 사용할 지문을 입력하세요...")
        self.passage_edit.setToolTip(self.FIELD_HELP_TEXTS["passage"])
        self.passage_edit.setMinimumHeight(70)
        self.passage_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.passage_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.passage_edit.textChanged.connect(self._schedule_preview_update)
        layout.addWidget(self.passage_edit, 1)

        # Example (collapsible)
        example_header = QHBoxLayout()
        example_header.setSpacing(8)
        example_header.addWidget(self._make_field_label("보기 / 추가 제시문", self.FIELD_HELP_TEXTS["example"]))
        example_hint = QLabel("(선택사항 — 없으면 비워두세요)")
        example_hint.setObjectName("sectionHint")
        example_header.addWidget(example_hint)
        example_header.addStretch(1)
        layout.addLayout(example_header)

        self.example_edit = QPlainTextEdit()
        self.example_edit.setPlaceholderText("보기 또는 추가 제시문이 있으면 입력하세요...")
        self.example_edit.setToolTip(self.FIELD_HELP_TEXTS["example"])
        self.example_edit.setMinimumHeight(52)
        self.example_edit.setMaximumHeight(120)
        self.example_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.example_edit.textChanged.connect(self._schedule_preview_update)
        layout.addWidget(self.example_edit)

        return card

    def _build_output_area(self) -> QWidget:
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # Header
        header = QHBoxLayout()
        header.setSpacing(8)
        self.output_title_label = QLabel("생성 결과")
        self.output_title_label.setObjectName("sectionTitle")
        header.addWidget(self.output_title_label)

        self.output_summary_label = QLabel("")
        self.output_summary_label.setObjectName("sectionHint")
        header.addWidget(self.output_summary_label)
        header.addStretch(1)

        self.token_label = QLabel("")
        self.token_label.setObjectName("tokenCounter")
        header.addWidget(self.token_label)
        layout.addLayout(header)

        # Output text
        self.output_edit = QPlainTextEdit()
        self.output_edit.setObjectName("outputEditor")
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText("프롬프트 생성 버튼을 누르면 결과가 여기에 표시됩니다.")
        self.output_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.output_edit.setTabStopDistance(28)
        self.output_edit.setMinimumHeight(70)
        self.output_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        fixed_font.setPointSize(max(fixed_font.pointSize(), 11))
        self.output_edit.setFont(fixed_font)
        layout.addWidget(self.output_edit, 1)

        # Action row
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.copy_button = QPushButton("클립보드 복사")
        self.copy_button.setObjectName("secondaryButton")
        self.copy_button.setToolTip(self.FIELD_HELP_TEXTS["copy"] + "  (Ctrl+Shift+C)")
        self.copy_button.clicked.connect(self.copy_output)
        action_row.addWidget(self.copy_button)

        self.save_txt_button = QPushButton(".txt 저장")
        self.save_txt_button.setObjectName("secondaryButton")
        self.save_txt_button.setToolTip(self.FIELD_HELP_TEXTS["save_txt"] + "  (Ctrl+S)")
        self.save_txt_button.clicked.connect(lambda: self.save_output("txt"))
        action_row.addWidget(self.save_txt_button)

        self.save_md_button = QPushButton(".md 저장")
        self.save_md_button.setObjectName("secondaryButton")
        self.save_md_button.setToolTip(self.FIELD_HELP_TEXTS["save_md"] + "  (Ctrl+Shift+S)")
        self.save_md_button.clicked.connect(lambda: self.save_output("md"))
        action_row.addWidget(self.save_md_button)

        action_row.addStretch(1)

        self.load_button = QPushButton("불러오기")
        self.load_button.setObjectName("iconButton")
        self.load_button.setToolTip(self.FIELD_HELP_TEXTS["load"])
        self.load_button.clicked.connect(self.load_saved_archive)
        action_row.addWidget(self.load_button)

        layout.addLayout(action_row)

        self._set_output_buttons_enabled(False)
        return card

    # -------------------------------------------------------------------
    # Bottom action bar (always visible)
    # -------------------------------------------------------------------

    def _build_bottom_bar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("toolbarFrame")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        self.generate_button = QPushButton("  프롬프트 생성  ")
        self.generate_button.setObjectName("generateButton")
        self.generate_button.setToolTip(self.FIELD_HELP_TEXTS["generate"] + "  (Ctrl+Enter)")
        self.generate_button.clicked.connect(self.generate_prompt)
        layout.addWidget(self.generate_button)

        layout.addStretch(1)

        self.reset_button = QPushButton("초기화")
        self.reset_button.setObjectName("dangerButton")
        self.reset_button.setToolTip(self.FIELD_HELP_TEXTS["reset"] + "  (Ctrl+R)")
        self.reset_button.clicked.connect(self._confirm_reset)
        layout.addWidget(self.reset_button)

        return frame

    # -------------------------------------------------------------------
    # Keyboard shortcuts
    # -------------------------------------------------------------------

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+Return"), self, self.generate_prompt)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, self.copy_output)
        QShortcut(QKeySequence("Ctrl+S"), self, lambda: self.save_output("txt"))
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, lambda: self.save_output("md"))
        QShortcut(QKeySequence("Ctrl+R"), self, self._confirm_reset)
        QShortcut(QKeySequence("F1"), self, self.show_user_guide)
        QShortcut(QKeySequence("Ctrl+E"), self, self.build_evaluation_prompt)

    # ===================================================================
    # ACTIONS
    # ===================================================================

    def generate_prompt(self) -> None:
        """Generate the final prompt from selected options."""
        request = self._build_request_from_inputs()
        if request is None:
            return

        previous_runs = self.history_store.load_runs(request.passage, request.category)
        try:
            variation = self.prompt_builder.plan_variation(
                request, previous_runs, self._selected_manual_types()
            )
            final_prompt = self.prompt_builder.build(request, variation)
        except TemplateLoadError as exc:
            QMessageBox.warning(self, "템플릿 확인 필요", str(exc))
            self._toast("템플릿을 불러오지 못했습니다.", "error")
            return
        except Exception as exc:
            QMessageBox.critical(
                self,
                "프롬프트 생성 오류",
                f"프롬프트 생성 중 예상하지 못한 오류가 발생했습니다.\n\n{exc}",
            )
            self._toast("예상치 못한 오류가 발생했습니다.", "error")
            return

        if variation is not None:
            self.history_store.record(request, variation)

        self.output_edit.setPlainText(final_prompt)
        self.output_title_label.setText("생성 결과")
        self.output_kind = "prompt"
        self._set_workflow_step(1)
        self.last_generated_request = request
        self.last_generated_prompt = final_prompt
        self.last_variation_plan = variation
        self._set_output_buttons_enabled(True)
        self._update_token_count(final_prompt)
        self._update_output_summary(variation)
        self._toast(self._variation_toast_message(variation), "success")
        self.statusBar().showMessage(self._variation_status_message(variation))
        self._refresh_round_indicator()

    def show_user_guide(self, *, first_run: bool = False) -> None:
        """Open the usage walkthrough."""
        try:
            guide = self.template_loader.load_user_guide()
        except TemplateLoadError as exc:
            QMessageBox.warning(self, "사용 안내를 불러올 수 없습니다", str(exc))
            return
        if not guide:
            QMessageBox.information(
                self,
                "사용 안내 없음",
                "사용 안내 파일을 찾을 수 없습니다.\nconfig/user_guide.json 을 확인해 주세요.",
            )
            return

        dialog = GuideDialog(guide, self, show_dismiss=first_run)
        dialog.exec()
        if first_run and dialog.dismissed_forever():
            self.app_settings.set("guide_seen", True)

    def _on_startup(self) -> None:
        """Restore the previous session, then show the guide on first launch."""
        self._restore_session()
        self._maybe_show_guide_on_startup()

    def _maybe_show_guide_on_startup(self) -> None:
        """Show the walkthrough the first time this user opens the app."""
        if self.app_settings.get("guide_seen"):
            return
        self.show_user_guide(first_run=True)

    def load_saved_archive(self) -> None:
        """Restore passage, example, and settings from a saved .txt/.md archive."""
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "저장한 프롬프트 불러오기",
            str(Path.home()),
            "프롬프트 파일 (*.txt *.md);;모든 파일 (*.*)",
        )
        if not selected_path:
            return

        try:
            content = Path(selected_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            QMessageBox.warning(
                self,
                "불러오기 실패",
                f"파일을 읽지 못했습니다.\n\n{exc}\n\nUTF-8로 저장된 파일인지 확인해 주세요.",
            )
            return

        parsed = parse_export_content(content)
        passage = parsed.get("passage", "").strip()
        if not passage:
            QMessageBox.warning(
                self,
                "지문을 찾지 못했습니다",
                "이 파일에서 지문을 찾지 못했습니다.\n"
                "이 앱에서 저장한 .txt 또는 .md 파일인지 확인해 주세요.",
            )
            return

        self.passage_edit.setPlainText(passage)
        self.example_edit.setPlainText(parsed.get("example_text", ""))
        self._set_combo_text(self.category_combo, parsed.get("category", ""))
        self._set_combo_text(self.version_combo, parsed.get("version", ""))
        self._set_combo_text(self.difficulty_combo, parsed.get("difficulty", ""))

        raw_count = parsed.get("question_count", "")
        if raw_count.isdigit():
            count = int(raw_count)
            spin = self.question_count_spin
            if spin.minimum() <= count <= spin.maximum():
                spin.setValue(count)

        self._clear_generated_output()
        self._refresh_round_indicator()
        self._update_passage_count()
        self._toast(f"불러왔습니다: {Path(selected_path).name}", "success")

    # -------------------------------------------------------------------
    # Appearance
    # -------------------------------------------------------------------

    def _apply_appearance(self) -> None:
        """Re-apply theme and font scale across the window."""
        theme = str(self.app_settings.get("theme"))
        scale = int(self.app_settings.get("font_scale") or 100)
        apply_theme(theme)
        self.setStyleSheet(build_stylesheet(scale))

        # Widgets that set colors inline cannot be reached by the stylesheet.
        for section in self.findChildren(CollapsibleSection):
            section.refresh_theme()
        if hasattr(self, "step_indicator"):
            self.step_indicator.refresh_theme()

        self.theme_button.setText("라이트" if theme == "dark" else "다크")
        self.font_smaller_button.setEnabled(scale > 80)
        self.font_larger_button.setEnabled(scale < 150)

    def toggle_theme(self) -> None:
        theme = "light" if str(self.app_settings.get("theme")) == "dark" else "dark"
        self.app_settings.set("theme", theme)
        self._apply_appearance()
        self._on_exam_mode_changed(self.exam_mode_combo.currentText())
        self._reload_output_types()
        self._toast("어두운 화면으로 바꿨습니다." if theme == "dark" else "밝은 화면으로 바꿨습니다.", "info")

    def adjust_font_scale(self, delta: int) -> None:
        scale = int(self.app_settings.get("font_scale") or 100)
        new_scale = max(80, min(150, scale + delta))
        if new_scale == scale:
            return
        self.app_settings.set("font_scale", new_scale)
        self._apply_appearance()
        self._on_exam_mode_changed(self.exam_mode_combo.currentText())
        self._reload_output_types()
        self._toast(f"글자 크기 {new_scale}%", "info")

    # -------------------------------------------------------------------
    # Session restore
    # -------------------------------------------------------------------

    def _capture_session(self) -> dict:
        """Snapshot the current inputs so the next launch can restore them."""
        return {
            "passage": self.passage_edit.toPlainText(),
            "example": self.example_edit.toPlainText(),
            "exam_mode": "무엇을 대비하는 자료인지 고릅니다. 수능·모의고사는 1~9등급 축을, 중·고 내신은 기초~최고난도 축을 사용하고 교과 연계 입력란이 열립니다.",
        "output_type": "만들 자료의 형태를 고릅니다. 문항만 만들지, 개념 정리와 작품 해제까지 포함한 학습지를 만들지, 해제만 만들지에 따라 프롬프트가 통째로 달라집니다.",
        "curriculum": "교과서 출판사, 학년, 단원명을 적으면 그 단원의 학습 목표에 맞춰 설계합니다. 예: [비상] 국어2 Ⅰ. 나, 너, 우리가 만나는 길 (1) 문학의 해석과 생활화",
        "category": self.category_combo.currentText(),
            "version": self.version_combo.currentText(),
            "difficulty": self.difficulty_combo.currentText(),
            "question_count": self.question_count_spin.value(),
            "question_style": self.question_style_combo.currentText(),
            "set_style": self.set_style_combo.currentText(),
            "answer_layout": "해설을 어디에 둘지 정합니다. '문항 바로 뒤에'는 검토하기 좋고, '맨 뒤에 모아서'는 학생에게 나눠 줄 시험지로 바로 쓸 수 있습니다.",
        "scoring_scheme": self.scoring_scheme_combo.currentText(),
            "modules": self.module_group.selected_names(),
            "manual_types_enabled": self.manual_types_checkbox.isChecked(),
            "manual_types": self.question_type_picker.selected_names(),
            "exam_mode": self.exam_mode_combo.currentText(),
            "output_type": self.output_type_combo.currentText(),
            "curriculum": self.curriculum_edit.text(),
        }

    def _save_session(self) -> None:
        session = self._capture_session()
        # An empty passage means nothing worth restoring.
        if not session["passage"].strip():
            self.app_settings.set("last_session", None)
            return
        self.app_settings.set("last_session", session)

    def _restore_session(self) -> None:
        """Put back the last session's inputs, skipping anything no longer valid."""
        session = self.app_settings.get("last_session")
        if not isinstance(session, dict):
            return
        passage = str(session.get("passage", ""))
        if not passage.strip():
            return

        self.passage_edit.setPlainText(passage)
        self.example_edit.setPlainText(str(session.get("example", "")))
        # Mode first: it repopulates the difficulty list the next line depends on.
        self._set_combo_text(self.exam_mode_combo, str(session.get("exam_mode", "")))
        self._set_combo_text(self.output_type_combo, str(session.get("output_type", "")))
        self.curriculum_edit.setText(str(session.get("curriculum", "")))

        # Combo values may have disappeared (a user category was deleted, say),
        # so set each only when the entry still exists.
        self._set_combo_text(self.category_combo, str(session.get("category", "")))
        self._set_combo_text(self.version_combo, str(session.get("version", "")))
        self._set_combo_text(self.difficulty_combo, str(session.get("difficulty", "")))
        self._set_combo_text(self.question_style_combo, str(session.get("question_style", "")))
        self._set_combo_text(self.set_style_combo, str(session.get("set_style", "")))
        self._set_combo_text(self.scoring_scheme_combo, str(session.get("scoring_scheme", "")))
        self._set_combo_text(self.answer_layout_combo, str(session.get("answer_layout", "")))

        count = session.get("question_count")
        if isinstance(count, int):
            self.question_count_spin.setValue(count)

        modules = session.get("modules")
        if isinstance(modules, list):
            self.module_group.set_checked([str(name) for name in modules])

        if session.get("manual_types_enabled"):
            self.manual_types_checkbox.setChecked(True)
            manual_types = session.get("manual_types")
            if isinstance(manual_types, list):
                self.question_type_picker.set_checked([str(name) for name in manual_types])

        self._refresh_round_indicator()
        self._toast("마지막 작업을 불러왔습니다.", "info")

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._save_session()
        super().closeEvent(event)

    def _set_workflow_step(self, index: int) -> None:
        if hasattr(self, "step_indicator"):
            self.step_indicator.set_current(index)

    def build_evaluation_prompt(self) -> None:
        """Open the verification dialog and turn what was pasted into a check prompt."""
        passage = self.passage_edit.toPlainText().strip()
        if not passage:
            self._show_validation_warning(
                "지문 확인 필요",
                "검증에는 원본 지문이 필요합니다.\n문항을 만들 때 사용한 지문을 입력해 주세요.",
                self.passage_edit,
            )
            return

        try:
            mode_labels = self.template_loader.evaluation_mode_labels()
        except TemplateLoadError as exc:
            QMessageBox.warning(self, "검증 설정 확인 필요", str(exc))
            return

        dialog = EvaluationDialog(
            mode_labels,
            self._describe_evaluation_mode,
            self,
            initial_text=self.last_evaluation_text,
            initial_mode=self.last_evaluation_mode,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        pasted = dialog.pasted_text()
        mode_label = dialog.selected_mode()
        self.last_evaluation_text = pasted
        self.last_evaluation_mode = mode_label

        if not pasted:
            QMessageBox.warning(
                self,
                "검증할 내용 없음",
                "LLM이 생성한 문항을 붙여 넣어 주세요.",
            )
            return

        try:
            mode = self.template_loader.load_evaluation_mode(mode_label)
            evaluation_prompt = self.evaluation_builder.build(
                EvaluationRequest(
                    generated_output=pasted,
                    passage=passage,
                    example_text=self.example_edit.toPlainText().strip(),
                    category=self.category_combo.currentText(),
                    difficulty=self.difficulty_combo.currentText(),
                    question_style=self.question_style_combo.currentText().strip(),
                    mode=mode,
                )
            )
        except EvaluationBuildError as exc:
            QMessageBox.warning(self, "검증 프롬프트를 만들 수 없습니다", str(exc))
            self._toast("검증 프롬프트를 만들지 못했습니다.", "error")
            return
        except TemplateLoadError as exc:
            QMessageBox.warning(self, "검증 설정 확인 필요", str(exc))
            self._toast("검증 설정을 불러오지 못했습니다.", "error")
            return

        self.output_edit.setPlainText(evaluation_prompt)
        self.output_title_label.setText("검증 프롬프트")
        self.output_summary_label.setText(mode.label)
        self._set_workflow_step(2)
        self.last_generated_prompt = evaluation_prompt
        self.output_kind = "evaluation"
        self._set_output_buttons_enabled(True)
        self._update_token_count(evaluation_prompt)

        if mode.strip_answers:
            self._toast("정답·해설을 제거했습니다. 새 대화창에서 실행하세요.", "success")
        else:
            self._toast("검증 프롬프트를 만들었습니다. 새 대화창에서 실행하세요.", "success")
        self.statusBar().showMessage(
            f"검증 프롬프트 생성 완료  |  방식: {mode.label}  |  반드시 새 대화창에서 실행하세요."
        )

    def _describe_evaluation_mode(self, mode_label: str) -> str:
        """Human-readable blurb for one verification mode, for the dialog."""
        try:
            mode = self.template_loader.load_evaluation_mode(mode_label)
        except TemplateLoadError:
            return ""
        text = mode.description
        if mode.strip_answers:
            text += "\n정답과 해설은 앱이 자동으로 제거한 뒤 프롬프트에 넣습니다."
        return text

    def _on_exam_mode_changed(self, mode_label: str) -> None:
        """Swap the difficulty axis and show the curriculum field only where it applies."""
        if not hasattr(self, "difficulty_combo"):
            return
        try:
            mode = self.template_loader.load_exam_mode(mode_label.strip())
        except TemplateLoadError:
            return

        previous = self.difficulty_combo.currentText()
        names = self.template_loader.difficulty_names(mode.mode_id)
        with block_signals(self.difficulty_combo):
            self.difficulty_combo.clear()
            self.difficulty_combo.addItems(names)
            index = self.difficulty_combo.findText(previous)
            self.difficulty_combo.setCurrentIndex(index if index >= 0 else 0)

        wants_context = bool(mode.context_label)
        self.curriculum_label.setVisible(wants_context)
        self.curriculum_edit.setVisible(wants_context)
        if wants_context and mode.context_help:
            self.curriculum_edit.setToolTip(mode.context_help)

    def _reload_output_types(self) -> None:
        """Offer only the output types that suit the selected exam area.

        A 문학 학습지 asks for 갈래·성격·시어 의미표 — on a 비문학 지문that produces
        nonsense, so the mismatch is prevented rather than warned about.
        """
        if not hasattr(self, "output_type_combo"):
            return
        try:
            labels = self.template_loader.output_type_labels(self.category_combo.currentText())
        except TemplateLoadError:
            return

        previous = self.output_type_combo.currentText()
        with block_signals(self.output_type_combo):
            self.output_type_combo.clear()
            self.output_type_combo.addItems(labels)
            index = self.output_type_combo.findText(previous)
            self.output_type_combo.setCurrentIndex(index if index >= 0 else 0)

        if self.output_type_combo.currentText() != previous:
            # The previous choice does not apply to this area any more.
            self._toast(
                f"'{self.category_combo.currentText()}'에 맞는 산출물 유형으로 바꿨습니다.", "info"
            )
        self._on_output_type_changed(self.output_type_combo.currentText())

    def _on_output_type_changed(self, type_label: str) -> None:
        """Grey out question settings for outputs that contain no questions."""
        if not hasattr(self, "output_type_description_label"):
            return
        try:
            output_type = self.template_loader.load_output_type(type_label.strip())
        except TemplateLoadError:
            self.output_type_description_label.setText("")
            return

        self.output_type_description_label.setText(output_type.description)

        wants_questions = output_type.includes_questions
        for widget in (
            self.question_count_spin,
            self.question_style_combo,
            self.set_style_combo,
            self.scoring_scheme_combo,
            self.answer_layout_combo,
            self.manual_types_checkbox,
        ):
            widget.setEnabled(wants_questions)
        if not wants_questions:
            self.question_type_picker.setVisible(False)

    def _on_manual_types_toggled(self, checked: bool) -> None:
        """Switch between automatic type assignment and a hand-picked list."""
        self.question_type_picker.setVisible(checked)
        if checked:
            self._reload_question_types()
            self.question_type_hint.setText(
                "고른 유형만 사용합니다. 문항 수보다 적게 고르면 순서대로 반복됩니다."
            )
        else:
            self.question_type_hint.setText(
                "자동: 문항마다 다른 유형을 배분하고, 회차가 바뀌면 지난 유형을 피합니다."
            )

    def _reload_question_types(self) -> None:
        """Refill the picker for the currently selected category."""
        if not hasattr(self, "question_type_picker"):
            return
        try:
            types = self.template_loader.load_question_types(self.category_combo.currentText())
        except TemplateLoadError:
            types = []
        self.question_type_picker.set_types([(qt.name, qt.focus) for qt in types])

    def _selected_manual_types(self) -> list[str] | None:
        """Return hand-picked type names, or None when running in automatic mode."""
        if not getattr(self, "manual_types_checkbox", None):
            return None
        if not self.manual_types_checkbox.isChecked():
            return None
        return self.question_type_picker.selected_names() or None

    def apply_selected_preset(self) -> None:
        preset_label = self.preset_combo.currentText().strip()
        if preset_label == "직접 설정":
            self._toast("프리셋 대신 직접 설정을 사용 중입니다.", "info")
            return

        preset = self.presets_by_label.get(preset_label)
        if preset is None:
            QMessageBox.warning(self, "프리셋 확인", "선택한 프리셋을 불러올 수 없습니다.")
            return

        self._apply_preset(preset)
        self._clear_generated_output()
        self._toast(f"프리셋 적용: {preset.label}", "success")

    def save_current_as_preset(self) -> None:
        preset_label, ok = QInputDialog.getText(
            self, "프리셋 저장", "새 프리셋 이름을 입력하세요.", text=self._suggest_preset_label(),
        )
        if not ok:
            return
        normalized_label = preset_label.strip()
        if not normalized_label:
            QMessageBox.warning(self, "프리셋 저장", "프리셋 이름은 비워둘 수 없습니다.")
            return

        description, ok = QInputDialog.getMultiLineText(
            self, "프리셋 설명", "프리셋 설명을 입력하세요.", self._suggest_preset_description(),
        )
        if not ok:
            return
        normalized_description = description.strip()
        if not normalized_description:
            QMessageBox.warning(self, "프리셋 저장", "프리셋 설명은 비워둘 수 없습니다.")
            return

        preset = PromptPreset(
            preset_id="",
            label=normalized_label,
            description=normalized_description,
            category=self.category_combo.currentText().strip(),
            version=self.version_combo.currentText().strip(),
            difficulty=self.difficulty_combo.currentText().strip(),
            question_count=self.question_count_spin.value(),
            modules=self.module_group.selected_names(),
            question_style=self.question_style_combo.currentText().strip(),
            set_style=self.set_style_combo.currentText().strip(),
            scoring_scheme=self.scoring_scheme_combo.currentText().strip(),
            is_user_defined=True,
        )

        try:
            saved_preset = self.preset_loader.save_user_preset(preset)
        except (PresetSaveError, PresetLoadError) as exc:
            QMessageBox.warning(self, "프리셋 저장", str(exc))
            return

        self._reload_presets(saved_preset.label)
        self._toast(f"새 프리셋 저장: {saved_preset.label}", "success")

    def delete_selected_preset(self) -> None:
        preset_label = self.preset_combo.currentText().strip()
        if preset_label == "직접 설정":
            return

        preset = self.presets_by_label.get(preset_label)
        if preset is None:
            return

        detail = "이 사용자 프리셋을 완전히 삭제합니다." if preset.is_user_defined else (
            "기본 프리셋은 파일에서 지우지 않고 현재 사용자 목록에서 숨깁니다."
        )
        answer = QMessageBox.question(
            self, "프리셋 삭제", f"'{preset.label}' 프리셋을 제거할까요?\n\n{detail}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.preset_loader.remove_preset(preset)
        except (PresetSaveError, PresetLoadError) as exc:
            QMessageBox.warning(self, "프리셋 삭제", str(exc))
            return

        self._reload_presets()
        self._clear_generated_output()
        self._toast(f"프리셋 제거: {preset.label}", "info")

    def add_custom_category(self) -> None:
        current_category = self.category_combo.currentText().strip()
        starters = self.template_loader.load_category_starters()
        suggested_name = ""
        try:
            base_category = current_category.split("-", 1)[0].strip()
            matching_starters = [
                (sn, st) for sn, st in starters.items() if sn.startswith(f"{base_category}-")
            ]
            if matching_starters:
                existing = set(self.template_loader.category_names())
                for sn, st in matching_starters:
                    if sn not in existing:
                        suggested_name = sn
                        initial_template = st
                        break
                else:
                    initial_template = self.template_loader.load_category_template(current_category)
            else:
                initial_template = self.template_loader.load_category_template(current_category)
        except TemplateLoadError:
            initial_template = (
                "이 출제영역에서 중점적으로 평가할 개념, 표현, 사고 과정을 한국어로 적어 주세요.\n"
                "- 어떤 능력을 물을지\n- 어떤 근거를 중시할지\n- 어떤 오답을 피해야 할지"
            )

        category_name, ok = QInputDialog.getText(
            self, "출제영역 추가", "새 출제영역 이름을 입력하세요.", text=suggested_name,
        )
        if not ok:
            return
        normalized = category_name.strip()
        if not normalized:
            QMessageBox.warning(self, "출제영역 추가", "출제영역 이름은 비워둘 수 없습니다.")
            return

        template_text, ok = QInputDialog.getMultiLineText(
            self, "출제영역 지시문", "이 출제영역에 사용할 지시문을 입력하세요.", initial_template,
        )
        if not ok:
            return

        try:
            self.template_loader.add_user_category(normalized, template_text)
        except (CategorySaveError, TemplateLoadError) as exc:
            QMessageBox.warning(self, "출제영역 추가", str(exc))
            return

        self._reload_categories(normalized)
        self._clear_generated_output()
        self._toast(f"새 출제영역 추가: {normalized}", "success")

    def delete_selected_category(self) -> None:
        category_name = self.category_combo.currentText().strip()
        if not self.template_loader.is_user_category(category_name):
            QMessageBox.information(self, "출제영역 삭제", "기본 제공 출제영역은 삭제할 수 없습니다.")
            return

        answer = QMessageBox.question(
            self, "출제영역 삭제", f"'{category_name}' 출제영역을 삭제할까요?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.template_loader.remove_user_category(category_name)
        except (CategorySaveError, TemplateLoadError) as exc:
            QMessageBox.warning(self, "출제영역 삭제", str(exc))
            return

        self._reload_categories()
        self._clear_generated_output()
        self._toast(f"출제영역 삭제: {category_name}", "info")

    def copy_output(self) -> None:
        output = self._require_generated_prompt("복사")
        if output is None:
            return

        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(output)
            QApplication.processEvents()
        self._toast("클립보드에 복사되었습니다!", "success")

    def save_output(self, extension: str) -> None:
        output = self._require_generated_prompt("저장")
        if output is None:
            return

        if self.output_kind == "evaluation":
            export_data = self._build_evaluation_export_data(output)
        elif self.last_generated_request is not None:
            export_data = self._build_export_data(self.last_generated_request, output)
        else:
            self._toast("저장할 생성 정보가 없습니다.", "error")
            return
        content = build_export_content(export_data, extension)
        default_name = build_default_filename(export_data.category, export_data.version, extension)
        selected_path, _ = QFileDialog.getSaveFileName(
            self, "프롬프트 저장", str(Path.home() / default_name),
            f"{extension.upper()} 파일 (*.{extension});;모든 파일 (*.*)",
        )
        if not selected_path:
            return

        target_path = ensure_file_extension(Path(selected_path), extension)
        try:
            save_text_file(target_path, content)
        except OSError as exc:
            QMessageBox.critical(self, "저장 오류", f"파일 저장 중 오류가 발생했습니다.\n\n{exc}")
            return

        self._toast(f"저장 완료: {target_path.name}", "success")

    def _confirm_reset(self) -> None:
        """Reset with confirmation dialog."""
        has_content = bool(self.passage_edit.toPlainText().strip() or self.last_generated_prompt)
        if has_content:
            answer = QMessageBox.question(
                self, "초기화 확인", "모든 입력과 출력을 초기화할까요?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.reset_all()

    def reset_all(self) -> None:
        self.preset_combo.setCurrentIndex(0)
        self.exam_mode_combo.setCurrentIndex(0)
        self.output_type_combo.setCurrentIndex(0)
        self.curriculum_edit.clear()
        self.category_combo.setCurrentIndex(0)
        self.version_combo.setCurrentIndex(0)
        self.difficulty_combo.setCurrentIndex(0)
        self.question_count_spin.setValue(1)
        self.question_style_combo.setCurrentIndex(0)
        self.set_style_combo.setCurrentIndex(0)
        self.scoring_scheme_combo.setCurrentIndex(0)
        self.answer_layout_combo.setCurrentIndex(0)
        self.passage_edit.clear()
        self.example_edit.clear()
        self.module_group.reset()
        self.manual_types_checkbox.setChecked(False)
        self.question_type_picker.reset()
        self.last_evaluation_text = ""
        self._clear_generated_output()
        self._refresh_round_indicator()
        self.app_settings.set("last_session", None)
        self._toast("모든 입력을 초기화했습니다.", "info")

    # ===================================================================
    # INTERNAL HELPERS
    # ===================================================================

    def _variation_toast_message(self, variation: VariationPlan | None) -> str:
        if variation is None:
            return "프롬프트 생성이 완료되었습니다!"
        if variation.round_number == 1:
            return "프롬프트 생성이 완료되었습니다!"
        return f"{variation.round_number}회차 생성 완료 — 이전 회차와 다른 유형으로 구성했습니다."

    def _variation_status_message(self, variation: VariationPlan | None) -> str:
        if variation is None:
            return "프롬프트 생성 완료"
        type_names = ", ".join(qt.name for qt in variation.assigned_types)
        return (
            f"프롬프트 생성 완료  |  {variation.round_number}회차"
            f"  |  초점: {variation.anchor.label}  |  문항 유형: {type_names}"
        )

    def reset_passage_history(self) -> None:
        """Forget this passage's generation history so numbering restarts at 1."""
        passage = self.passage_edit.toPlainText().strip()
        if not passage:
            self._toast("지문을 먼저 입력해 주세요.", "error")
            return

        round_number = self.history_store.round_number(passage, self.category_combo.currentText())
        if round_number <= 1:
            self._toast("이 지문에는 아직 생성 이력이 없습니다.", "info")
            return

        confirm = QMessageBox.question(
            self,
            "생성 이력 초기화",
            f"이 지문의 생성 이력({round_number - 1}회)을 지울까요?\n"
            "지우면 다음 생성이 다시 1회차로 시작합니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            self.history_store.clear_passage(passage)
        except HistoryStoreError as exc:
            QMessageBox.warning(self, "이력 초기화 실패", str(exc))
            return
        self._toast("이 지문의 생성 이력을 지웠습니다.", "info")
        self._refresh_round_indicator()

    def _toast(self, message: str, kind: str = "info") -> None:
        toast = ToastNotification(self, message, kind=kind)
        toast.show_at_top()
        self.statusBar().showMessage(message)

    def _make_field_label(self, text: str, help_text: str | None = None) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        label = QLabel(text)
        label.setObjectName("fieldLabel")
        row.addWidget(label)

        if help_text:
            row.addWidget(create_help_button(help_text))

        row.addStretch(1)
        return container

    def _make_section_title_with_help(self, text: str, help_text: str) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        label = QLabel(text)
        label.setObjectName("sectionTitle")
        row.addWidget(label)
        row.addWidget(create_help_button(help_text))
        row.addStretch(1)
        return container

    def _schedule_preview_update(self) -> None:
        """Debounce passage edits so the round indicator does not refresh per keystroke."""
        if self._preview_timer is None:
            self._preview_timer = QTimer(self)
            self._preview_timer.setSingleShot(True)
            self._preview_timer.setInterval(400)
            self._preview_timer.timeout.connect(self._refresh_round_indicator)
        self._preview_timer.start()
        self._update_passage_count()

    def _refresh_round_indicator(self) -> None:
        """Show how many times this passage has already been generated."""
        if not hasattr(self, "round_label") or not hasattr(self, "passage_edit"):
            return  # Category signals can fire before the passage widgets exist.
        passage = self.passage_edit.toPlainText().strip()
        if not passage:
            self.round_label.setText("")
            self.reset_history_button.setVisible(False)
            return

        round_number = self.history_store.round_number(passage, self.category_combo.currentText())
        if round_number <= 1:
            self.round_label.setText("")
            self.reset_history_button.setVisible(False)
            return

        self.round_label.setText(f"이 지문 {round_number - 1}회 생성됨 — 다음은 {round_number}회차")
        self.reset_history_button.setVisible(True)

    def _update_passage_count(self) -> None:
        """Show passage length and warn when it is too thin for the question count."""
        if not hasattr(self, "passage_count_label"):
            return
        passage = self.passage_edit.toPlainText().strip()
        self.passage_hint_label.setVisible(not passage)
        if not passage:
            self.passage_count_label.setText("")
            self.passage_count_label.setToolTip("")
            return

        char_count = len(passage)
        question_count = self.question_count_spin.value()
        # Roughly one question needs 250 characters of passage to have distinct ground.
        thin = char_count < question_count * 250

        text = f"{char_count:,}자"
        if thin:
            text += "  ⚠ 지문이 짧습니다"
            self.passage_count_label.setToolTip(
                f"지문 {char_count:,}자로 {question_count}문항을 만들면 문항끼리 근거가 겹치기 쉽습니다.\n"
                "지문을 늘리거나 문항 수를 줄이는 편이 좋습니다."
            )
        else:
            self.passage_count_label.setToolTip("")
        self.passage_count_label.setText(text)

    def _update_output_summary(self, variation: VariationPlan | None) -> None:
        """Summarise what went into the prompt, next to the output title."""
        if not hasattr(self, "output_summary_label"):
            return
        parts = [
            self.output_type_combo.currentText().split(" (")[0],
            self.category_combo.currentText(),
            self.version_combo.currentText(),
        ]
        if variation is not None:
            parts.append(f"{variation.round_number}회차")
            parts.append(f"유형 {len(set(qt.name for qt in variation.assigned_types))}종")
            parts.append(variation.anchor.label)
        modules = self.module_group.selected_names()
        if modules:
            parts.append(f"모듈 {len(modules)}개")
        self.output_summary_label.setText("  ·  ".join(part for part in parts if part))

    def _update_token_count(self, text: str) -> None:
        char_count = len(text)
        estimated_tokens = int(char_count / self.APPROX_CHARS_PER_TOKEN)
        self.token_label.setText(f"{char_count:,}자  |  ~{estimated_tokens:,} 토큰")

    def _set_output_buttons_enabled(self, enabled: bool) -> None:
        self.copy_button.setEnabled(enabled)
        self.save_txt_button.setEnabled(enabled)
        self.save_md_button.setEnabled(enabled)

    # Preset helpers

    def _load_presets_into_ui(self) -> None:
        try:
            presets = self.preset_loader.load_presets()
        except PresetLoadError as exc:
            self.presets_by_label = {}
            self.preset_load_error_message = str(exc)
            return
        self.presets_by_label = {p.label: p for p in presets}
        for p in presets:
            self.preset_combo.addItem(p.label)
        self.preset_load_error_message = ""

    def _reload_presets(self, selected_label: str = "직접 설정") -> None:
        with block_signals(self.preset_combo):
            self.preset_combo.clear()
            self.preset_combo.addItem("직접 설정")
            self._load_presets_into_ui()
            idx = self.preset_combo.findText(selected_label)
            self.preset_combo.setCurrentIndex(max(idx, 0))
        self._update_preset_description(self.preset_combo.currentText())

    def _reload_categories(self, selected_label: str | None = None) -> None:
        current = selected_label or self.category_combo.currentText().strip()
        with block_signals(self.category_combo):
            self.category_combo.clear()
            self.category_combo.addItems(self.template_loader.category_names())
            idx = self.category_combo.findText(current)
            self.category_combo.setCurrentIndex(max(idx, 0))
        self._update_category_actions(self.category_combo.currentText())

    def _update_preset_description(self, preset_label: str) -> None:
        if preset_label == "직접 설정":
            self.delete_preset_button.setEnabled(False)
            if getattr(self, "preset_load_error_message", ""):
                self.preset_description_label.setText("프리셋 파일을 불러오지 못했습니다.")
            else:
                self.preset_description_label.setText("설정을 직접 선택하거나 프리셋을 적용하세요.")
            return

        preset = self.presets_by_label.get(preset_label)
        if preset is None:
            self.delete_preset_button.setEnabled(False)
            self.preset_description_label.setText("")
            return
        self.delete_preset_button.setEnabled(True)
        source = "사용자" if preset.is_user_defined else "기본"
        self.preset_description_label.setText(f"[{source}] {preset.description}")

    def _update_category_actions(self, category_name: str) -> None:
        self._refresh_round_indicator()
        self._reload_question_types()
        self._reload_output_types()
        is_user = self.template_loader.is_user_category(category_name.strip())
        self.delete_category_button.setEnabled(is_user)

    def _update_version_description(self, version_name: str) -> None:
        desc = self.VERSION_DESCRIPTIONS.get(version_name.strip(), "")
        self.version_description_label.setText(desc)

    def _apply_preset(self, preset: PromptPreset) -> None:
        self._set_combo_text(self.category_combo, preset.category)
        self._set_combo_text(self.version_combo, preset.version)
        self._set_combo_text(self.difficulty_combo, preset.difficulty)
        self._set_combo_text(self.question_style_combo, preset.question_style)
        self._set_combo_text(self.set_style_combo, preset.set_style)
        self._set_combo_text(self.scoring_scheme_combo, preset.scoring_scheme)
        self.question_count_spin.setValue(preset.question_count)
        self.module_group.set_checked(preset.modules)

    def _selected_module_names(self) -> list[str]:
        return self.module_group.selected_names()

    def _suggest_preset_label(self) -> str:
        cat = self.category_combo.currentText().strip()
        diff = self.difficulty_combo.currentText().strip()
        return f"{cat} 사용자 프리셋 ({diff})"

    def _suggest_preset_description(self) -> str:
        modules = self.module_group.selected_names()
        module_text = ", ".join(modules) if modules else "선택 모듈 없음"
        return (
            f"{self.category_combo.currentText().strip()} / "
            f"{self.version_combo.currentText().strip()} / "
            f"{self.difficulty_combo.currentText().strip()} / "
            f"{self.question_style_combo.currentText().strip()} / "
            f"{self.set_style_combo.currentText().strip()} / "
            f"{self.scoring_scheme_combo.currentText().strip()} / "
            f"{self.question_count_spin.value()}문항 / {module_text}"
        )

    def _set_combo_text(self, combo: QComboBox, value: str) -> None:
        idx = combo.findText(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _build_request_from_inputs(self) -> PromptRequest | None:
        result = self._validate_inputs()
        if result is None:
            return None
        passage, category, version, question_count = result
        return PromptRequest(
            passage=passage,
            example_text=self.example_edit.toPlainText().strip(),
            category=category,
            version=version,
            selected_modules=self.module_group.selected_names(),
            question_count=question_count,
            difficulty=self.difficulty_combo.currentText(),
            question_style=self.question_style_combo.currentText().strip(),
            set_style=self.set_style_combo.currentText().strip(),
            scoring_scheme=self.scoring_scheme_combo.currentText().strip(),
            answer_layout=self.answer_layout_combo.currentText().strip(),
            exam_mode=self.exam_mode_combo.currentText().strip(),
            output_type=self.output_type_combo.currentText().strip(),
            curriculum_context=self.curriculum_edit.text().strip(),
        )

    def _validate_inputs(self) -> tuple[str, str, str, int] | None:
        passage = self.passage_edit.toPlainText().strip()
        if not passage:
            self._show_validation_warning(
                "입력 확인", "지문은 비워둘 수 없습니다.\n문항 생성에 사용할 지문을 먼저 입력해 주세요.",
                self.passage_edit,
            )
            return None

        question_count = self.question_count_spin.value()
        if question_count < 1:
            self._show_validation_warning("입력 확인", "생성 문항 수는 1 이상이어야 합니다.", self.question_count_spin)
            return None

        category = self.category_combo.currentText().strip()
        if category not in self.template_loader.category_names():
            self._show_validation_warning("선택 확인", "유효한 출제 영역을 선택해 주세요.", self.category_combo)
            return None

        version = self.version_combo.currentText().strip()
        if version not in self.template_loader.version_names():
            self._show_validation_warning("선택 확인", "유효한 프롬프트 버전을 선택해 주세요.", self.version_combo)
            return None

        difficulty = self.difficulty_combo.currentText().strip()
        if difficulty not in self.template_loader.difficulty_names():
            self._show_validation_warning("선택 확인", "유효한 난이도 등급을 선택해 주세요.", self.difficulty_combo)
            return None

        return passage, category, version, question_count

    def _require_generated_prompt(self, action_name: str) -> str | None:
        output = self.last_generated_prompt.strip() or self.output_edit.toPlainText().strip()
        if output:
            return output
        self._toast(f"생성된 프롬프트가 없어 {action_name}할 수 없습니다.", "warning")
        return None

    def _show_validation_warning(self, title: str, message: str, focus_widget: QWidget) -> None:
        QMessageBox.warning(self, title, message)
        self._toast(message.split("\n")[0], "warning")
        focus_widget.setFocus()

    def _clear_generated_output(self) -> None:
        self.output_edit.clear()
        self.last_generated_request = None
        self.last_generated_prompt = ""
        self.last_variation_plan = None
        self.output_kind = "prompt"
        self.output_title_label.setText("생성 결과")
        self.output_summary_label.setText("")
        self._set_workflow_step(0)
        self.token_label.setText("")
        self._set_output_buttons_enabled(False)

    def _build_evaluation_export_data(self, evaluation_prompt: str) -> PromptExportData:
        """Export metadata for a verification prompt rather than a generation prompt."""
        mode_label = self.last_evaluation_mode
        category = self.category_combo.currentText()
        return PromptExportData(
            title=f"수능 국어 문항 검증 프롬프트 - {category} / {mode_label}",
            timestamp=current_timestamp(),
            category=category,
            version=mode_label,
            difficulty=self.difficulty_combo.currentText(),
            question_count=self.question_count_spin.value(),
            selected_options=[
                f"검증 방식: {mode_label}",
                f"문항 형식: {self.question_style_combo.currentText().strip()}",
                "이 프롬프트는 새 대화창에서 실행해야 합니다.",
            ],
            passage=self.passage_edit.toPlainText().strip(),
            example_text=self.example_edit.toPlainText().strip(),
            generated_prompt=evaluation_prompt,
        )

    def _build_export_data(self, request: PromptRequest, generated_prompt: str) -> PromptExportData:
        selected_options = [
            f"난이도: {request.difficulty}",
            f"문항 수: {request.question_count}",
            f"문항 형식: {request.question_style}",
            f"출제 묶음: {request.set_style}",
            f"배점 구조: {request.scoring_scheme}",
            f"해설 배치: {request.answer_layout}",
            f"평가 맥락: {request.exam_mode}",
            f"산출물 유형: {request.output_type}",
            *([f"교과 연계: {request.curriculum_context}"] if request.curriculum_context else []),
            *request.selected_modules,
        ]
        if self.last_variation_plan is not None:
            plan = self.last_variation_plan
            selected_options.append(f"생성 회차: {plan.round_number}회차")
            selected_options.append(f"회차 초점: {plan.anchor.label}")
            selected_options.append(
                "문항 유형: " + ", ".join(qt.name for qt in plan.assigned_types)
            )
        title = f"수능 국어 프롬프트 아카이브 - {request.category} / {request.version}"
        return PromptExportData(
            title=title,
            timestamp=current_timestamp(),
            category=request.category,
            version=request.version,
            difficulty=request.difficulty,
            question_count=request.question_count,
            selected_options=selected_options,
            passage=request.passage,
            example_text=request.example_text,
            generated_prompt=generated_prompt,
        )
