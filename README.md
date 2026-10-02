# 📄 AI Document Analyzer

Streamlit + OpenAI 기반 문서 분석 어플리케이션

## 기능

| 기능 | 설명 |
|------|------|
| 📝 요약 | 짧게 / 보통 / 자세히 세 가지 길이로 문서 요약 |
| 💬 Q&A 챗봇 | 문서 내용 기반 질문 답변 (대화 히스토리 유지) |
| 💡 핵심 인사이트 | 주제 / 할 일 / 수치 / 결론 / 위험 요소 추출 |
| 📃 원문 보기 | 추출된 텍스트 확인 및 다운로드 |

## 지원 파일 형식

- PDF (`.pdf`)
- Word 문서 (`.docx`)
- 텍스트 (`.txt`)

## 설치 및 실행

```bash
# 패키지 설치
pip install -r requirements.txt

# API 키 설정 (선택)
cp .env.example .env
# .env 파일에서 OPENAI_API_KEY 입력

# 실행
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속

## 환경변수

| 변수 | 설명 |
|------|------|
| `OPENAI_API_KEY` | OpenAI API 키 (앱 사이드바에서도 입력 가능) |

## 사용 모델

- `gpt-4o-mini` (기본, 빠르고 저렴)
- `gpt-4o`
- `gpt-4-turbo`

## 📊 삿포로 관광지 데이터 분석 (부가 프로젝트)

이 저장소에는 별도로 **삿포로 관광지 데이터 분석** 작업이 포함되어 있습니다.
Firecrawl로 삿포로 관광협회 공식 사이트의 관광시설 132곳을 수집·분석하고,
발표용 HTML 슬라이드 덱을 생성합니다.

- 슬라이드: `docs/index.html` (GitHub Pages로 배포)
- 소스/문서: [`sapporo_tourism/`](sapporo_tourism/README.md)
- 데이터셋: `sapporo_tourism/data/sapporo_spots.csv`

```bash
cd sapporo_tourism
python crawler.py && python analyze.py && python build_deck.py
```

