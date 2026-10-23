"""Test helpers. All rows built here are synthetic test fixtures, never published data."""

from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path

import pytest

from itv_aggregator.ingest import Response
from itv_aggregator.schema import NOT_ANSWERED, load_schema

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "survey" / "questionnaire-v1.json"
SCHEMA = load_schema(SCHEMA_PATH)


@pytest.fixture(scope="session")
def schema():
    return SCHEMA


def make_export(schema, rows: list[dict], extra_columns: tuple[str, ...] = ("COMMENTS",)) -> str:
    """Build a LimeSurvey-style CSV export (code headings, short answers).

    Row keys: id, submitdate, consent, any single-choice code (e.g. STATE,
    INCOME), any multi-choice code mapped to a list (e.g. CONCERN), and extra
    columns such as COMMENTS. Lower-case state/industry/concerns are accepted
    as shorthands.
    """
    header = ["id", "submitdate", "lastpage", "startlanguage", "seed", schema.consent_code]
    header += [q.code for q in schema.singles if q.code not in extra_columns]
    header += [q.column(o) for q in schema.multis for o in q.options]
    header += list(extra_columns)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    for i, row in enumerate(rows, start=1):
        row = dict(row)
        row.setdefault("STATE", row.pop("state", "MH"))
        row.setdefault("INDUSTRY", row.pop("industry", "ITSW"))
        row.setdefault("CONCERN", row.pop("concerns", ["COSTLIV"]))
        out = {h: "" for h in header}
        out.update({
            "id": str(row.get("id", i)),
            "submitdate": row.get("submitdate", "2026-11-02 10:15:00"),
            "lastpage": "4", "startlanguage": "en", "seed": "12345",
            schema.consent_code: row.get("consent", "Y"),
        })
        for q in schema.singles:
            if q.code in row:
                out[q.code] = row[q.code]
        for q in schema.multis:
            for o in row.get(q.code, ()):
                out[q.column(o)] = "Y"
        for col in extra_columns:
            out[col] = row.get(col, "")
        writer.writerow(out)
    return buf.getvalue()


def many(n: int, **row) -> list[dict]:
    return [dict(row) for _ in range(n)]


def resp(i, state="MH", industry="ITSW", concerns=("COSTLIV",), d=date(2026, 11, 4), **answers) -> Response:
    """A validated response, as ingest would produce it."""
    full = {q.code: NOT_ANSWERED for q in SCHEMA.singles if not q.required}
    full.update(answers, STATE=state, INDUSTRY=industry)
    selections = {q.code: frozenset() for q in SCHEMA.multis}
    selections["CONCERN"] = frozenset(concerns)
    return Response(str(i), d, full, selections)
