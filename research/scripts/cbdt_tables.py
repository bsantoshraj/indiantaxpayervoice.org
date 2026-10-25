"""Extract range tables from a CBDT "Income Tax Return Statistics" PDF into CSV.

Each table lists, per income (or tax) range, the number of returns, the sum in
crore and the average in lakh.  Every table is checked against its own printed
total before it is written, so a parsing slip cannot pass silently.

Needs pdftotext (poppler-utils).

Usage:
    python3 -I research/scripts/cbdt_tables.py research/sources/a11-cbdt-itr-stats-ay2023-24.pdf
"""

from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# Table number -> output name (layout of the AY 2022-23 and 2023-24 reports)
TABLES = {
    "1.10": "all-taxpayers-returned-income",
    "2.1": "individual-gross-total-income",
    "2.2": "individual-salary-income",
    "2.3": "individual-house-property-income",
    "2.10": "individual-returned-income",
    "2.11": "individual-tax-payable",
}

ROW = re.compile(r"^\s*(?P<label>(?:<|=|>).*?)\s{2,}(?P<n>[\d,]+|-)\s+(?P<sum>-\s?[\d,.]+|[\d,.]+|-)\s+(?P<avg>-\s?[\d,.]+|[\d,.]+|-)\s*$")
EMPTY_ROW = re.compile(r"^\s*(?P<label><0|=0)\s+(?P<n>[\d,]+|-)(\s+-)*\s*$")
TOTAL = re.compile(r"^\s*Total\s+(?P<n>[\d,]+)\s+(?P<sum>[\d,.]+)\s*$")


def number(text: str) -> float | None:
    """'1,23,456.78' -> 123456.78; '-64,071.91' (a loss) -> -64071.91; '-' (none) -> None."""
    # AY 2018-19 prints losses with a space after the sign: '- 48,255'.
    return None if text == "-" else float(text.replace(",", "").replace(" ", ""))


def bounds(label: str) -> tuple[int | None, int | None]:
    """'>5,00,000 and <= 5,50,000' -> (500000, 550000); '=0' -> (0, 0); '<0' -> (None, 0)."""
    values = [int(v.replace(",", "")) for v in re.findall(r"[\d,]+", label)]
    if label.startswith("<"):
        return None, 0
    if label.startswith("="):
        return 0, 0
    return values[0], (values[1] if len(values) > 1 else None)


def parse(text: str, number_: str) -> tuple[str, list[dict]]:
    lines = text.splitlines()
    title_re = re.compile(rf"^\s*{re.escape(number_)}\s+(?P<title>\S.*\(AY [\d-]+\))\s*$")
    for i, line in enumerate(lines):
        match = title_re.match(line)
        if match and "...." not in line:  # skip the table of contents
            break
    else:
        raise ValueError(f"table {number_} not found")
    title, rows = match["title"].strip(), []
    for line in lines[i + 1:]:
        if total := TOTAL.match(line):
            count = sum(r["returns"] or 0 for r in rows)
            amount = sum(r["sum_crore"] or 0 for r in rows)
            printed_n, printed_sum = number(total["n"]), number(total["sum"])
            # Older reports (AY 2012-13 to 2018-19) print amounts in whole crore, so the
            # rounded rows can drift from the printed total by up to half a crore each.
            # Counts are never rounded and must match exactly.
            whole = "." not in total["sum"]
            slack = 0.5 * sum(1 for r in rows if r["sum_crore"]) if whole else 1
            if count != printed_n or abs(amount - printed_sum) > slack:
                raise ValueError(f"{number_}: rows give {count:,} / {amount:,.2f}, "
                                 f"printed total {printed_n:,.0f} / {printed_sum:,.2f}")
            # Older reports wrap one label (">100,00,00,000 and" / "<=500,00,00,000"):
            # its upper bound is the next row's lower bound.
            for r, nxt in zip(rows, rows[1:]):
                if r["range"].endswith(" and") and r["upper_inr"] is None:
                    r["upper_inr"] = nxt["lower_inr"]
                    r["range"] += f" <={nxt['lower_inr']:,}"
            return title, rows
        row = ROW.match(line) or EMPTY_ROW.match(line)
        if row:
            lo, hi = bounds(row["label"].strip())
            fields = row.groupdict()
            rows.append({
                "range": " ".join(row["label"].split()),
                "lower_inr": lo,
                "upper_inr": hi,
                "returns": int(number(fields["n"]) or 0),
                "sum_crore": number(fields.get("sum") or "-"),
                "average_lakh": number(fields.get("avg") or "-"),
            })
    raise ValueError(f"{number_}: no Total row")


def main(pdf: str) -> None:
    text = subprocess.run(["pdftotext", "-layout", pdf, "-"], check=True,
                          capture_output=True, text=True).stdout
    year = re.search(r"Assessment Year (\d{4}-\d{2})", text)[1]
    DATA.mkdir(exist_ok=True)
    for number_, name in TABLES.items():
        title, rows = parse(text, number_)
        out = DATA / f"cbdt-ay{year}-{name}.csv"
        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"{number_:5} {title}: {len(rows)} rows, totals match -> {out.name}")


if __name__ == "__main__":
    main(sys.argv[1])
