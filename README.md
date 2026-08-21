# 수능 국어 프롬프트 템플릿 생성기

PySide6 기반의 로컬 데스크톱 앱입니다. macOS와 Windows에서 모두 실행됩니다.  
지문과 보기, 카테고리, 프롬프트 버전, 보조 모듈, 난이도, 문항 수를 설정해 ChatGPT나 다른 LLM 웹 인터페이스에 바로 붙여 넣을 수 있는 수능 국어용 프롬프트를 생성합니다.

이 프로젝트는 웹 앱이 아니며, 데이터베이스 없이 로컬 파일만 사용합니다.

## 프로젝트 개요

이 앱은 한국 수능 국어 문항 설계용 프롬프트를 빠르게 만들기 위한 도구입니다.

- 지문 입력
- 선택형 보기 입력
- 카테고리 선택
- 프롬프트 버전 선택
- 보조 모듈 선택
- 난이도 및 문항 수 설정
- 프리셋 적용
- 결과 미리보기
- 클립보드 복사
- `.txt` / `.md` 저장

템플릿과 프리셋은 외부 파일로 분리되어 있어, 코드를 크게 수정하지 않고도 내용을 조정할 수 있습니다.

## 주요 기능

- 큰 지문 입력 영역과 결과 미리보기 영역
- 다음 카테고리 지원
  - 문학
  - 현대시
  - 현대소설
  - 고전시가
  - 고전소설
  - 독서
  - 문법
  - 언어와 매체
  - 화법과 작문
- 프롬프트 버전 지원
  - 기본형
  - 고급형
  - Ultimate형
- 보조 모듈 지원
  - Anchor Setting 포함
  - CoT 포함
  - Self-Correction 포함
  - 오답 유형 라벨링 포함
  - 난이도 미세조정 포함
- 난이도는 수능 상대평가 등급 기준(1등급 ~ 9등급)
  - 등급별 목표 수준과 지침은 `config/difficulty_profiles.json`에서 관리
- 출제 옵션
  - 문항 형식: 객관식 5지선다 / 4지선다 / 3지선다 / 서술형
  - 출제 묶음: 지문 세트형(수능형) / 독립 문항형 / 혼합형
  - 배점 구조: 수능형 2점·3점 혼합 / 균등 배점 / 고난도 3점 중심
- 자주 쓰는 프리셋 지원
  - 독서 기본형
  - 독서 고난도형
  - 현대시 기본형
  - 현대시 해석통제형
  - 고전시가 보기중심형
  - 고전소설 구조분석형
  - 문법 개념적용형
- 문항 중복 방지 (같은 지문을 여러 번 써도 비슷한 문항이 반복되지 않도록)
  - 문항마다 서로 다른 출제 유형을 강제 배분
  - 회차마다 지문의 다른 지점을 겨냥하도록 초점 이동
  - 같은 지문의 생성 이력을 기억해 이전 회차에서 쓴 유형을 피함
  - 한 문항 안의 오답 선지에 서로 다른 오류 유형을 배분
- 생성 결과 검증 (만들어진 문항이 실제로 쓸 만한지 점검)
  - LLM이 만든 문항을 되붙여 넣으면 검증 프롬프트를 만들어 줌
  - 블라인드 풀이: 정답·해설을 제거하고 직접 풀게 해 복수 정답과 모호성을 검출
  - 정밀 검토: 근거가 실제 지문에 있는지, 선지 설계가 적절한지 진단
  - 난이도 점검: 목표 등급에 실제로 맞는지 진단
- 사용자 정의 프리셋 저장 및 삭제
- 사용자 정의 출제영역 추가 및 삭제
  - 추가 시 `config/category_starter_templates.json`의 시작 템플릿을 예시로 제공
- 단축키
  - Ctrl+Enter: 생성
  - Ctrl+Shift+C: 복사
  - Ctrl+S: .txt 저장
  - Ctrl+Shift+S: .md 저장
  - Ctrl+R: 초기화
- 입력 검증 및 한국어 오류 메시지
- 저장 파일에 메타데이터 포함
  - 제목
  - 생성 시각
  - 카테고리
  - 버전
  - 선택 옵션
  - 지문
  - 보기
  - 최종 생성 프롬프트

## 폴더 구조

```text
csat_prompt_generator/
├─ main.py
├─ app.py
├─ requirements.txt
├─ README.md
├─ CLAUDE.md
├─ CSATPromptGenerator.spec
├─ config/
│  ├─ presets.json
│  ├─ difficulty_profiles.json
│  ├─ category_starter_templates.json
│  ├─ question_types.json
│  ├─ rotation_anchors.json
│  └─ evaluation_criteria.json
├─ core/
│  ├─ __init__.py
│  ├─ evaluation_builder.py
│  ├─ file_utils.py
│  ├─ history_store.py
│  ├─ models.py
│  ├─ preset_loader.py
│  ├─ prompt_builder.py
│  └─ template_loader.py
├─ gui/
│  ├─ __init__.py
│  ├─ main_window.py
│  ├─ styles.py
│  └─ widgets.py
├─ tools/
│  └─ smoke_test.py
└─ templates/
   ├─ common.txt
   ├─ literature.txt
   ├─ modern_poetry.txt
   ├─ modern_novel.txt
   ├─ classical_poetry.txt
   ├─ classical_novel.txt
   ├─ reading.txt
   ├─ grammar.txt
   ├─ language_media.txt
   ├─ speech_writing.txt
   ├─ versions/
   │  ├─ basic.txt
   │  ├─ advanced.txt
   │  └─ ultimate.txt
   └─ modules/
      ├─ anchor.txt
      ├─ cot.txt
      ├─ self_correction.txt
      ├─ distractor_labeling.txt
      └─ difficulty_control.txt
```

## 설치 방법

Python 3.10 이상이 필요합니다. (개발·검증 환경은 Python 3.12)

### macOS / Linux

```bash
cd 경로/csat_prompt_generator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows

PowerShell 기준입니다.

```powershell
cd 경로\csat_prompt_generator
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 실행 방법

가상환경을 활성화한 뒤 다음 둘 중 하나로 실행합니다.

```bash
python main.py
```

또는

```bash
python app.py
```

실제 진입점은 `main.py`이며, `app.py`는 같은 앱을 실행하는 간단한 대체 진입점입니다.

가상환경을 활성화하지 않고 바로 실행할 수도 있습니다.

```bash
.venv/bin/python main.py          # macOS / Linux
.venv\Scripts\python.exe main.py  # Windows
```

## 동작 확인

GUI를 띄우지 않고 템플릿 로딩, 프리셋 로딩, 프롬프트 조립, 윈도우 생성까지 한 번에 점검합니다.

```bash
.venv/bin/python tools/smoke_test.py
```

템플릿이나 설정 JSON을 수정한 뒤에는 이 스크립트를 먼저 돌려 보는 것을 권장합니다.

## 생성 결과 검증하기

만들어진 문항이 실제로 쓸 만한지 앱 안에서 점검할 수 있습니다.
앱은 LLM을 직접 호출하지 않으므로, 생성과 같은 방식으로 프롬프트를 만들어 드립니다.

1. 생성된 프롬프트를 LLM에 넣어 문항을 받습니다.
2. 받은 문항을 그대로 복사해 앱의 `생성 결과 검증` 칸에 붙여 넣습니다.
3. 검증 방식을 고르고 `검증 프롬프트 생성`을 누릅니다.
4. 만들어진 검증 프롬프트를 **반드시 새 대화창에서** 실행합니다.

4번이 중요합니다. 문항을 만든 그 대화창에서 검증하면, 모델이 이미 자기가 쓴 근거에
이끌려 결함을 놓칩니다. 새 대화창에서 실행해야 정직한 판정이 나옵니다.

### 검증 방식

| 방식 | 정답 제공 | 잡아내는 것 |
| --- | --- | --- |
| 블라인드 풀이 | 제거함 | 복수 정답, 모호한 발문, 변별에 기여하지 못하는 선지 |
| 정밀 검토 | 제공함 | 지문에 없는 근거, 선지 설계 결함, 문항 간 중복 |
| 난이도 점검 | 제공함 | 목표 등급과 실제 체감 난이도의 차이 |

블라인드 풀이는 정답과 해설을 앱이 자동으로 제거한 뒤 프롬프트에 넣습니다.
분석 단계나 자기 점검 내용이 섞여 있어도 문항 부분만 골라냅니다.
붙여 넣은 형식이 특이해서 문항을 찾지 못하면 안내 메시지가 뜹니다.

검증 방식과 점검 항목은 `config/evaluation_criteria.json`에서 수정할 수 있습니다.

## 템플릿 커스터마이징 가이드

프롬프트 내용은 모두 외부 텍스트 파일로 분리되어 있습니다.

### 공통 규칙

- `templates/common.txt`

### 카테고리별 지시

- `templates/reading.txt`
- `templates/modern_poetry.txt`
- `templates/classical_poetry.txt`
- `templates/classical_novel.txt`
- `templates/grammar.txt`
- 그 외 나머지 카테고리 템플릿

### 버전별 지시

- `templates/versions/basic.txt`
- `templates/versions/advanced.txt`
- `templates/versions/ultimate.txt`

### 모듈별 지시

- `templates/modules/anchor.txt`
- `templates/modules/cot.txt`
- `templates/modules/self_correction.txt`
- `templates/modules/distractor_labeling.txt`
- `templates/modules/difficulty_control.txt`

### 프리셋 수정

자주 쓰는 설정 조합은 아래 파일에서 관리합니다.

- `config/presets.json`

프리셋은 다음 항목을 자동으로 채웁니다.

- 카테고리
- 버전
- 난이도
- 문항 수
- 선택 모듈
- 문항 형식, 출제 묶음, 배점 구조

프리셋 적용 후에도 사용자가 화면에서 자유롭게 다시 수정할 수 있습니다.

### 문항 유형 수정

문항마다 배분되는 출제 유형은 아래 파일에서 관리합니다.

- `config/question_types.json`

`types` 아래에 영역 이름별로 유형 목록을 둡니다. 목록이 없는 영역(사용자 정의 출제영역 등)은
`default` 목록을 사용합니다. 각 항목은 `name`(유형 이름)과 `focus`(무엇을 평가하는지)로 이루어집니다.

문항 수보다 유형이 많으면 회차가 바뀔 때마다 아직 안 쓴 유형이 먼저 배정됩니다.
**유형을 넉넉히 넣어 둘수록 같은 지문을 여러 번 써도 중복이 덜 생깁니다.**

### 회차 초점 수정

같은 지문을 반복해서 쓸 때 회차마다 지문의 어느 지점을 겨냥할지는 아래 파일에서 관리합니다.

- `config/rotation_anchors.json`

목록 순서대로 순환하며 적용됩니다.

### 난이도 수정

등급별 목표 수준과 지침은 아래 파일에서 관리합니다.

- `config/difficulty_profiles.json`

### 출제영역 시작 템플릿 수정

사용자 정의 출제영역을 추가할 때 예시로 제시되는 문구는 아래 파일에서 관리합니다.

- `config/category_starter_templates.json`

항목 이름은 `"<기본영역>-<세부유형>"` 형식이어야 하며, 앱은 선택한 기본영역 접두사로 후보를 걸러 보여 줍니다.

## 저장 파일 형식

앱에서 `.txt` 또는 `.md`로 저장하면 메타데이터와 최종 프롬프트가 함께 저장됩니다.

예시:

```text
제목: 수능 국어 프롬프트 아카이브 - 독서 / 고급형
생성 시각: 2026-03-23 14:30:00
카테고리: 독서
프롬프트 버전: 고급형
난이도: 2등급
문항 수: 2
선택 옵션: 난이도: 2등급, 문항 수: 2, Anchor Setting 포함

[지문]
...

[보기]
...

[최종 생성 프롬프트]
...
```

## PyInstaller 빌드 방법

PyInstaller는 런타임 필수 패키지가 아니므로, 필요할 때만 별도로 설치합니다.

이 프로젝트는 템플릿과 프리셋을 외부 리소스로 읽기 때문에, 빌드할 때 `templates`와 `config` 폴더를 함께 포함해야 합니다.
코드에서는 `core/file_utils.py`의 `resource_root()`를 사용해 일반 실행과 PyInstaller 번들 실행(`sys._MEIPASS`)을 모두 처리합니다.

### 1. PyInstaller 설치

```bash
pip install pyinstaller
```

### 2. spec 파일로 빌드 (권장)

`CSATPromptGenerator.spec`에 `templates`와 `config` 포함 설정이 이미 들어 있습니다.

```bash
pyinstaller --noconfirm CSATPromptGenerator.spec
```

### 3. spec 없이 직접 빌드

macOS / Linux는 `--add-data` 구분자로 `:`를 사용합니다.

```bash
pyinstaller --noconfirm --windowed --name CSATPromptGenerator \
  --add-data "templates:templates" --add-data "config:config" main.py
```

Windows는 구분자로 `;`를 사용합니다.

```powershell
pyinstaller --noconfirm --windowed --name CSATPromptGenerator --add-data "templates;templates" --add-data "config;config" main.py
```

단일 실행 파일로 만들려면 `--onefile`을 추가합니다.

## 빌드 결과

- macOS one-folder: `dist/CSATPromptGenerator/` 와 `dist/CSATPromptGenerator.app`
- Windows one-folder: `dist/CSATPromptGenerator/`
- Windows single exe: `dist/CSATPromptGenerator.exe`

## 사용자 데이터 저장 위치

사용자가 앱에서 만든 프리셋과 출제영역은 번들 폴더가 아니라 아래 위치에 저장됩니다.

- macOS: `~/Library/Application Support/CSATPromptGenerator/`
- Windows: `%APPDATA%\CSATPromptGenerator\`
- Linux: `~/.local/share/CSATPromptGenerator/`

저장되는 파일은 다음과 같습니다.

- `user_presets.json` — 사용자가 만든 프리셋
- `hidden_presets.json` — 숨긴 기본 프리셋
- `user_categories.json` — 사용자가 추가한 출제영역
- `generation_history.json` — 지문별 생성 이력 (회차 계산과 문항 중복 회피에 사용)

생성 이력에는 지문 원문이 아니라 지문의 해시값과 그 회차에 요청한 문항 유형만 저장됩니다.
지문 입력란 위의 `이력 초기화` 버튼으로 해당 지문의 이력을 지우면 다음 생성이 다시 1회차로 시작합니다.

## 현재 requirements.txt

현재 실제 런타임 의존성은 아래 한 가지입니다.

```text
PySide6>=6.6,<7
```

즉, `requirements.txt`는 현재 코드베이스 기준으로 최소 의존성만 포함합니다.

## 참고

- Python 3.10 이상 권장
- UTF-8 한국어 텍스트 기준
- 인터넷 연결 없이 로컬 실행 가능
- 데이터베이스 사용 없음
- GUI, 비즈니스 로직, 템플릿 로딩, 프리셋 로딩이 분리되어 있음
