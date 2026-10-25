"""Charts for Article 11, as inline SVG for the website.

Every value is computed here: tax shares from the CBDT table CSVs (run
cbdt_tables.py first), take-home pay and Budget 2025 relief from the slab rules.
Writes research/charts/a11-*.svg.

Colours: the site's teal as a one-hue ordinal ramp, checked with the dataviz
validator (monotone lightness, clear steps, light end >= 2:1 on white); text is
ink on the two light steps and white on the two dark ones (all >= 4.5:1).

Usage:
    python3 -I research/scripts/charts_article11.py
"""

from __future__ import annotations

import csv
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "charts"
LAKH = 100_000

INK, MUTED, GRID, SURFACE = "#12232E", "#56656F", "#DCE3E7", "#FFFFFF"
RAMP = ["#7DBFB9", "#3A9893", "#0E7570", "#073F40"]  # light -> dark
ON_RAMP = [INK, INK, SURFACE, SURFACE]
LINE, BAND = "#0E7570", "#FBE9C8"
FONT = "font-family:inherit,system-ui,sans-serif"

# --- tax rules -------------------------------------------------------------------
NEW_2025 = [(4, 0), (8, .05), (12, .10), (16, .15), (20, .20), (24, .25), (None, .30)]
NEW_2024 = [(3, 0), (7, .05), (10, .10), (12, .15), (15, .20), (None, .30)]


def slab_tax(income: float, slabs) -> float:
    tax, lower = 0.0, 0
    for upper, rate in slabs:
        top = income if upper is None else min(income, upper * LAKH)
        if top > lower:
            tax += (top - lower) * rate
        if upper is None or income <= upper * LAKH:
            break
        lower = upper * LAKH
    return tax


def tax_2025(taxable: float) -> float:
    """New regime, FY 2025-26 onward: rebate to Rs 12 lakh, marginal relief, 4% cess."""
    tax = slab_tax(taxable, NEW_2025)
    if taxable <= 12 * LAKH:
        return 0.0
    return min(tax, taxable - 12 * LAKH) * 1.04


def tax_2024(taxable: float) -> float:
    """New regime, FY 2024-25: rebate to Rs 7 lakh (before cess, for the relief table)."""
    return 0.0 if taxable <= 7 * LAKH else slab_tax(taxable, NEW_2024)


def fmt_inr(value: float) -> str:
    s = f"{round(value):d}"
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    return ",".join(([head] if head else []) + parts + [tail]) if head or parts else tail


# --- svg helpers -----------------------------------------------------------------
def svg(width: int, height: int, title: str, desc: str, body: list[str]) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" '
            f'role="img" aria-labelledby="t d" style="max-width:{width}px;height:auto;{FONT}">'
            f'<title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>'
            f'<rect width="{width}" height="{height}" fill="{SURFACE}"/>' + "".join(body) + "</svg>\n")


def text(x, y, s, size=13, fill=INK, anchor="start", weight="normal") -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
            f'font-weight="{weight}">{escape(s)}</text>')


# --- chart 1: who pays -----------------------------------------------------------------
def who_pays() -> str:
    with (ROOT / "data" / "cbdt-ay2023-24-individual-tax-payable.csv").open(encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f)]
    total_n = sum(int(r["returns"]) for r in rows)
    total_tax = sum(float(r["sum_crore"] or 0) for r in rows)
    groups = ["No tax", "Tax up to ₹1.5 lakh", "₹1.5–10 lakh", "₹10 lakh or more"]
    n = [0, 0, 0, 0]
    t = [0.0, 0.0, 0.0, 0.0]
    for r in rows:
        upper = int(r["upper_inr"]) if r["upper_inr"] else None
        lower = int(r["lower_inr"]) if r["lower_inr"] else None
        if upper == 0:
            g = 0
        elif upper is not None and upper <= int(1.5 * LAKH):
            g = 1
        elif upper is not None and upper <= 10 * LAKH:
            g = 2
        else:
            g = 3
        assert g != 3 or (lower is not None and lower >= 10 * LAKH)
        n[g] += int(r["returns"])
        t[g] += float(r["sum_crore"] or 0)
    share_n = [100 * x / total_n for x in n]
    share_t = [100 * x / total_tax for x in t]

    width, height, left, right = 720, 300, 150, 700
    plot = right - left
    body = [text(20, 30, "Who pays individual income tax", 17, weight="bold"),
            text(20, 52, "Tax-payable groups, share of all individual returns and of all tax payable, AY 2023-24",
                 13, MUTED)]
    # legend
    x = 20
    for i, label in enumerate(groups):
        fill = RAMP[i]
        body.append(f'<rect x="{x}" y="70" width="14" height="14" rx="3" fill="{fill}"/>')
        body.append(text(x + 20, 82, label, 13))
        x += 20 + 7.3 * len(label) + 28
    bars = [("Share of returns", share_n, n, "returns", 110), ("Share of tax paid", share_t, t, "crore", 200)]
    edges = {}
    for label, shares, raw, unit, y in bars:
        body.append(text(left - 12, y + 27, label, 13, INK, "end", "bold"))
        cursor = left
        for i, s in enumerate(shares):
            w = plot * s / 100
            if w <= 0:
                edges[(label, i)] = (cursor, cursor)
                continue
            gap = 2 if i < 3 else 0
            detail = (f"{fmt_inr(raw[i])} returns" if unit == "returns" else f"₹{fmt_inr(raw[i])} crore")
            body.append(f'<rect x="{cursor:.1f}" y="{y}" width="{max(w - gap, 1):.1f}" height="40" '
                        f'rx="{4 if i in (0, 3) else 0}" fill="{RAMP[i]}"><title>{escape(groups[i])}: '
                        f'{s:.1f}% ({detail})</title></rect>')
            if w > 46:
                body.append(text(cursor + w / 2, y + 26, f"{s:.1f}%", 14, ON_RAMP[i], "middle", "bold"))
            edges[(label, i)] = (cursor, cursor + w)
            cursor += w
    # ribbon: the top group in both bars
    a0, a1 = edges[("Share of returns", 3)]
    b0, b1 = edges[("Share of tax paid", 3)]
    body.insert(3, f'<polygon points="{a0:.1f},150 {a1:.1f},150 {b1:.1f},200 {b0:.1f},200" '
                   f'fill="{RAMP[3]}" fill-opacity="0.14"/>')
    body.append(text(right, 172, f"{share_n[3]:.1f}% of returns", 13, INK, "end", "bold"))
    body.append(text(20, 268, f"{share_n[3]:.1f}% of individual returns paid half of all individual income tax. "
                              f"{share_n[0]:.1f}% paid none.", 14, INK, weight="bold"))
    body.append(text(20, 288, "Source: CBDT, Income Tax Return Statistics AY 2023-24, table 2.11 (income of 2022-23).",
                     12, MUTED))
    return svg(width, height, "Who pays individual income tax, AY 2023-24",
               f"{share_n[3]:.1f}% of individual returns, those with tax payable of ₹10 lakh or more, paid "
               f"{share_t[3]:.1f}% of all individual income tax. {share_n[0]:.1f}% of returns had no tax payable.",
               body)


# --- chart 2: the cliff ----------------------------------------------------------------
def cliff() -> str:
    lo_x, hi_x = 12.0 * LAKH, 15.0 * LAKH
    lo_y, hi_y = 12.4 * LAKH, 14.2 * LAKH
    left, right, top, bottom = 90, 690, 96, 340

    def px(v):
        return left + (v - lo_x) / (hi_x - lo_x) * (right - left)

    def py(v):
        return bottom - (v - lo_y) / (hi_y - lo_y) * (bottom - top)

    # take-home along the line; find the trap band (take-home below its value at Rs 12.75 lakh)
    salaries = [lo_x + step * 100 for step in range(int((hi_x - lo_x) / 100) + 1)]
    home = [(s, s - tax_2025(s - 75_000)) for s in salaries]
    base = dict(home)[12.75 * LAKH]
    trap_end = max(s for s, h in home if s > 12.75 * LAKH and h <= base)
    low_point = min((h, s) for s, h in home if s > 12.75 * LAKH)

    body = [text(20, 30, "The cliff after ₹12.75 lakh", 17, weight="bold"),
            text(20, 52, "Take-home pay after income tax, salaried person, new regime (FY 2025-26 rules)", 13, MUTED)]
    body.append(f'<rect x="{px(12.75 * LAKH):.1f}" y="{top}" width="{px(trap_end) - px(12.75 * LAKH):.1f}" '
                f'height="{bottom - top}" fill="{BAND}"/>')
    body.append(text((px(12.75 * LAKH) + px(trap_end)) / 2, top - 8, "A raise here lowers take-home pay",
                     12, INK, "middle", "bold"))
    for v in range(124, 143, 4):
        y = py(v * LAKH / 10)
        body.append(f'<line x1="{left}" x2="{right}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>')
        body.append(text(left - 8, y + 4, f"₹{v / 10:.1f}L", 12, MUTED, "end"))
    for v in range(120, 151, 5):
        x = px(v * LAKH / 10)
        body.append(text(x, bottom + 20, f"₹{v / 10:.1f}L", 12, MUTED, "middle"))
    body.append(text((left + right) / 2, bottom + 40, "Gross salary", 12, MUTED, "middle"))
    # reference: pay before tax, clipped to the plot (salary = take-home where there is no tax)
    body.append(f'<line x1="{px(lo_y):.1f}" y1="{py(lo_y):.1f}" x2="{px(hi_y):.1f}" y2="{py(hi_y):.1f}" '
                f'stroke="{MUTED}" stroke-width="1.5" stroke-dasharray="5 4"/>')
    body.append(text(px(14.1 * LAKH) - 8, py(14.1 * LAKH) + 4, "Salary before tax", 12, MUTED, "end"))
    shown = [(s, h) for s, h in home if lo_y <= h <= hi_y]
    path = "M" + " L".join(f"{px(s):.1f},{py(h):.1f}" for s, h in shown)
    body.append(f'<path d="{path}" fill="none" stroke="{LINE}" stroke-width="2.5" stroke-linejoin="round"/>')
    body.append(text(px(14.95 * LAKH), py(dict(home)[14.95 * LAKH]) - 12, "Take-home pay", 13, LINE, "end", "bold"))
    for s, label, dy in [(12.75 * LAKH, f"₹{fmt_inr(base)} at ₹12.75L", -14),
                         (low_point[1], f"₹{fmt_inr(low_point[0])} at ₹{low_point[1] / LAKH:.2f}L", 22)]:
        h = dict(home)[s]
        body.append(f'<circle cx="{px(s):.1f}" cy="{py(h):.1f}" r="5" fill="{LINE}" stroke="{SURFACE}" '
                    f'stroke-width="2"><title>Salary ₹{fmt_inr(s)}: take-home ₹{fmt_inr(h)}, '
                    f'tax ₹{fmt_inr(s - h)}</title></circle>')
        body.append(text(px(s) + 8, py(h) + dy, label, 12, INK, "start", "bold"))
    body.append(text(20, 400, f"Each extra rupee up to ₹{low_point[1] / LAKH:.2f} lakh costs ₹1.04 in tax; "
                              f"take-home recovers at ₹{trap_end / LAKH:.2f} lakh.", 13, INK, weight="bold"))
    body.append(text(20, 420, "Our calculation from Income Tax Department slabs, rebate and 4% cess; ₹75,000 standard "
                              "deduction.", 12, MUTED))
    return svg(720, 432, "Take-home pay just above ₹12.75 lakh",
               f"Take-home pay is ₹{fmt_inr(base)} at a salary of ₹12.75 lakh, then falls to ₹{fmt_inr(low_point[0])} "
               f"at ₹{low_point[1] / LAKH:.2f} lakh, and only rises above ₹12.75 lakh again after about "
               f"₹{trap_end / LAKH:.2f} lakh.", body)


# --- chart 3: relief by income ---------------------------------------------------------
def relief() -> str:
    incomes = [12, 16, 20, 25, 50]
    data = []
    for inc in incomes:
        before, after = tax_2024(inc * LAKH), slab_tax(inc * LAKH, NEW_2025) if inc > 12 else 0.0
        data.append((inc, before, after, before - after, 100 * (before - after) / before))
    left, right, top, bottom = 60, 700, 80, 300
    slot = (right - left) / len(data)
    body = [text(20, 30, "Who gained most from Budget 2025", 17, weight="bold"),
            text(20, 52, "Cut in income tax as a share of the tax paid before, by taxable income (new regime)", 13, MUTED)]
    for pct in (0, 25, 50, 75, 100):
        y = bottom - pct / 100 * (bottom - top)
        body.append(f'<line x1="{left}" x2="{right}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRID}"/>')
        body.append(text(left - 8, y + 4, f"{pct}%", 12, MUTED, "end"))
    for i, (inc, before, after, saving, pct) in enumerate(data):
        x = left + i * slot + slot * 0.25
        w = slot * 0.5
        y = bottom - pct / 100 * (bottom - top)
        body.append(f'<path d="M{x:.1f},{bottom} V{y + 4:.1f} Q{x:.1f},{y:.1f} {x + 4:.1f},{y:.1f} H{x + w - 4:.1f} '
                    f'Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + 4:.1f} V{bottom} Z" fill="{LINE}">'
                    f'<title>₹{inc} lakh: tax ₹{fmt_inr(before)} before, ₹{fmt_inr(after)} after; saves '
                    f'₹{fmt_inr(saving)} ({pct:.0f}%)</title></path>')
        body.append(text(x + w / 2, y - 8, f"{pct:.0f}%", 14, INK, "middle", "bold"))
        body.append(text(x + w / 2, bottom + 20, f"₹{inc} lakh", 13, INK, "middle", "bold"))
        body.append(text(x + w / 2, bottom + 38, f"saves ₹{fmt_inr(saving)}", 12, MUTED, "middle"))
    body.append(text(20, 368, "The rupee saving grows to ₹1.1 lakh, but as a share of the tax paid it shrinks from 100% "
                              "to 9%.", 13, INK, weight="bold"))
    body.append(text(20, 388, "Our calculation from the FY 2024-25 and FY 2025-26 new-regime slabs and rebates; excludes "
                              "4% cess.", 12, MUTED))
    return svg(720, 400, "Budget 2025 tax cut as a share of tax paid, by taxable income",
               "; ".join(f"₹{inc} lakh: {pct:.0f}% (₹{fmt_inr(saving)})" for inc, _, _, saving, pct in data) + ".",
               body)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for name, chart in [("a11-who-pays", who_pays), ("a11-cliff", cliff), ("a11-relief", relief)]:
        (OUT / f"{name}.svg").write_text(chart(), encoding="utf-8")
        print(f"wrote research/charts/{name}.svg")


if __name__ == "__main__":
    main()
