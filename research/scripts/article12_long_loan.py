"""Article 12, second worked example: a long home loan taken before the 2017 cap.

A let-out flat bought with a 30-year loan in April 2016 at 8.5% fixed, EMI Rs 1.5
lakh a month; rent Rs 25,000 a month; owner in the 30% slab (old regime) plus 4%
cess, no surcharge. House-property loss = interest - (rent - 30% standard
deduction). Before AY 2018-19 the whole loss was set off against other income;
from FY 2017-18 at most Rs 2 lakh, the rest carried forward (8 years, against
house-property income only, which this flat never has).

Writes data/a12-long-loan.csv and prints a Markdown table. Illustration, not tax advice.

Usage:
    python3 -I research/scripts/article12_long_loan.py
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EMI, RATE, YEARS = 150_000, 0.085, 30
RENT = 25_000 * 12
CAP, TAX = 200_000, 0.30 * 1.04


def rows() -> list[dict]:
    r = RATE / 12
    balance = EMI * (1 - (1 + r) ** -(YEARS * 12)) / r
    out = []
    for year in range(2016, 2026):
        interest = 0.0
        for _ in range(12):
            i = balance * r
            interest += i
            balance -= EMI - i
        loss = interest - RENT * 0.70
        allowed = loss if year < 2017 else min(loss, CAP)
        out.append({
            "financial_year": f"{year}-{str(year + 1)[2:]}",
            "interest": round(interest),
            "loss": round(loss),
            "set_off": round(allowed),
            "carried_forward": round(loss - allowed),
            "relief_old_rules": round(loss * TAX),
            "relief_now": round(allowed * TAX),
            "extra_tax": round((loss - allowed) * TAX),
        })
    return out


def main() -> None:
    data = rows()
    with (ROOT / "data" / "a12-long-loan.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]))
        w.writeheader()
        w.writerows(data)
    lakh = lambda v: f"₹{v / 100_000:.2f}L"
    print("| Year | Interest | Loss | Set off against salary | Carried forward | Extra tax vs old rules |")
    print("|---|---|---|---|---|---|")
    for d in data:
        print(f"| {d['financial_year']} | {lakh(d['interest'])} | {lakh(d['loss'])} | {lakh(d['set_off'])} | "
              f"{lakh(d['carried_forward'])} | {lakh(d['extra_tax'])} |")
    capped = data[1:]
    r = RATE / 12
    print(f"\nLoan {lakh(EMI * (1 - (1 + r) ** -(YEARS * 12)) / r)}; FY 2017-18 to {data[-1]['financial_year']}: "
          f"carried forward {lakh(sum(d['carried_forward'] for d in capped))}, extra tax "
          f"{lakh(sum(d['extra_tax'] for d in capped))}, relief now {lakh(capped[0]['relief_now'])} a year")


if __name__ == "__main__":
    main()
