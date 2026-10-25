"""Article 14: where homes sell, and how much of a home loan's interest the tax system recognises.

1. Sales by ticket size, H1 2025 and H1 2026, eight cities (Knight Frank India Real
   Estate H1 2026, chart "India ticket size split comparison of sales", transcribed
   by hand; the shares above Rs 1 crore add up to the report's own 49% and 54%).
2. An illustration: a home bought with an 80% loan over 20 years at 8.5%. The tax
   system recognises at most Rs 2 lakh of interest a year on a self-occupied home
   under the old regime (unchanged since July 2014) and none under the new regime.

Writes data/a14-ticket-split.csv, data/a14-interest-recognised.csv and
charts/a14-ticket-split.svg. Illustration, not tax advice.

Usage:
    python3 -I research/scripts/article14_housing.py
"""

from __future__ import annotations

import csv
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from charts_article11 import INK, MUTED, ON_RAMP, RAMP, svg, text  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Knight Frank bands (INR mn) -> share of sales (%), bottom of the stacked bar first
SPLIT = {
    "H1 2025": {"<5": 22, "5-10": 29, "10-20": 27, "20-50": 17, "50-100": 4, ">100": 1},
    "H1 2026": {"<5": 19, "5-10": 27, "10-20": 29, "20-50": 20, "50-100": 4, ">100": 1},
}
GROUPS = [("Under ₹50 lakh", ["<5"]), ("₹50 lakh–1 crore", ["5-10"]), ("₹1–2 crore", ["10-20"]),
          ("Above ₹2 crore", ["20-50", "50-100", ">100"])]
PRICES = [50, 100, 150, 200]          # Rs lakh
LOAN_SHARE, RATE, YEARS, CAP = 0.80, 0.085, 20, 2.0


def first_year_interest(loan_lakh: float) -> float:
    r = RATE / 12
    emi = loan_lakh * r / (1 - (1 + r) ** -(YEARS * 12))
    bal, interest = loan_lakh, 0.0
    for _ in range(12):
        i = bal * r
        interest += i
        bal -= emi - i
    return interest


def chart() -> str:
    left, right = 120, 690
    body = [text(20, 30, "More homes now sell above ₹1 crore", 17, weight="bold"),
            text(20, 52, "Share of residential sales by price, eight cities (Knight Frank)", 13, MUTED)]
    x = 20
    for i, (label, _) in enumerate(GROUPS):
        body.append(f'<rect x="{x}" y="70" width="14" height="14" rx="3" fill="{RAMP[i]}"/>')
        body.append(text(x + 20, 82, label, 12.5))
        x += 20 + 7.2 * len(label) + 26
    for row, (period, split) in enumerate(SPLIT.items()):
        y = 104 + row * 66
        body.append(text(left - 12, y + 26, period, 13, INK, "end", "bold"))
        cursor = left
        for i, (label, keys) in enumerate(GROUPS):
            share = sum(split[k] for k in keys)
            w = (right - left) * share / 100
            body.append(f'<rect x="{cursor:.1f}" y="{y}" width="{w - 2:.1f}" height="40" fill="{RAMP[i]}">'
                        f'<title>{escape(period)}, {escape(label)}: {share}% of sales</title></rect>')
            body.append(text(cursor + w / 2, y + 26, f"{share}%", 14, ON_RAMP[i], "middle", "bold"))
            cursor += w
    above_1cr = {p: sum(s[k] for k in ["10-20", "20-50", "50-100", ">100"]) for p, s in SPLIT.items()}
    body.append(text(20, 262, f"Above ₹1 crore: {above_1cr['H1 2025']}% → {above_1cr['H1 2026']}% of sales in a year. "
                              "Under ₹50 lakh: 22% → 19%.", 13.5, INK, weight="bold"))
    body.append(text(20, 282, "Source: Knight Frank, India Real Estate H1 2026 (new homes sold, eight cities).", 12, MUTED))
    desc = "; ".join(f"{p}: " + ", ".join(f"{l} {sum(s[k] for k in ks)}%" for l, ks in GROUPS) for p, s in SPLIT.items())
    return svg(720, 295, "Share of residential sales by price band, H1 2025 and H1 2026", desc + ".", body)


def main() -> None:
    data = ROOT / "data"
    with (data / "a14-ticket-split.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["period"] + [label for label, _ in GROUPS])
        for p, s in SPLIT.items():
            w.writerow([p] + [sum(s[k] for k in ks) for _, ks in GROUPS])
    rows = []
    for price in PRICES:
        loan = price * LOAN_SHARE
        interest = first_year_interest(loan)
        rows.append({"home_price_lakh": price, "loan_lakh": loan, "first_year_interest_lakh": round(interest, 2),
                     "recognised_old_regime_pct": round(100 * min(CAP, interest) / interest),
                     "recognised_new_regime_pct": 0})
    with (data / "a14-interest-recognised.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (ROOT / "charts" / "a14-ticket-split.svg").write_text(chart(), encoding="utf-8")
    print("| Home price | Loan (80%) | Interest in year 1 | Share the tax system recognises: old regime | New regime |")
    print("|---|---|---|---|---|")
    for r in rows:
        print(f"| ₹{r['home_price_lakh']:g} lakh | ₹{r['loan_lakh']:g} lakh | ₹{r['first_year_interest_lakh']:.2f} lakh | "
              f"{r['recognised_old_regime_pct']}% | 0% |")


if __name__ == "__main__":
    main()
