"""
삿포로 관광지 데이터 수집 크롤러
================================================
데이터 출처:
  1) Firecrawl  : 삿포로 관광협회 공식 사이트(https://www.sapporo.travel)의
                  관광시설 상세 페이지(일본어/한국어) - 운영정보, 명칭, 설명 수집
  2) WP REST API: 동일 사이트의 공식 분류(spotcat/area/season) 메타데이터
                  (LLM 추론이 아닌 사이트가 직접 부여한 태그)

원칙:
  - 실제 사이트에서 수집한 값만 저장한다. 값을 임의로 생성/보정하지 않는다.
  - 응답은 data/raw/<slug>.json 에 캐시하여 재실행 시 크레딧 재소모를 막는다.

사용법:
  python crawler.py --discover          # 시설 URL/분류 목록만 갱신(무료, Firecrawl 미사용)
  python crawler.py --limit 3           # 앞 3개만 수집(테스트)
  python crawler.py                     # 전체 수집
  python crawler.py --force             # 캐시 무시하고 재수집
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
META = DATA / "meta"

BASE = "https://www.sapporo.travel"
SITEMAP = BASE + "/ko/wp-sitemap-posts-facility-1.xml"
REST = BASE + "/wp-json/wp/v2"
UA = {"User-Agent": "Mozilla/5.0 (compatible; SapporoDataResearch/1.0; educational data collection)"}

try:  # Windows 콘솔(cp949)에서 유니코드 출력 오류 방지
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

# 사이트 공식 taxonomy slug -> 한국어 라벨 (공식 표기 번역)
SPOTCAT_KO = {
    "sc01-onsen": "온천",
    "sc02-history": "역사",
    "sc03-culture": "문화",
    "sc04-art": "예술",
    "sc05-parks": "공원",
    "sc06-nature": "자연",
    "sc07-yakei": "야경",
    "sc08-shops": "쇼핑",
    "sc09-recreational": "체험",
    "sc10-sports": "스포츠",
    "sc11-outdoor": "아웃도어",
    "sc12-drink": "주류",
    "sc13-ainu": "아이누 문화",
    "sc14-event": "이벤트",
    "sc20-hotel": "숙박",
    "sc25-traffic": "교통",
    "sc99-other": "기타",
    "sc-foods": "기념품",
    "%e3%82%a4%e3%83%99%e3%83%b3%e3%83%88": "이벤트",
    "%e3%81%8a%e5%9c%9f%e7%94%a3": "기념품",
}
SPOTCAT_KO_BY_NAME = {"イベント": "이벤트", "お土産": "기념품"}

SEASON_KO = {
    "m-01": "1월", "m-02": "2월", "m-03": "3월", "m-04": "4월",
    "m-05": "5월", "m-06": "6월", "m-07": "7월", "m-08": "8월",
    "m-09": "9월", "m-10": "10월", "m-11": "11월", "m-12": "12월",
    "s-spring": "봄", "s-summer": "여름", "s-autumn": "가을", "s-winter": "겨울",
    "m-all": "연중",
}

AREA_KO = {
    "a01-chuo": "주오구",
    "a02-kita": "기타구",
    "a03-shiroishi": "시로이시구",
    "a04-atsubetsu": "아쓰베쓰구",
    "a05-toyohira": "도요히라구",
    "a06-kiyota": "기요타구",
    "a07-minami": "미나미구",
    "a08-nishi": "니시구",
    "a09-teine": "데이네구",
    "a10-higashi": "히가시구",
    "a11-jozankei": "조잔케이",
    "a50-suburbs": "교외",
    "a01-chuo-01-sapporo": "삿포로역 주변",
    "a01-chuo-02-odori": "오도리 주변",
    "a01-chuo-03-susukino": "스스키노 주변",
    "a01-chuo-04-nakjima": "나카지마 공원 주변",
}


def log(msg: str) -> None:
    print(msg)
    sys.stdout.flush()


def clean_text(s: str) -> str:
    s = re.sub(r"<br\s*/?>", " ", s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    s = html_lib.unescape(s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


# --------------------------------------------------------------------------
# 1) discovery: 시설 URL, 공식 분류 목록
# --------------------------------------------------------------------------
def discover() -> dict:
    META.mkdir(parents=True, exist_ok=True)

    sm = requests.get(SITEMAP, headers=UA, timeout=30).text
    paths = re.findall(r"<loc>(https://www\.sapporo\.travel/[^<]*?/facility/[^<]+)</loc>", sm)
    facilities = []
    seen = set()
    for u in paths:
        slug = u.rstrip("/").split("/facility/")[-1]
        if slug in seen:
            continue
        seen.add(slug)
        # 사이트 내 경로(언어 프리픽스 없음)를 보존
        path = u.replace(BASE, "")
        facilities.append({"slug": slug, "path": path})
    facilities.sort(key=lambda x: x["slug"])

    tax = {}
    for name in ("spotcat", "area", "season"):
        r = requests.get(f"{REST}/{name}?per_page=100", headers=UA, timeout=30)
        terms = r.json() if r.status_code == 200 else []
        tax[name] = [
            {"id": t["id"], "slug": t.get("slug"), "name": clean_text(t.get("name", ""))}
            for t in terms
        ]

    meta = {"facilities": facilities, "taxonomies": tax, "source": SITEMAP}
    (META / "discovery.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"[discover] facilities={len(facilities)} taxonomies={ {k: len(v) for k, v in tax.items()} }")
    return meta


def load_or_discover() -> dict:
    p = META / "discovery.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return discover()


def fetch_rest_facilities() -> dict:
    """slug -> {id, title_ja_rest, spotcat_ids[], area_ids[], season_ids[]}"""
    out = {}
    page = 1
    while page <= 15:
        url = f"{REST}/facility?per_page=100&page={page}&_fields=id,slug,title,spotcat,area,season"
        r = requests.get(url, headers=UA, timeout=60)
        if r.status_code != 200:
            break
        try:
            items = r.json()
        except Exception:  # noqa: BLE001
            break
        if not items:
            break
        for item in items:
            out[item["slug"]] = {
                "id": item.get("id"),
                "title_ja_rest": clean_text((item.get("title") or {}).get("rendered", "")),
                "spotcat_ids": item.get("spotcat") or [],
                "area_ids": item.get("area") or [],
                "season_ids": item.get("season") or [],
            }
        page += 1
    return out


# --------------------------------------------------------------------------
# 2) Firecrawl 수집
# --------------------------------------------------------------------------
def get_client():
    load_dotenv(PROJECT_ROOT / ".env")
    key = os.getenv("FIRECRAWL_API_KEY")
    if not key:
        raise SystemExit("FIRECRAWL_API_KEY 가 .env 에 없습니다.")
    from firecrawl import Firecrawl

    return Firecrawl(api_key=key)


# Firecrawl 플랜 요청 제한 대응: 60초 슬라이딩 윈도우로 분당 호출 수 제한
import collections  # noqa: E402

_REQ_TIMES: "collections.deque[float]" = collections.deque()
_MAX_PER_MIN = 10


def _rate_limit() -> None:
    while True:
        now = time.time()
        while _REQ_TIMES and now - _REQ_TIMES[0] > 60:
            _REQ_TIMES.popleft()
        if len(_REQ_TIMES) < _MAX_PER_MIN:
            _REQ_TIMES.append(now)
            return
        wait = 60 - (now - _REQ_TIMES[0]) + 1.0
        log(f"[rate] 60초 제한 대기 {wait:.1f}s")
        time.sleep(wait)


def scrape(client, url: str, formats: list, retries: int = 4) -> dict:
    last = None
    for attempt in range(retries + 1):
        _rate_limit()
        try:
            doc = client.scrape(url, formats=formats, only_main_content=True, timeout=60000)
            return {
                "markdown": getattr(doc, "markdown", None),
                "html": getattr(doc, "html", None),
                "metadata": _meta_to_dict(getattr(doc, "metadata", None)),
            }
        except Exception as e:  # noqa: BLE001
            last = e
            wait = 8 * (attempt + 1)
            log(f"[retry] {url} ({attempt + 1}/{retries}) {wait}s 후 재시도")
            time.sleep(wait)
    raise RuntimeError(f"scrape failed {url}: {last}")


def _meta_to_dict(meta) -> dict:
    if meta is None:
        return {}
    if isinstance(meta, dict):
        return meta
    if hasattr(meta, "model_dump"):
        try:
            return meta.model_dump()
        except Exception:  # noqa: BLE001
            pass
    return {k: getattr(meta, k) for k in dir(meta) if not k.startswith("_") and not callable(getattr(meta, k))}


def parse_section_data(html: str) -> dict:
    pairs = re.findall(
        r"<dt[^>]*section-data_label[^>]*>(.*?)</dt>\s*<dd[^>]*section-data_content[^>]*>(.*?)</dd>",
        html or "",
        re.S,
    )
    result = {}
    for label, value in pairs:
        result[clean_text(label)] = clean_text(value)
    return result


def first_paragraph(markdown: str) -> str:
    for line in (markdown or "").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("!") or s.startswith("[") or s.startswith("|") or s.startswith("-"):
            continue
        if s.startswith("http") or len(s) < 25:
            continue
        return clean_text(s)
    return ""


def name_from_markdown(markdown: str) -> str:
    for line in (markdown or "").splitlines():
        s = line.strip()
        if s.startswith("# "):
            return clean_text(s[2:])
    return ""


def name_from_html(html: str) -> str:
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html or "", re.S)
    return clean_text(m.group(1)) if m else ""


def collect_one(client, fac: dict) -> dict:
    slug = fac["slug"]
    path = fac["path"]
    jp_url = BASE + path
    ko_url = BASE + "/ko" + path

    jp = scrape(client, jp_url, ["markdown", "html"])
    time.sleep(0.4)
    ko = scrape(client, ko_url, ["markdown"])

    jp_info = parse_section_data(jp.get("html") or "")
    ko_info = parse_section_data(ko.get("markdown") or "")

    return {
        "slug": slug,
        "url_ja": jp_url,
        "url_ko": ko_url,
        "name_ja": name_from_markdown(jp.get("markdown") or "") or name_from_html(jp.get("html") or ""),
        "name_ko": name_from_markdown(ko.get("markdown") or ""),
        "desc_ja": first_paragraph(jp.get("markdown") or ""),
        "desc_ko": first_paragraph(ko.get("markdown") or ""),
        "info_ja": jp_info,
        "info_ko": ko_info,
        "meta_ja": jp.get("metadata") or {},
    }


# --------------------------------------------------------------------------
# 3) 병합 및 CSV 저장
# --------------------------------------------------------------------------
def map_terms(ids, terms, ko_map, ko_by_name) -> list:
    by_id = {t["id"]: t for t in terms}
    out = []
    for tid in ids:
        t = by_id.get(tid)
        if not t:
            continue
        label = ko_map.get(t.get("slug") or "") or ko_by_name.get(t.get("name") or "")
        out.append(label or t.get("name") or str(tid))
    return out


def build_records(discovery, rest_facs, force=False):
    client = get_client()
    RAW.mkdir(parents=True, exist_ok=True)
    records = []
    facs = discovery["facilities"]
    for i, fac in enumerate(facs, 1):
        slug = fac["slug"]
        cache = RAW / f"{slug}.json"
        if cache.exists() and not force:
            raw = json.loads(cache.read_text(encoding="utf-8"))
            log(f"[{i}/{len(facs)}] cache  {slug}")
        else:
            try:
                raw = collect_one(client, fac)
            except Exception as e:  # noqa: BLE001
                log(f"[{i}/{len(facs)}] FAIL   {slug}: {e}")
                continue
            cache.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
            log(f"[{i}/{len(facs)}] fetch  {slug}")
            time.sleep(0.4)

        rf = rest_facs.get(slug, {})
        info_ja = raw.get("info_ja", {}) or {}
        info_ko = raw.get("info_ko", {}) or {}
        tax = discovery["taxonomies"]
        records.append(
            {
                "slug": slug,
                "name_ko": raw.get("name_ko") or "",
                "name_ja": raw.get("name_ja") or rf.get("title_ja_rest") or "",
                "categories": "|".join(map_terms(rf.get("spotcat_ids", []), tax["spotcat"], SPOTCAT_KO, SPOTCAT_KO_BY_NAME)),
                "areas": "|".join(map_terms(rf.get("area_ids", []), tax["area"], AREA_KO, {})),
                "seasons": "|".join(map_terms(rf.get("season_ids", []), tax["season"], SEASON_KO, {})),
                "address": info_ja.get("住所") or info_ko.get("주소") or "",
                "opening_hours": info_ja.get("営業時間") or "",
                "closed_days": info_ja.get("定休日") or "",
                "fee": info_ja.get("料金") or "",
                "parking": info_ja.get("駐車場") or "",
                "phone": info_ja.get("電話") or "",
                "website": info_ja.get("公式サイト") or info_ko.get("홈페이지") or "",
                "notes": info_ja.get("備考") or "",
                "description": raw.get("desc_ko") or raw.get("desc_ja") or "",
                "description_ja": raw.get("desc_ja") or "",
                "url": raw.get("url_ko") or "",
            }
        )
    return records


COLUMNS = [
    "slug", "name_ko", "name_ja", "categories", "areas", "seasons", "address",
    "opening_hours", "closed_days", "fee", "parking", "phone", "website",
    "notes", "description", "description_ja", "url",
]


def write_csv(records):
    import csv

    DATA.mkdir(parents=True, exist_ok=True)
    out = DATA / "sapporo_spots.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in records:
            w.writerow({k: r.get(k, "") for k in COLUMNS})
    log(f"[csv] {len(records)} rows -> {out}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--discover", action="store_true", help="시설/분류 목록만 갱신")
    ap.add_argument("--limit", type=int, default=0, help="앞 N개만 수집(테스트)")
    ap.add_argument("--force", action="store_true", help="캐시 무시")
    args = ap.parse_args()

    if args.discover:
        discover()
        return

    discovery = load_or_discover()
    if args.limit:
        discovery = dict(discovery)
        discovery["facilities"] = discovery["facilities"][: args.limit]

    rest_facs = fetch_rest_facilities()
    log(f"[rest] facilities={len(rest_facs)}")
    records = build_records(discovery, rest_facs, force=args.force)

    if args.limit:
        for r in records:
            log(json.dumps({k: r[k] for k in ("slug", "name_ko", "name_ja", "categories", "areas", "address")}, ensure_ascii=False))
    else:
        write_csv(records)


if __name__ == "__main__":
    main()
