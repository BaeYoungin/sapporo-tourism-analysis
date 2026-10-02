# AI 문서 분석기 — 설계 문서 ([plan.md](http://plan.md))

---

## 1. 프로젝트 개요


| 항목     | 내용                                       |
| ------ | ---------------------------------------- |
| 프로젝트명  | AI 문서 분석기                                |
| 목적     | 텍스트 문서를 업로드하면 AI가 요약하고 질문에 답변하는 웹 앱      |
| 대상 사용자 | 문서를 빠르게 분석하고 싶은 일반 사용자                   |
| 배포 형태  | Streamlit 로컬 실행 (`streamlit run app.py`) |


---

## 2. 기술 스택 및 의존성

### 기술 스택


| 레이어      | 기술                      |
| -------- | ----------------------- |
| UI 프레임워크 | Python 3.10+, Streamlit |
| AI 모델    | OpenAI `gpt-4o-mini`     |
| 환경변수 관리  | python-dotenv           |


### `requirements.txt`

```
streamlit>=1.32.0
openai>=1.14.0
python-dotenv>=1.0.1
```

---

## 3. 파일 구조 및 역할 정의

```
ai-document-analyzer/
├── app.py            # Streamlit 앱 진입점, UI 렌더링 및 이벤트 처리
├── llm.py            # OpenAI API 호출 로직 (요약, Q&A)
├── utils.py          # 파일 읽기, 텍스트 전처리 유틸리티
├── requirements.txt  # 패키지 의존성
├── .env              # OPENAI_API_KEY (git 제외)
└── plan.md           # 설계 문서 (현재 파일)
```


| 파일         | 책임                                                                |
| ---------- | ----------------------------------------------------------------- |
| `app.py`   | 페이지 레이아웃, 위젯 이벤트, 세션 상태 관리                                        |
| `llm.py`   | `summarize(text)` / `answer(text, question)` 함수 정의, OpenAI 호출 캡슐화 |
| `utils.py` | 업로드 파일 디코딩, 텍스트 정제(공백·특수문자 처리)                                    |


---

## 4. 기능별 세부 설계

### 4-1. 파일 업로드


| 구분     | 내용                                                     |
| ------ | ------------------------------------------------------ |
| **입력** | `.txt` 파일 (Streamlit `st.file_uploader`)               |
| **처리** | `utils.read_uploaded_file(file)` → UTF-8 디코딩, 앞뒤 공백 제거 |
| **출력** | `st.text_area`에 원문 표시, `st.session_state.doc_text`에 저장 |
| **예외** | 빈 파일이면 `st.warning` 표시 후 중단                            |


```python
# utils.py
def read_uploaded_file(file) -> str:
    return file.read().decode("utf-8", errors="ignore").strip()
```

### 4-2. AI 요약


| 구분      | 내용                                                |
| ------- | ------------------------------------------------- |
| **입력**  | `st.session_state.doc_text` (문서 전문)               |
| **처리**  | `llm.summarize(text)` 호출 → OpenAI Chat Completion |
| **출력**  | 300자 이내 요약문을 `st.success` 박스에 표시                  |
| **트리거** | "요약 생성" 버튼 클릭                                     |
| **캐싱**  | `st.session_state.summary`에 저장 (재클릭 시 재생성)        |


### 4-3. Q&A


| 구분      | 내용                                                       |
| ------- | -------------------------------------------------------- |
| **입력**  | 사용자 질문 (`st.text_input`) + `st.session_state.doc_text`   |
| **처리**  | `llm.answer(text, question)` 호출 → OpenAI Chat Completion |
| **출력**  | AI 답변을 `st.info` 박스에 표시                                  |
| **트리거** | "질문하기" 버튼 클릭 또는 Enter                                    |
| **제약**  | 문서가 업로드되지 않은 상태에서 질문 시 `st.warning` 표시                   |


---

## 5. API 호출 설계

### 공통 설정

```python
# llm.py
from openai import OpenAI

client = OpenAI()          # OPENAI_API_KEY 환경변수 자동 참조
MODEL  = "gpt-4o-mini"
```

### 5-1. 요약 API

```python
def summarize(text: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "당신은 문서 요약 전문가입니다. 핵심만 300자 이내 한국어로 요약하세요."
            },
            {
                "role": "user",
                "content": f"다음 문서를 요약해 주세요:\n\n{text[:3000]}"  # 비용 절감용 앞 3000자
            },
        ],
        max_tokens=200,     # 300자 ≈ 200 토큰
        temperature=0.3,    # 일관된 요약을 위해 낮게 설정
    )
    return response.choices[0].message.content.strip()
```


| 파라미터          | 값             | 이유                 |
| ------------- | ------------- | ------------------ |
| `model`       | `gpt-4o-mini`  | 요구사항               |
| `max_tokens`  | `200`         | 300자 이내 제약, 비용 최소화 |
| `temperature` | `0.3`         | 요약은 창의성보다 정확성 우선   |
| 입력 텍스트        | 앞 3,000자 슬라이싱 | 불필요한 토큰 소비 방지      |


### 5-2. Q&A API

```python
def answer(text: str, question: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "문서를 기반으로 질문에 간결하게 답하세요. 문서에 없는 내용은 '문서에서 확인할 수 없습니다'라고 답하세요."
            },
            {
                "role": "user",
                "content": f"문서:\n{text[:3000]}\n\n질문: {question}"
            },
        ],
        max_tokens=300,     # 답변 적절한 길이 허용
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()
```


| 파라미터          | 값     | 이유                 |
| ------------- | ----- | ------------------ |
| `max_tokens`  | `300` | 간결한 답변, 비용 최소화     |
| `temperature` | `0.2` | 사실 기반 답변을 위해 낮게 설정 |


---

## 6. UI 레이아웃 설계

```
┌─────────────────────────────────────────────────┐
│  📄 AI 문서 분석기                               │  ← st.title
│  텍스트 파일을 업로드하고 AI로 분석하세요        │  ← st.caption
├─────────────────────────────────────────────────┤
│  [파일 업로드]  (.txt 파일을 드래그하거나 선택)  │  ← st.file_uploader
│                                                 │
│  ▼ 업로드 시 표시                               │
│  ┌───────────────────────────────────────────┐  │
│  │ 원문 미리보기 (st.text_area, height=200)  │  │
│  └───────────────────────────────────────────┘  │
├─────────────────────────────────────────────────┤
│  📝 AI 요약                                      │  ← st.subheader
│  [요약 생성 버튼]                                │  ← st.button
│  ┌───────────────────────────────────────────┐  │
│  │ 요약 결과 (st.success)                    │  │
│  └───────────────────────────────────────────┘  │
├─────────────────────────────────────────────────┤
│  💬 문서 Q&A                                     │  ← st.subheader
│  [질문 입력창          ] [질문하기]              │  ← st.text_input + st.button
│  ┌───────────────────────────────────────────┐  │
│  │ 답변 결과 (st.info)                       │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### 세션 상태 목록


| 키          | 타입    | 초기값  | 설명         |
| ---------- | ----- | ---- | ---------- |
| `doc_text` | `str` | `""` | 업로드된 문서 원문 |
| `summary`  | `str` | `""` | 생성된 요약 결과  |
| `answer`   | `str` | `""` | 마지막 Q&A 답변 |


---

## 7. 구현 순서 (우선순위)


| 순서  | 작업                                 | 파일                 | 우선순위  |
| --- | ---------------------------------- | ------------------ | ----- |
| 1   | 환경 설정 (`requirements.txt`, `.env`) | —                  | 🔴 필수 |
| 2   | 파일 읽기 유틸리티 구현                      | `utils.py`         | 🔴 필수 |
| 3   | OpenAI 요약 함수 구현                    | `llm.py`           | 🔴 필수 |
| 4   | 파일 업로드 + 원문 표시 UI                  | `app.py`           | 🔴 필수 |
| 5   | 요약 UI 연결 (버튼 → `summarize`)        | `app.py`           | 🔴 필수 |
| 6   | OpenAI Q&A 함수 구현                   | `llm.py`           | 🔴 필수 |
| 7   | Q&A UI 연결 (입력 → `answer`)          | `app.py`           | 🔴 필수 |
| 8   | 에러 처리 (빈 파일, API 오류)               | `app.py`, `llm.py` | 🟡 권장 |
| 9   | 세션 상태로 결과 유지                       | `app.py`           | 🟡 권장 |


---

## 8. 제약 조건 요약


| 제약                    | 대응 방법                                 |
| --------------------- | ------------------------------------- |
| 모델: `gpt-4o-mini` 기본 | 앱 사이드바에서 `gpt-4o`, `gpt-4-turbo` 선택 가능 |
| API 비용 최소화            | 입력 텍스트 앞 3,000자 슬라이싱, `max_tokens` 제한 |
| UI: Streamlit 기본 컴포넌트 | 외부 CSS·JS 미사용, 기본 위젯만 활용              |


---

## 9. 데모 Seed 데이터 (`seed.yaml`)

인터뷰·데모 시 파일 업로드 없이 앱을 즉시 시연할 수 있도록 샘플 문서를 `seed.yaml`로 관리합니다.

### 파일 위치

```
ai-document-analyzer/
└── seed.yaml    # 데모용 샘플 문서 목록
```

### 스키마 구조

```yaml
documents:
  - name: <파일명.txt>       # 문서 식별자 (다운로드 시 파일명)
    label: <UI 표시 라벨>    # 사이드바·버튼에 표시되는 이름 (이모지 포함)
    text: |                  # 문서 본문 (멀티라인 블록 스칼라)
      ...
```

### 로딩 방법 (`seed_documents.py`)

```python
import yaml

def load_seed_documents(path: str = "seed.yaml") -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["documents"]
```

### 현재 포함된 문서


| #   | `name`                          | `label`             | 주요 내용               |
| --- | ------------------------------- | ------------------- | ------------------- |
| 1   | `AI_Market_Report_2025.txt`     | 📊 AI 시장 보고서 (2025) | 시장 규모·트렌드·리스크·권고사항  |
| 2   | `Project_Proposal_EcoApp.txt`   | 🌱 프로젝트 제안서 (친환경 앱) | 문제 정의·솔루션·예산·기대효과   |
| 3   | `Meeting_Minutes_Q2_Review.txt` | 📋 회의록 (Q2 사업 검토)   | 재무 성과·액션 아이템·리스크 관리 |


### seed.yaml 문서 추가 가이드

1. `seed.yaml`의 `documents` 리스트에 항목 추가
2. `name`, `label`, `text` 세 필드 모두 필수
3. 본문은 YAML 블록 스칼라(`|`)로 작성하여 줄바꿈 보존
4. 앱 재시작 없이 파일 저장만으로 즉시 반영

