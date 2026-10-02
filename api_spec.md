# OpenAI API 호출 명세 — AI 문서 분석기

본 문서는 **Chat Completions** 기준으로 요약·Q&A 기능의 호출 형식, 응답, 오류, 비용을 정리한다.  
SDK: 공식 `openai` Python 패키지 (`openai >= 1.0.0`).

---

## 공통

| 항목 | 값 |
|------|-----|
| **HTTP 엔드포인트** | `POST https://api.openai.com/v1/chat/completions` |
| **SDK** | `client.chat.completions.create(...)` |
| **모델** | `gpt-4o-mini` (고정) |
| **인증** | 헤더 `Authorization: Bearer <OPENAI_API_KEY>` (SDK는 환경 변수 또는 `api_key` 인자) |

---

## 1. 요약 기능 API 호출

### 1.1 엔드포인트·모델

- **엔드포인트**: `chat/completions` (`/v1/chat/completions`)
- **모델**: `gpt-4o-mini`

### 1.2 시스템 프롬프트 (권장 문안)

역할과 출력 제약을 짧게 고정한다.

```text
당신은 문서 요약 도우미입니다. 주어진 문서만을 근거로 한국어로 핵심을 압축합니다.
출력은 본문만 작성하고, 공백 포함 300자 이하여야 합니다. 목록·따옴표·메타 설명은 넣지 마세요.
```

(구현 시 한 줄로 압축해도 된다.)

### 1.3 입력 형식 (`messages`)

| role | content 구성 |
|------|----------------|
| `system` | 위 시스템 프롬프트 문자열 |
| `user` | 아래 템플릿에 **문서 본문**을 삽입 |

**사용자 메시지 템플릿 (예시)**

```text
다음 문서를 요약하세요.

---
{document_text}
```

- `document_text`: 업로드·추출된 전체 또는 앱에서 정한 **최대 문자/토큰 상한까지 절단한 문자열**.
- 절단 시 사용자 메시지 끝에 한 줄 안내 가능: `[이하 생략]` (토큰 절약을 위해 짧게).

### 1.4 기타 파라미터 (권장)

| 파라미터 | 권장값 | 설명 |
|----------|--------|------|
| `temperature` | `0.2` ~ `0.3` | 요약 일관성·사실 복기에 유리 |
| `max_tokens` | **128 ~ 256** | 한글 300자 목표면 상한을 과하게 쓰지 않음 (§4 참고) |

### 1.5 예상 응답 형식

**HTTP 200** 시 본문(JSON)의 핵심 경로:

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "gpt-4o-mini",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "한 줄 또는 짧은 단락의 요약 문자열"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0
  }
}
```

**앱에서 사용하는 값**

- `choices[0].message.content` → `str` (요약 결과)
- `finish_reason`이 `length`이면 모델이 `max_tokens`에 걸린 것이므로, 필요 시 앱에서 300자 절단 또는 재요청 정책 결정

**SDK (Python) 예시**

```python
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "<시스템 프롬프트>"},
        {"role": "user", "content": "<템플릿 + document_text>"},
    ],
    temperature=0.3,
    max_tokens=200,
)
text = response.choices[0].message.content or ""
```

---

## 2. Q&A 기능 API 호출

### 2.1 엔드포인트·모델

- **엔드포인트**: `chat/completions`
- **모델**: `gpt-4o-mini`

### 2.2 문서 + 질문 결합 프롬프트 구조

단일 `user` 메시지 안에 **문서 본문**과 **질문**을 구획으로 넣어 환각을 줄인다.

**시스템 프롬프트 (권장 문안)**

```text
당신은 문서 기반 질의응답 도우미입니다. 아래에 주어진 문서만을 근거로 답하세요.
문서에 근거가 없으면 "문서에서 확인할 수 없습니다."라고 답하세요. 추측하지 마세요. 한국어로 답합니다.
```

**사용자 메시지 템플릿 (예시)**

```text
[문서]
{document_text}

[질문]
{user_question}
```

- `document_text`: 토큰 한도를 넘지 않도록 앱에서 절단한 본문.
- `user_question`: UI에서 받은 질문 문자열 (`strip()` 후 빈 문자열이면 **API 호출 금지**).

### 2.3 입력 형식 요약

| role | 내용 |
|------|------|
| `system` | 위 시스템 프롬프트 |
| `user` | `[문서]` 블록 + `[질문]` 블록 (템플릿) |

### 2.4 기타 파라미터 (권장)

| 파라미터 | 권장값 |
|----------|--------|
| `temperature` | `0.2` ~ `0.4` |
| `max_tokens` | **256 ~ 512** (답변이 짧을 것이면 256부터) |

### 2.5 응답 형식

요약과 동일하게 `choices[0].message.content`를 답변 본문으로 사용한다.  
`finish_reason`이 `length`이면 잘린 답변일 수 있으므로 UI에 “일부만 표시” 등 정책을 둘 수 있다.

**SDK (Python) 예시**

```python
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "<Q&A 시스템 프롬프트>"},
        {"role": "user", "content": f"[문서]\n{doc}\n\n[질문]\n{question}"},
    ],
    temperature=0.3,
    max_tokens=384,
)
answer = response.choices[0].message.content or ""
```

---

## 3. 에러 처리

구현 시 OpenAI Python SDK 예외·HTTP 상태를 구분한다. 사용자에게는 **키·원문이 노출되지 않는** 짧은 메시지를 쓴다.

### 3.1 API 키 오류

| 신호 | 예시 |
|------|------|
| HTTP **401** | 잘못된 키, 만료, 프로젝트 권한 문제 |
| SDK | `openai.AuthenticationError` (또는 동등한 인증 관련 예외) |

**처리**

- UI: “API 키를 확인해 주세요.”
- 앱: `.env`의 `OPENAI_API_KEY` 재설정 안내

### 3.2 토큰 초과

| 신호 | 의미 |
|------|------|
| HTTP **400**, 메시지에 `context_length_exceeded` 등 | 요청 `messages`가 모델 컨텍스트 한도 초과 |
| `finish_reason: "length"` (성공 200이지만) | 출력이 `max_tokens` 상한으로 잘림 |

**처리**

- **입력 초과**: `document_text` 절단 상한을 낮추거나, 앞부분만 보내는 정책 적용 후 재시도.
- **출력 잘림**: `max_tokens` 상향(비용 증가) 또는 질문을 더 구체화해 재호출.

### 3.3 네트워크 오류

| 신호 | 예시 |
|------|------|
| 연결 실패·DNS·타임아웃 | `APIConnectionError`, `APITimeoutError` 등 |
| HTTP **5xx** | 서버/게이트웨이 일시 오류 |

**처리**

- 클라이언트에 **타임아웃** 설정(예: 60초).
- UI: “일시적으로 연결할 수 없습니다.” / “시간이 초과되었습니다. 다시 시도해 주세요.”
- 자동 재시도는 비용·지연이 커질 수 있어 **기본은 비권장**; 필요 시 지수 백오프 1~2회만 검토.

### 3.4 기타

| 신호 | 처리 요약 |
|------|-----------|
| **429** Rate limit | “잠시 후 다시 시도해 주세요.” |
| **400** (모델명·파라미터) | 로그에만 상세, UI는 일반화된 오류 문구 |

---

## 4. 비용 최적화

### 4.1 프롬프트 설계 팁 (입력 토큰 절약)

- 시스템 프롬프트는 **짧고 고정**; 매 호출마다 긴 예시를 넣지 않는다.
- 문서가 길면 **문자 수 또는 토큰 추정 상한**으로 잘라 보내고, `[이하 생략]` 한 줄로 끝낸다.
- 요약과 Q&A에서 **같은 문서**를 반복 호출할 때는, 변경이 없으면 요약 결과를 세션에 캐시해 **재요약 API 호출을 생략**한다.
- Q&A 질문은 `strip()` 후 빈 문자열이면 호출하지 않는다.

### 4.2 `max_tokens` 권장값

| 기능 | 권장 범위 | 비고 |
|------|-----------|------|
| **요약** (300자 목표) | **128 ~ 256** | 한글은 토큰당 문자 수가 적어, 200 전후로도 대부분 충분 |
| **Q&A** | **256 ~ 512** | 한두 문단 답변이면 256부터; 긴 설명이 필요할 때만 상향 |

`temperature`는 **0.2~0.4**로 낮게 유지해 불필요한 장황한 출력을 줄인다.

---

## 버전

- 문서: 초안 (프로젝트 `plan.md`의 Chat Completions·모델 정책과 정합)

실제 API 필드명·에러 타입은 사용 중인 `openai` 패키지 버전의 공식 문서와 릴리스 노트를 함께 확인한다.
