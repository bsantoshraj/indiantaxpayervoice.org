"""Fiscal drag: what the old-regime limits set in July 2014 would be if they had followed prices.

The limits come from the Budget Speech of 10 July 2014 (paragraphs 192, 195, 196) and
are unchanged on the Income Tax Department's page for AY 2026-27 (old regime). Prices:
World Bank CPI for India, a financial year April Y - March Y+1 taking
0.75 x CPI(Y) + 0.25 x CPI(Y+1), from FY 2014-15 to the latest complete financial year.

Writes data/fiscal-drag.csv and prints a Markdown table.

Usage:
    python3 -I research/scripts/fiscal_drag.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LIMITS = [  # (what, value in July 2014, unchanged in the old regime since)
    ("Income exempt from tax (under 60)", 250_000),
    ("Income exempt from tax (senior citizens)", 300_000),
    ("Section 80C investments (PPF, EPF, ELSS, life cover…)", 150_000),
    ("Home-loan interest, self-occupied house", 200_000),
]


def main() -> None:
    data = json.loads((ROOT / "sources/a13-worldbank-cpi-india.json").read_text(encoding="utf-8"))
    cpi = {int(r["date"]): r["value"] for r in data[1] if r["value"] is not None}
    fy = lambda y: 0.75 * cpi[y] + 0.25 * cpi[y + 1]  # FY y-(y+1)
    latest = max(y for y in cpi if y + 1 in cpi)
    factor = fy(latest) / fy(2014)
    rows = [{"limit": what, "set_july_2014_inr": v, "today_old_regime_inr": v,
             "if_indexed_inr": round(v * factor, -3), "real_value_today_inr": round(v / factor, -3)}
            for what, v in LIMITS]
    with (ROOT / "data" / "fiscal-drag.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"Prices FY 2014-15 → FY {latest}-{str(latest + 1)[2:]}: ×{factor:.3f} (+{100 * (factor - 1):.0f}%)\n")
    print("| Limit | Set in July 2014, still today | If it had followed prices | What it is worth today, in 2014 rupees |")
    print("|---|---|---|---|")
    lakh = lambda v: f"₹{v / 100_000:.2f} lakh".replace(".00 ", " ")
    for r in rows:
        print(f"| {r['limit']} | {lakh(r['set_july_2014_inr'])} | {lakh(r['if_indexed_inr'])} | {lakh(r['real_value_today_inr'])} |")


if __name__ == "__main__":
    main()
