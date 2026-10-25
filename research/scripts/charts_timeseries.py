"""Charts for the twelve-year picture (AY 2012-13 to 2023-24), as inline SVG.

Reads data/timeseries.csv (analyse_timeseries.py) and writes research/charts/ts-*.svg.
Colours: a teal / orange pair checked with the dataviz validator (CVD and
normal-vision separation, chroma, contrast); single-series charts use the teal.
Every point carries a hover title; each series is labelled at its end.

Usage:
    python3 -I research/scripts/charts_timeseries.py
"""

from __future__ import annotations

import csv
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from charts_article11 import GRID, INK, MUTED, OUT, SURFACE, svg, text  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEAL, ORANGE = "#00897B", "#B4570B"


def load() -> list[dict]:
    with (ROOT / "data" / "timeseries.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def line_chart(name, title, subtitle, rows, series, y_max, y_step, y_fmt, takeaway, source, mark=None):
    """series: [(label, key, colour, value_fmt)]; mark: (assessment year, note) drawn as a dashed rule."""
    left, right, top, bottom = 64, 600, 96, 316
    n = len(rows)
    xs = [left + i * (right - left) / (n - 1) for i in range(n)]

    def y(v):
        return bottom - v / y_max * (bottom - top)

    body = [text(20, 30, title, 17, weight="bold"), text(20, 52, subtitle, 13, MUTED)]
    if len(series) > 1:
        x = 20
        for label, _, colour, _ in series:
            body.append(f'<line x1="{x}" x2="{x + 18}" y1="72" y2="72" stroke="{colour}" stroke-width="3"/>')
            body.append(text(x + 24, 76, label, 12.5))
            x += 24 + 7 * len(label) + 26
    v = 0
    while v <= y_max + 1e-9:
        body.append(f'<line x1="{left}" x2="{right}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{GRID}"/>')
        body.append(text(left - 8, y(v) + 4, y_fmt(v), 12, MUTED, "end"))
        v += y_step
    for i, r in enumerate(rows):
        if (n - 1 - i) % 2 == 0:
            body.append(text(xs[i], bottom + 20, r["assessment_year"], 11.5, MUTED, "middle"))
    body.append(text((left + right) / 2, bottom + 40, "Assessment year (income earned the year before)", 11.5,
                     MUTED, "middle"))
    if mark:
        i = [r["assessment_year"] for r in rows].index(mark[0])
        body.append(f'<line x1="{xs[i]:.1f}" x2="{xs[i]:.1f}" y1="{top - 6}" y2="{bottom}" stroke="{MUTED}" '
                    f'stroke-dasharray="4 4"/>')
        body.append(text(xs[i] - 6, top + 6, mark[1], 11.5, INK, "end", "bold"))
    ends = set()
    for label, key, colour, value_fmt in series:
        values = [float(r[key]) for r in rows]
        path = "M" + " L".join(f"{xs[i]:.1f},{y(v):.1f}" for i, v in enumerate(values))
        body.append(f'<path d="{path}" fill="none" stroke="{colour}" stroke-width="2.5" stroke-linejoin="round"/>')
        for i, v in enumerate(values):
            body.append(f'<circle cx="{xs[i]:.1f}" cy="{y(v):.1f}" r="4" fill="{colour}" stroke="{SURFACE}" '
                        f'stroke-width="1.5"><title>{escape(label)}, AY {rows[i]["assessment_year"]}: '
                        f'{escape(value_fmt(v))}</title></circle>')
        body.append(text(xs[0] + 6, y(values[0]) - 10, value_fmt(values[0]), 12, INK, "start", "bold"))
        end_label = (round(y(values[-1])), value_fmt(values[-1]))
        if end_label not in ends:
            ends.add(end_label)
            body.append(text(right + 10, y(values[-1]) + 4, value_fmt(values[-1]), 12.5, INK, "start", "bold"))
    body.append(text(20, 378, takeaway, 13, INK, weight="bold"))
    body.append(text(20, 398, source, 12, MUTED))
    desc = "; ".join(f"{label}: " + ", ".join(f"AY {r['assessment_year']} {value_fmt(float(r[key]))}" for r in rows)
                     for label, key, _, value_fmt in series)
    (OUT / f"{name}.svg").write_text(svg(720, 410, title, desc, body), encoding="utf-8")
    print(f"wrote research/charts/{name}.svg")


def main() -> None:
    rows = load()
    first, last = rows[0], rows[-1]
    src = "Source: CBDT Income Tax Return Statistics (individuals)."
    crore = lambda v: f"{v / 1e7:.2f} cr"

    line_chart("ts-filers", "More people file, and more of them earn a salary",
               "Individual income tax returns per year, in crore", rows,
               [("All individual returns", "individual_returns", TEAL, crore),
                ("Returns reporting a salary", "salaried_filers", ORANGE, crore)],
               8e7, 2e7, lambda v: f"{v / 1e7:.0f}",
               f"Returns rose {int(last['individual_returns']) / int(first['individual_returns']):.1f}×; "
               f"salaried returns {int(last['salaried_filers']) / int(first['salaried_filers']):.1f}×.",
               src + " Table 2.2 (salary), 2.11 (total).")

    line_chart("ts-no-tax", "Most people who file pay no income tax",
               "Share of individual returns with no tax payable", rows,
               [("No tax payable", "no_tax_payable_pct", TEAL, lambda v: f"{v:.1f}%")],
               80, 20, lambda v: f"{v:.0f}%",
               f"The share fell to {min(float(r['no_tax_payable_pct']) for r in rows):.0f}%, then jumped to "
               f"{float(rows[8]['no_tax_payable_pct']):.0f}% in AY {rows[8]['assessment_year']} and has stayed above 60%.",
               src + " Table 2.11.",
               mark=(rows[8]["assessment_year"], "jump in AY 2020-21"))

    line_chart("ts-concentration", "Half of all individual income tax now comes from 1.4% of returns",
               "Share of all individual tax payable that came from returns with tax of ₹10 lakh or more", rows,
               [("Share of tax from returns paying ₹10 lakh or more", "tax_share_tax_10l_plus_pct", TEAL,
                 lambda v: f"{v:.1f}%")],
               60, 20, lambda v: f"{v:.0f}%",
               f"Those returns were {first['returns_tax_10l_plus_pct']}% of all returns in AY {first['assessment_year']} "
               f"and {last['returns_tax_10l_plus_pct']}% in AY {last['assessment_year']}.",
               src + " Table 2.11. The ₹10 lakh line is not inflation-adjusted.")

    line_chart("ts-top1", "The top-1% salary line, with and without inflation",
               "Salary at which the top 1% of salaried filers begins, ₹ lakh (estimate within reported ranges)", rows,
               [("In rupees of the time", "top1_salary_lakh", ORANGE, lambda v: f"₹{v:.0f}L"),
                (f"In {last['income_year']} rupees", "top1_salary_real_lakh", TEAL, lambda v: f"₹{v:.0f}L")],
               80, 20, lambda v: f"{v:.0f}",
               f"Before inflation: ₹{float(first['top1_salary_lakh']):.0f} → ₹{float(last['top1_salary_lakh']):.0f} lakh. "
               f"After inflation: below its AY {first['assessment_year']} level (₹{float(first['top1_salary_real_lakh']):.0f} lakh).",
               src + " Table 2.2; World Bank CPI (India).")


if __name__ == "__main__":
    main()
