"""
삿포로 관광지 데이터 분석
================================================
입력: data/sapporo_spots.csv  (Firecrawl + WP REST 로 수집한 실제 데이터)
출력: data/analysis/*.csv, data/analysis/summary.json

값을 임의로 만들지 않는다. 모든 수치는 수집 CSV 로부터 계산된 실제 집계값이다.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = DATA / "analysis"

WARDS = [
    "주오구", "기타구", "시로이시구", "아쓰베쓰구", "도요히라구", "기요타구",
    "미나미구", "니시구", "데이네구", "히가시구", "조잔케이", "교외",
]
SUBAREAS = ["삿포로역 주변", "오도리 주변", "스스키노 주변", "나카지마 공원 주변"]
CATEGORY_ORDER = [
    "문화", "체험", "자연", "역사", "공원", "쇼핑", "야경", "기념품",
    "주류", "온천", "이벤트", "아이누 문화", "숙박", "아웃도어", "교통", "기타",
]


def uniq(seq):
    seen = set()
    out = []
    for x in seq:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def main() -> None:
    rows = list(csv.DictReader((DATA / "sapporo_spots.csv").open(encoding="utf-8-sig")))
    total = len(rows)

    def field_split(r, key):
        return uniq([v for v in r[key].split("|") if v])

    cat_counter = Counter()
    ward_counter = Counter()
    subarea_counter = Counter()
    season_counter = Counter()
    matrix = Counter()  # (category, ward)
    with_hours = 0
    with_fee = 0
    free_count = 0
    paid_count = 0
    with_phone = 0
    with_website = 0
    with_address = 0
    with_desc = 0

    cat_examples = {}

    for r in rows:
        cats = field_split(r, "categories")
        areas = field_split(r, "areas")
        seasons = field_split(r, "seasons")
        wards = [a for a in areas if a in WARDS]
        subs = [a for a in areas if a in SUBAREAS]

        for c in cats:
            cat_counter[c] += 1
            cat_examples.setdefault(c, []).append(r["name_ko"] or r["name_ja"])
        for w in wards:
            ward_counter[w] += 1
        for s in subs:
            subarea_counter[s] += 1
        for c in cats:
            for w in wards:
                matrix[(c, w)] += 1
        for s in seasons:
            season_counter[s] += 1

        if r["opening_hours"].strip():
            with_hours += 1
        fee = r["fee"].strip()
        if fee:
            with_fee += 1
            if ("無料" in fee) or ("무료" in fee):
                free_count += 1
            if "円" in fee or "¥" in fee:
                paid_count += 1
        if r["phone"].strip():
            with_phone += 1
        if r["website"].strip():
            with_website += 1
        if r["address"].strip():
            with_address += 1
        if r["description"].strip():
            with_desc += 1

    # 시즌 그룹: 연중 / 계절 / 월
    season_count = {k: v for k, v in season_counter.most_common()}
    year_round = season_counter.get("연중", 0)

    completeness = {
        "명칭(한국어)": sum(1 for r in rows if r["name_ko"].strip()),
        "명칭(일본어)": sum(1 for r in rows if r["name_ja"].strip()),
        "설명": with_desc,
        "카테고리": sum(1 for r in rows if r["categories"].strip()),
        "지역": sum(1 for r in rows if r["areas"].strip()),
        "주소": with_address,
        "전화": with_phone,
        "홈페이지": with_website,
        "운영시간": with_hours,
        "요금": with_fee,
    }

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "site": "https://www.sapporo.travel",
            "operator": "일반사단법인 삿포로 관광협회 (Sapporo Tourist Association)",
            "collector": "Firecrawl (상세 페이지) + WordPress REST API (공식 분류)",
            "dataset_rows": total,
        },
        "headline": {
            "total_spots": total,
            "total_categories": len([c for c in cat_counter if cat_counter[c] > 0]),
            "total_wards": len([w for w in WARDS if ward_counter.get(w, 0) > 0]),
            "top_category": cat_counter.most_common(1)[0][0],
            "top_category_count": cat_counter.most_common(1)[0][1],
            "top_ward": ward_counter.most_common(1)[0][0],
            "top_ward_count": ward_counter.most_common(1)[0][1],
            "with_hours": with_hours,
            "with_fee": with_fee,
            "free_listed": free_count,
            "paid_listed": paid_count,
            "with_phone": with_phone,
            "with_website": with_website,
            "year_round": year_round,
        },
        "category_counts": [[c, n] for c, n in cat_counter.most_common()],
        "ward_counts": [[w, ward_counter.get(w, 0)] for w in WARDS if ward_counter.get(w, 0) > 0],
        "subarea_counts": [[a, subarea_counter.get(a, 0)] for a in SUBAREAS if subarea_counter.get(a, 0) > 0],
        "season_counts": season_count,
        "completeness": completeness,
        "category_ward_matrix": {c: {w: matrix.get((c, w), 0) for w in WARDS} for c in cat_counter},
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    def write_csv(name, header, data):
        with (OUT / name).open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(data)

    write_csv("category_counts.csv", ["category", "count"],
              summary["category_counts"])
    write_csv("ward_counts.csv", ["ward", "count"], summary["ward_counts"])
    write_csv("subarea_counts.csv", ["subarea", "count"], summary["subarea_counts"])
    write_csv("season_counts.csv", ["season", "count"], summary["season_counts"].items())
    write_csv("data_completeness.csv", ["field", "count", "total"],
              [(k, v, total) for k, v in completeness.items()])
    with (OUT / "category_ward_matrix.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["category"] + [x for x, _ in summary["ward_counts"]])
        for c, _ in cat_counter.most_common():
            row = [c] + [matrix.get((c, w), 0) for w, _ in summary["ward_counts"]]
            if any(row[1:]):
                w.writerow(row)

    write_csv("category_examples.csv", ["category", "count", "examples"],
              [[c, n, " / ".join(uniq(cat_examples.get(c, []))[:3])]
               for c, n in cat_counter.most_common()])

    print(json.dumps(summary["headline"], ensure_ascii=False, indent=2))
    print("outputs ->", OUT)


if __name__ == "__main__":
    main()
