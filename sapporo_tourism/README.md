# 삿포로 관광지 데이터 분석

삿포로 관광협회 공식 사이트(https://www.sapporo.travel)의 관광시설 데이터를 **Firecrawl**로 수집하고
분석하여, 발표용 HTML 슬라이드 덱으로 만드는 프로젝트입니다.

## 결과물

| 결과물 | 경로 |
|--------|------|
| 발표 슬라이드 (GitHub Pages) | `../docs/index.html` |
| 수집 데이터셋 | `data/sapporo_spots.csv` (132행 × 17열) |
| 분석 요약 | `data/analysis/summary.json` |
| 분석 표 | `data/analysis/*.csv` |

## 데이터 수집 원칙

- 실제 사이트에서 수집한 값만 사용하며, 값을 임의로 생성하거나 보정하지 않습니다.
- 수집 대상: 관광시설 **132곳** (공식 sitemap 기준)
- 수집 도구·출처
  - **Firecrawl** — 일본어 상세페이지(운영정보), 한국어 페이지(명칭·설명)
  - **WordPress REST API** — 사이트가 직접 부여한 공식 분류(카테고리/지역/계절)
- 응답은 `data/raw/<slug>.json`에 캐시되어 재실행 시 재수집을 방지합니다.

## 수집 필드

`name_ko, name_ja, categories, areas, seasons, address, opening_hours,
closed_days, fee, parking, phone, website, notes, description, url`

## 실행 방법

```bash
pip install firecrawl-py python-dotenv requests
# 프로젝트 루트 .env 에 FIRECRAWL_API_KEY 설정

cd sapporo_tourism
python crawler.py --discover   # 시설/분류 목록 갱신 (무료, Firecrawl 미사용)
python crawler.py              # 전체 수집 (실패 시 재실행하면 캐시로 재개)
python analyze.py              # 분석 → data/analysis/*
python build_deck.py           # 발표 슬라이드 → ../docs/index.html
```

## 슬라이드 조작

- `←`/`→`, `Space`, `PageUp`/`PageDown` : 이동
- 화면 우하단 버튼 : 이전/다음
- URL 해시 `#5` : 특정 슬라이드로 바로 이동
- `index.html?static=1` : 애니메이션 없이 정적 표시 (인쇄/캡처용)

## 저작권

원천 데이터의 저작권은 삿포로 관광협회에 있습니다. 본 자료는 **교육·분석 목적**으로만 사용하며,
원문·이미지의 무단 재배포는 지양하고 출처를 명시합니다.
