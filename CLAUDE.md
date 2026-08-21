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
  models.py             dataclass: PromptRequest, PromptExportData, PromptPreset, DifficultyProfile,
                        QuestionType, RotationAnchor, VariationPlan, GenerationRun
  template_loader.py    templates/*.txt + config/*.json 로딩, 사용자 정의 출제영역 CRUD
  prompt_builder.py     템플릿 조각을 섹션(## 1) ... )으로 합성 → 최종 프롬프트 문자열
                        + plan_variation()으로 문항 유형 배분과 회차 앵커 결정
  preset_loader.py      기본/사용자 프리셋 로딩·저장·숨김 처리
  evaluation_builder.py 되붙여 넣은 생성 결과 → 검증 프롬프트 (정답 제거 포함)
  app_settings.py       로컬 UI 설정과 세션 복원 (테마·폰트·가이드 표시·마지막 입력)
  history_store.py      지문별 생성 이력(요청한 유형·앵커) 기록 → 회차 계산과 중복 회피
  file_utils.py         리소스 경로 해석, passage_fingerprint(), .txt/.md 내보내기 렌더링
gui/
  main_window.py        전체 UI + 액션 (약 1000줄, 이 앱의 중심)
  widgets.py            ToastNotification, CollapsibleSection, ModuleCheckboxGroup 등 재사용 위젯
  styles.py             LIGHT/DARK 팔레트, apply_theme(), build_stylesheet(font_scale)
  guide_dialog.py       config/user_guide.json 을 렌더링하는 사용 안내 다이얼로그
  evaluation_dialog.py  생성 결과를 되붙여 넣는 검증 창 (3단계)
```

### 프롬프트 조립 순서 (`PromptBuilder.build`)

작업 목표 → 공통 규칙(common + 버전 지침 + 난이도 지침) → 영역별 지시 → 문항 구성 설계 →
추가 모듈 → 사용자 입력 지문 → 사용자 입력 보기 → 출력 형식.
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
- 평가 맥락(수능/내신): `config/exam_modes.json`
- 산출물 유형(문항 세트·학습지·해제·문법표·모의고사): `config/output_types.json`
- 난이도: `config/difficulty_profiles.json` — 각 프로파일의 `mode`가 `csat`/`school`을 가른다
- 영역별 문항 유형: `config/question_types.json` — 없는 영역은 `default` 목록으로 대체
- 회차별 초점 앵커: `config/rotation_anchors.json` — 회차 % 개수로 순환
- 기본 프리셋: `config/presets.json`
- 검증 모드와 점검 항목: `config/evaluation_criteria.json`
- 사용 안내(3단계 시나리오, FAQ, 단축키): `config/user_guide.json`
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
  `apply_theme()`이 `COLORS`를 제자리에서 교체하므로 `from .styles import COLORS`로
  받아둔 참조는 자동으로 현재 테마를 가리킨다. 다만 **위젯 생성 시점에 인라인
  스타일로 박아 넣은 색은 갱신되지 않는다** — 그런 위젯에는 `refresh_theme()`을 만들고
  `MainWindow._apply_appearance()`에서 불러 준다.
- QSS의 `font-size: Npx`는 빌드 시점에 `_scale_fonts()`가 배율을 적용한다.
  새 규칙에도 px 단위를 쓰면 자동으로 따라간다.

## 산출물 유형과 평가 맥락

프롬프트는 두 축으로 달라진다.

- **평가 맥락**(`ExamMode`) — `csat`는 1~9등급 축, `school`은 내신 기초~최고난도 축을 쓰고
  교과 연계 입력란이 열린다. `difficulty_names(mode_id)`가 축을 갈라 준다.
- **산출물 유형**(`OutputType`) — 문항 세트 / 학습지 전체 / 작품 해제만 / 문법 개념 정리표 /
  미니 모의고사. `structure`와 `instructions`가 "산출물 구성" 섹션이 된다.

`includes_questions: false`인 유형(작품 해제만)은 문항 관련 섹션이 **통째로 빠진다** —
문항 유형 배분, 추가 모듈, 문항 중심 출력 지시가 모두 제외되고, `common.txt` 대신
`_analysis_only_rules()`가 들어간다. common.txt는 전부 문항 설계를 전제로 쓰여 있어서
걸러 쓰는 것보다 별도 기준을 두는 편이 정확하다.

새 산출물 유형을 추가할 때는 `config/output_types.json`에 항목만 넣으면 된다.
코드 수정은 필요 없고, `tools/smoke_test.py`의 `check_output_types()`가 자동으로 검사한다.

## 문항 다양성 설계 (중복 방지)

같은 지문을 반복 입력하면 비슷한 문항만 나온다는 사용자 피드백에 대응한 구조다.
원인은 `common.txt` 1단계가 지문에서 항상 같은 것을 식별하고 2단계가 "그것만 쓰라"고
못 박은 데 있었다. 네 갈래로 대응한다.

1. **유형 강제 배분** — `PromptBuilder.plan_variation()`이 문항마다 서로 다른 유형을 배정하고,
   프롬프트의 "문항 구성 설계" 섹션에 넣는다.
2. **후보 풀 확장** — `common.txt`의 1-B단계(Candidate Pool Stage)가 출제 후보 12개 이상을
   문단별로 고르게 뽑게 한 뒤 그중에서 고르게 한다.
3. **오답 유형 배분 + 선지 서술 다양화** — `common.txt` 3단계.
4. **회차 기반 중복 회피** — `GenerationHistoryStore`가 지문별로 지난 회차에 쓴 유형을 기억하고,
   `plan_variation()`이 안 쓴 유형을 우선 배정한다. 회차마다 `rotation_anchors.json`의
   앵커가 순환하며 지문의 다른 지점을 겨냥하게 한다.

중요한 제약: **앱은 LLM이 실제로 만든 문항을 볼 수 없다.** 프롬프트만 만들고 결과는 외부에서
받기 때문이다. 그래서 이력에는 *요청한* 유형과 앵커만 기록한다. 실제 생성물 기준의 중복 제거가
필요해지면 결과를 되붙여 넣는 입력이 따로 있어야 한다.

유형 배정은 결정론적이다. 같은 지문·같은 회차면 같은 배정이 나온다. 서로 다른 지문이 같은 유형으로
시작하지 않도록 `passage_fingerprint()` 값으로 시작 위치를 오프셋한다.

## 생성 결과 검증 (검증 루프)

앱은 LLM을 호출하지 않으므로 검증도 생성과 같은 방식으로 돈다.
사용자가 LLM 출력을 되붙여 넣으면 앱이 **검증 프롬프트**를 만들고, 사용자가 그것을
**새 대화창**에서 실행한다. 같은 대화창에서 돌리면 자기가 쓴 근거에 앵커링되어 결함을 놓친다.

모드는 `config/evaluation_criteria.json`에 있고 `strip_answers` 플래그로 갈린다.

- `blind_solve` (strip_answers: true) — 정답·해설을 제거하고 응시자로서 직접 풀게 한다.
  복수 정답, 모호성, 죽은 선지를 잡는다.
- `full_review` (false) — 정답까지 다 보여 주고 검토위원으로서 진단한다. 근거 환각, 선지 설계.
- `difficulty_check` (false) — 목표 등급에 실제로 맞는지 진단한다.

`EvaluationBuilder.extract_question_items()`가 정답 제거를 담당한다. 단순 치환이 아니라
**추출**이다. 생성 출력에는 분석 단계·후보 목록·자기 점검이 함께 들어 있어서, 문항 블록만
남기고 나머지를 버리는 쪽이 안전하다. 세 개의 정규식이 경계를 정한다.

- `QUESTION_START` — 블록 시작 (`1.` `1)` `[문항 1]` `Q1`)
- `ANSWER_MARKER` / `SECTION_BREAK` — 블록 종료
- `_looks_like_question()` — 선지 마커가 있거나 발문형 어미로 끝나는 블록만 통과.
  후보 목록도 `1.`로 시작하므로 이 필터가 없으면 분석 내용이 블라인드 풀이로 새어 나간다.

정답 제거 로직을 건드리면 `tools/smoke_test.py`의 `check_evaluation()`이 누출을 잡는다.
새로운 정답 표기 방식(`채점 기준:`처럼 키워드 뒤에 수식어가 붙는 형태)을 만나면
`_ANSWER_KEYWORD`에 추가하라.

## UI 구조

화면은 워크플로 3단계를 그대로 반영한다. `StepIndicator`가 상단에 현재 단계를 표시하고,
가운데 세로 스플리터가 `지문 입력 / 생성 결과` 두 카드를 담으며, 그 아래 한 줄짜리 바가
3단계(검증) 진입점이다.

**검증을 세로 스플리터의 세 번째 칸으로 넣지 말 것.** 두 번 시도했고 두 번 다 실패했다.
처음에는 지문 카드 안 접이식 섹션이라 발견성이 없었고, 다음에는 별도 칸으로 올렸더니
세 칸이 약 620px을 나눠 쓰게 되어 펼쳤을 때 내용이 서로 겹쳐 버렸다. 지문·결과 카드의
minimumSizeHint가 커서 스플리터가 공간을 양보하지 못하는 것이 원인이다.
지금은 `EvaluationDialog`가 별도 창으로 뜬다 — 별개 단계이므로 별개 창이 맞다.

`AppSettings`가 테마, 폰트 배율, 가이드 표시 여부, 마지막 세션을 한 파일에 모은다.
새 UI 설정을 추가할 때는 `AppSettings.DEFAULTS`에 키를 넣어야 저장·복원 대상이 된다.
(DEFAULTS에 없는 키는 로드 시 버려진다.)

## 알려진 상태 / 이어서 할 만한 것

- `templates/categories/` 디렉터리는 비어 있고 아무 코드도 참조하지 않는다.
- 최상위 `csat_prompt_generator/` 디렉터리는 `__pycache__`만 남은 예전 구조의 잔재다. (삭제해도 무방)
- 자동화된 테스트가 없다. `tools/smoke_test.py`가 유일한 확인 수단.
- 검증은 아직 사람이 프롬프트를 옮겨 실행해야 한다. API를 붙이면 생성 → 검증 → 재생성이
  자동으로 돌고, 그때 비로소 템플릿 변경의 효과를 점수로 잴 수 있다.
