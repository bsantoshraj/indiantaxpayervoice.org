"""Chart for Article 12: tax relief on a rented-out flat's loss, before and after the 2017 cap.

The worked example is computed here (rent, 30% standard deduction, first-year
interest on the loan) and drawn with the Article 11 chart helpers.
Writes research/charts/a12-relief.svg.

Usage:
    python3 -I research/scripts/charts_article12.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from charts_article11 import GRID, INK, LINE, MUTED, OUT, fmt_inr, svg, text  # noqa: E402

LOAN, RATE, YEARS, RENT = 94_00_000, 0.085, 20, 3_00_000
CAP, MARGINAL = 2_00_000, 0.30 * 1.04  # 30% slab plus 4% cess


def example() -> dict:
    r, n = RATE / 12, YEARS * 12
    emi = LOAN * r * (1 + r) ** n / ((1 + r) ** n - 1)
    balance, interest = LOAN, 0.0
    for _ in range(12):
        month = balance * r
        interest += month
        balance -= emi - month
    interest = round(interest, -5)  # "about Rs 8 lakh", as in the article
    loss = interest - (RENT - 0.30 * RENT)
    return {"emi": emi, "interest": interest, "loss": loss,
            "eras": [("Before AY 2018-19", loss), ("From AY 2018-19, old regime", min(loss, CAP)),
                     ("New regime", 0.0)]}


def chart(ex: dict) -> str:
    left, right, top, bottom = 240, 570, 96, 266
    peak = 2_00_000
    body = [text(20, 30, "Tax relief on a rented-out flat's loss", 17, weight="bold"),
            text(20, 52, f"Our example: ₹{ex['loan_lakh']} lakh loan at {RATE:.1%}, ₹{RENT // 100_000} lakh rent, "
                         f"loss of ₹{fmt_inr(ex['loss'])} a year; 30% slab plus cess", 13, MUTED)]
    for value in range(0, peak + 1, 50_000):
        x = left + value / peak * (right - left)
        body.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top - 8}" y2="{bottom}" stroke="{GRID}"/>')
        body.append(text(x, bottom + 18, f"₹{fmt_inr(value)}", 12, MUTED, "middle"))
    step = (bottom - top) / len(ex["eras"])
    for i, (label, set_off) in enumerate(ex["eras"]):
        saved = set_off * MARGINAL
        y = top + i * step + 8
        h = step - 22
        w = saved / peak * (right - left)
        body.append(text(left - 12, y + h / 2 + 5, label, 13, INK, "end", "bold"))
        if w > 0:
            body.append(f'<path d="M{left},{y:.1f} H{left + w - 4:.1f} Q{left + w:.1f},{y:.1f} {left + w:.1f},{y + 4:.1f} '
                        f'V{y + h - 4:.1f} Q{left + w:.1f},{y + h:.1f} {left + w - 4:.1f},{y + h:.1f} H{left} Z" '
                        f'fill="{LINE}"><title>{label}: ₹{fmt_inr(set_off)} of the loss counts; tax saved '
                        f'₹{fmt_inr(saved)} a year</title></path>')
        body.append(text(left + w + 8, y + h / 2 + 5, f"₹{fmt_inr(saved)} a year", 13, INK, "start", "bold"))
    body.append(text(20, 318, "Same flat, same loan: two-thirds of the relief went in 2018-19; the new regime gives none.", 13, INK, weight="bold"))
    body.append(text(20, 338, "Our calculation. Law: Finance Act 2017, s.71(3A); Income Tax Department rules for "
                              "AY 2026-27.", 12, MUTED))
    desc = "; ".join(f"{label}: ₹{fmt_inr(s * MARGINAL)} a year" for label, s in ex["eras"])
    return svg(720, 350, "Tax relief on a rented-out flat's loss, before and after the 2017 cap", desc + ".", body)


def long_loan() -> None:
    """Second example: relief per year under the old rules and under the cap (article12_long_loan.py)."""
    from article12_long_loan import rows
    from charts_timeseries import ORANGE, TEAL, line_chart
    data = [dict(d, assessment_year=d["financial_year"]) for d in rows()]
    lakh = lambda v: f"₹{v / 100_000:.2f}L"
    total = sum(d["extra_tax"] for d in data[1:])
    line_chart("a12-long-loan", "A long loan taken before 2017: relief frozen at ₹62,400",
               "Tax relief a year on a let-out flat: ₹1.95 crore, 30-year loan, EMI ₹1.5 lakh, rent ₹25,000 a month",
               data,
               [("Relief under the old rules", "relief_old_rules", ORANGE, lakh),
                ("Relief allowed since 2017-18", "relief_now", TEAL, lakh)],
               5e5, 1e5, lambda v: f"{v / 100_000:.0f}L",
               f"About ₹{total / 100_000:.1f} lakh more tax over nine years; the unused loss lapses.",
               "Our calculation (illustration, not tax advice): 8.5% fixed, 30% slab plus cess.",
               x_title="Financial year")


def main() -> None:
    long_loan()
    ex = example()
    ex["loan_lakh"] = LOAN // 100_000
    OUT.mkdir(exist_ok=True)
    (OUT / "a12-relief.svg").write_text(chart(ex), encoding="utf-8")
    print(f"EMI ₹{fmt_inr(ex['emi'])}, first-year interest ₹{fmt_inr(ex['interest'])}, loss ₹{fmt_inr(ex['loss'])}")
    print("wrote research/charts/a12-relief.svg")


if __name__ == "__main__":
    main()
