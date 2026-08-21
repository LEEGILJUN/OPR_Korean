# CLAUDE.md

수능 국어 프롬프트 생성기 — PySide6 기반 로컬 데스크톱 앱.
지문/보기와 출제 설정을 입력하면 LLM에 붙여 넣을 수능 국어 문항 생성 프롬프트를 만들어 준다.
웹 앱 아님, DB 없음, 네트워크 호출 없음. 모든 데이터는 로컬 파일.

## 실행 / 개발 명령 (macOS)

```bash
.venv/bin/python main.py            # 앱 실행 (app.py도 동일한 진입점)
.venv/bin/python tools/smoke_test.py  # GUI 없이 로더 + 빌더 + 윈도우 생성 확인
```

가상환경은 `.venv` (Python 3.12, PySide6 6.10). 새로 만들 때:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

빌드(one-folder, macOS `.app` 생성):

```bash
.venv/bin/pip install pyinstaller
.venv/bin/pyinstaller --noconfirm CSATPromptGenerator.spec
```

`.spec`에 `datas=[('templates','templates'), ('config','config')]`가 이미 들어 있다.
macOS/Linux에서 `--add-data`를 직접 쓸 때 구분자는 `:`, Windows는 `;`.

## 아키텍처

레이어가 단방향으로 분리되어 있다. `gui` → `core` → 파일. `core`는 Qt에 의존하지 않는다.

```
main.py / app.py        진입점 (QApplication + MainWindow)
core/
  models.py             dataclass: PromptRequest, PromptExportData, PromptPreset, DifficultyProfile
  template_loader.py    templates/*.txt + config/*.json 로딩, 사용자 정의 출제영역 CRUD
  prompt_builder.py     템플릿 조각을 섹션(## 1) ... )으로 합성 → 최종 프롬프트 문자열
  preset_loader.py      기본/사용자 프리셋 로딩·저장·숨김 처리
  file_utils.py         리소스 경로 해석, .txt/.md 내보내기 렌더링
gui/
  main_window.py        전체 UI + 액션 (약 1000줄, 이 앱의 중심)
  widgets.py            ToastNotification, CollapsibleSection, ModuleCheckboxGroup 등 재사용 위젯
  styles.py             COLORS 딕셔너리 + build_stylesheet() 로 만드는 단일 QSS
```

### 프롬프트 조립 순서 (`PromptBuilder.build`)

작업 목표 → 공통 규칙(common + 버전 지침 + 난이도 지침) → 영역별 지시 → 추가 모듈 →
사용자 입력 지문 → 사용자 입력 보기 → 출력 형식.
각 섹션은 `@@TITLE:` 마커로 만들어졌다가 `_join_sections`에서 `## n) 제목` 으로 번호가 매겨진다.
빈 섹션(보기 미입력, 모듈 미선택)은 자동으로 빠지고 번호가 다시 매겨진다.

### 리소스 경로 규칙

`core/file_utils.py`의 `resource_root()`가 일반 실행과 PyInstaller 번들(`sys._MEIPASS`)을 모두 처리한다.
템플릿/설정 파일 경로는 **반드시** `templates_root()` / `config_root()`를 거쳐 얻는다.
직접 상대경로를 쓰면 번들에서 깨진다.

읽기 전용 번들 리소스와 쓰기 가능한 사용자 데이터는 위치가 다르다.

- 번들: `templates/`, `config/presets.json`, `config/difficulty_profiles.json`, `config/category_starter_templates.json`
- 사용자 데이터(`user_data_root()`): macOS `~/Library/Application Support/CSATPromptGenerator/`
  - `user_presets.json`, `hidden_presets.json`, `user_categories.json`

## 콘텐츠를 바꾸는 법 (코드 수정 없이)

- 공통 지시: `templates/common.txt`
- 영역별 지시: `templates/<category>.txt` — 이름 매핑은 `TemplateLoader.categories`
- 버전 지시: `templates/versions/{basic,advanced,ultimate}.txt` (파일 없으면 `version_fallbacks` 사용)
- 모듈 지시: `templates/modules/*.txt` — 매핑은 `TemplateLoader.modules`
- 난이도(1~9등급): `config/difficulty_profiles.json`
- 기본 프리셋: `config/presets.json`
- 출제영역별 시작 템플릿(사용자 정의 출제영역 추가 시 예시로 제공): `config/category_starter_templates.json`
  - 키 규칙이 `"<기본영역>-<세부유형>"` 이고, GUI가 `startswith(f"{base_category}-")` 로 필터링한다.

새 카테고리/모듈/버전을 **코드에** 추가할 때는 `TemplateLoader`의 OrderedDict와 실제 파일을 함께 넣어야 한다.
GUI 도움말 문구도 `MainWindow.FIELD_HELP_TEXTS` / `MODULE_HELP_TEXTS` / `VERSION_DESCRIPTIONS`에 있다.

## 컨벤션

- 모든 사용자 대면 문자열은 한국어. 에러 메시지는 "무엇이 왜 잘못됐는지 + 경로/사용 가능 항목"까지 알려 준다.
- 도메인 예외를 쓴다: `TemplateLoadError`, `CategorySaveError`, `PresetLoadError`, `PresetSaveError`.
  GUI에서 잡아 `QMessageBox` 또는 토스트로 보여 준다.
- 파일 입출력은 항상 `encoding="utf-8"`.
- 코드/주석/독스트링은 영어, UI 문자열은 한국어인 기존 스타일을 따른다.
- 타입 힌트 사용, 파일 상단에 `from __future__ import annotations`.
- 색상은 하드코딩하지 말고 `gui/styles.py`의 `COLORS`를 통해 쓴다.

## 알려진 상태 / 이어서 할 만한 것

- `MainWindow._schedule_preview_update()`는 아직 빈 껍데기다. `self._preview_timer`(QTimer)와 함께
  디바운스 라이브 프리뷰를 붙이려던 자리.
- `templates/categories/` 디렉터리는 비어 있고 아무 코드도 참조하지 않는다.
- 최상위 `csat_prompt_generator/` 디렉터리는 `__pycache__`만 남은 예전 구조의 잔재다. (삭제해도 무방)
- 자동화된 테스트가 없다. `tools/smoke_test.py`가 유일한 확인 수단.
