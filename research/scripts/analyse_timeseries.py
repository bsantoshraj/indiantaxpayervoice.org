"""Twelve years of CBDT return statistics (AY 2012-13 to AY 2023-24), one row a year.

Reads the CSVs written by cbdt_tables.py for every assessment year present and the
World Bank CPI for India, and writes:
  data/timeseries.csv            every figure, per assessment year
  data/timeseries-summary.md     the same as a table, with definitions

Definitions
- Assessment year (AY) Y-(Y+1) covers income earned in financial year (Y-1)-Y,
  e.g. AY 2023-24 is income of April 2022 - March 2023.
- Individual returns: all returns filed by individuals (CBDT table 2.11 total).
- No tax payable: returns whose tax payable is zero (table 2.11).
- Top tax group: returns with tax payable of Rs 10 lakh or more (table 2.11).
- Salaried filers: individual returns with salary income above zero (table 2.2).
- Top-1% / top-10% salary: the salary at which that share of salaried filers
  begins, assuming filers are spread evenly within the reported range (estimate).
- Real values: nominal rupees deflated with the World Bank CPI for India
  (FP.CPI.TOTL, calendar years). A financial year April Y - March Y+1 takes
  0.75 x CPI(Y) + 0.25 x CPI(Y+1). Expressed in rupees of the latest income year.

Usage:
    python3 -I research/scripts/analyse_timeseries.py
"""

from __future__ import annotations

import csv
import glob
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LAKH, CRORE = 100_000, 10_000_000


def load(year: str, table: str) -> list[dict]:
    with (DATA / f"cbdt-ay{year}-{table}.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["lower"] = int(r["lower_inr"]) if r["lower_inr"] else None
        r["upper"] = int(r["upper_inr"]) if r["upper_inr"] else None
        r["n"] = int(r["returns"])
        r["sum"] = float(r["sum_crore"]) if r["sum_crore"] else 0.0
    return rows


def positive(rows):
    return [r for r in rows if r["upper"] is None or r["upper"] > 0]


def at_least(rows, cut):
    return [r for r in positive(rows) if r["lower"] >= cut]


def threshold(rows, share):
    rows = positive(rows)
    need = share * sum(r["n"] for r in rows)
    above = 0
    for r in sorted(rows, key=lambda r: r["lower"], reverse=True):
        if above + r["n"] >= need:
            if r["upper"] is None:
                return float(r["lower"])
            return r["upper"] - (need - above) / r["n"] * (r["upper"] - r["lower"])
        above += r["n"]
    raise ValueError(share)


def cpi_by_year() -> dict[int, float]:
    data = json.loads((ROOT / "sources/a13-worldbank-cpi-india.json").read_text(encoding="utf-8"))
    return {int(r["date"]): r["value"] for r in data[1] if r["value"] is not None}


def main() -> None:
    years = sorted(re.search(r"ay(\d{4}-\d{2})-individual-tax-payable", f)[1]
                   for f in glob.glob(str(DATA / "cbdt-ay*-individual-tax-payable.csv")))
    cpi = cpi_by_year()

    def fy_cpi(ay: str) -> float:
        start = int(ay[:4]) - 1          # AY 2023-24 -> income year starting April 2022
        return 0.75 * cpi[start] + 0.25 * cpi[start + 1]

    base_ay = years[-1]
    out = []
    for ay in years:
        tax, salary = load(ay, "individual-tax-payable"), load(ay, "individual-salary-income")
        total = sum(r["n"] for r in tax)
        zero = total - sum(r["n"] for r in positive(tax))
        tax_total = sum(r["sum"] for r in positive(tax))
        top_tax = at_least(tax, 10 * LAKH)
        paid = positive(salary)
        salaried = sum(r["n"] for r in paid)
        deflate = fy_cpi(base_ay) / fy_cpi(ay)
        top1, top10 = threshold(salary, 0.01), threshold(salary, 0.10)
        out.append({
            "assessment_year": ay,
            "income_year": f"{int(ay[:4]) - 1}-{ay[2:4]}",
            "individual_returns": total,
            "no_tax_payable": zero,
            "no_tax_payable_pct": round(100 * zero / total, 2),
            "tax_payable_crore": round(tax_total),
            "returns_tax_10l_plus": sum(r["n"] for r in top_tax),
            "returns_tax_10l_plus_pct": round(100 * sum(r["n"] for r in top_tax) / total, 2),
            "tax_share_tax_10l_plus_pct": round(100 * sum(r["sum"] for r in top_tax) / tax_total, 1),
            "salaried_filers": salaried,
            "salaried_10l_plus": sum(r["n"] for r in at_least(salary, 10 * LAKH)),
            "salaried_25l_plus": sum(r["n"] for r in at_least(salary, 25 * LAKH)),
            "salaried_50l_plus": sum(r["n"] for r in at_least(salary, 50 * LAKH)),
            "salaried_1cr_plus": sum(r["n"] for r in at_least(salary, CRORE)),
            "top10_salary_lakh": round(top10 / LAKH, 1),
            "top1_salary_lakh": round(top1 / LAKH, 1),
            "top10_salary_real_lakh": round(top10 * deflate / LAKH, 1),
            "top1_salary_real_lakh": round(top1 * deflate / LAKH, 1),
            "cpi_factor_to_latest": round(deflate, 3),
        })

    with (DATA / "timeseries.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)

    first, last = out[0], out[-1]
    lines = [f"# Individual income tax returns, AY {first['assessment_year']} to AY {last['assessment_year']}", "",
             "Source: CBDT *Income Tax Return Statistics*, one report per assessment year (tables 2.2 and 2.11), "
             "and World Bank CPI for India. Generated by `scripts/analyse_timeseries.py`; definitions are in "
             "its docstring. Do not edit by hand.", "",
             "| AY | Individual returns | No tax payable | Tax ≥ ₹10 lakh: returns | Their share of tax | "
             "Salaried filers | Salary ≥ ₹50 lakh | Top 1% salary from | Same, in "
             f"{last['income_year']} rupees |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in out:
        lines.append(f"| {r['assessment_year']} | {r['individual_returns']:,} | {r['no_tax_payable_pct']}% | "
                     f"{r['returns_tax_10l_plus']:,} ({r['returns_tax_10l_plus_pct']}%) | "
                     f"{r['tax_share_tax_10l_plus_pct']}% | {r['salaried_filers']:,} | {r['salaried_50l_plus']:,} | "
                     f"₹{r['top1_salary_lakh']} lakh | ₹{r['top1_salary_real_lakh']} lakh |")
    grow = lambda k: last[k] / first[k]
    lines += ["",
              f"Over the period: individual returns ×{grow('individual_returns'):.2f}; salaried filers "
              f"×{grow('salaried_filers'):.2f}; salaried filers at ₹50 lakh or more ×{grow('salaried_50l_plus'):.1f} "
              f"(nominal ranges); prices ×{first['cpi_factor_to_latest']:.2f} (CPI)."]
    (DATA / "timeseries-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
