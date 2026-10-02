"""
발표용 HTML 슬라이드 덱 빌드
================================================
입력: data/analysis/summary.json, data/analysis/category_examples.csv
출력: ../../docs/index.html  (GitHub Pages 및 로컬 file:// 실행 가능)

Chart.js 는 docs/vendor/chart.umd.min.js 로컬 파일을 사용하므로 오프라인에서도 동작한다.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "analysis"
TEMPLATE = ROOT / "slides" / "template.html"
DOCS = ROOT.parent / "docs"


def main() -> None:
    summary = json.loads((DATA / "summary.json").read_text(encoding="utf-8"))

    examples = []
    with (DATA / "category_examples.csv").open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            examples.append([row["category"], int(row["count"]), row["examples"]])
    # 카드에는 상위 6개만
    summary["examples"] = examples[:6]

    generated = date.today().isoformat()
    tpl = TEMPLATE.read_text(encoding="utf-8")
    html = tpl.replace("__DATA__", json.dumps(summary, ensure_ascii=False)).replace("__GENERATED__", generated)

    DOCS.mkdir(parents=True, exist_ok=True)
    out = DOCS / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"built -> {out}  ({len(html):,} bytes, generated {generated})")


if __name__ == "__main__":
    main()
