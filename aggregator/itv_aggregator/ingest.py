"""Parse and validate a LimeSurvey response export (CSV, code headings, short answers).

Only the columns needed for public aggregates are read. Free-text answers and
any other columns are never copied out of the export.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TextIO

from .schema import CONCERN, INDUSTRY, NOT_ANSWERED, STATE, Schema


class IngestError(Exception):
    """The export as a whole cannot be trusted; nothing should be published."""


@dataclass(frozen=True)
class Limits:
    max_rows: int = 2_000_000
    max_field_chars: int = 20_000


@dataclass(frozen=True)
class Response:
    response_id: str
    submit_date: date
    answers: dict[str, str] = field(hash=False)  # single-choice code -> option (or NA)
    selections: dict[str, frozenset[str]] = field(hash=False)  # multi-choice code -> options

    @property
    def state(self) -> str:
        return self.answers[STATE]

    @property
    def industry(self) -> str:
        return self.answers[INDUSTRY]

    @property
    def concerns(self) -> frozenset[str]:
        return self.selections.get(CONCERN, frozenset())


@dataclass
class IngestReport:
    """Internal counts for operators. Not published as-is."""

    rows_read: int = 0
    valid: int = 0
    incomplete: int = 0
    no_consent: int = 0
    invalid_state: int = 0
    invalid_industry: int = 0
    invalid_answer: int = 0
    invalid_date: int = 0
    duplicate_ids: int = 0
    conflicting_duplicates: int = 0


def _parse_submit_date(value: str) -> date | None:
    value = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def required_columns(schema: Schema) -> set[str]:
    cols = {"id", "submitdate", schema.consent_code}
    cols |= {q.code for q in schema.singles}
    cols |= {q.column(o) for q in schema.multis for o in q.options}
    return cols


def parse_export(
    stream: TextIO, schema: Schema, limits: Limits = Limits(), delimiter: str = ","
) -> tuple[list[Response], IngestReport]:
    csv.field_size_limit(limits.max_field_chars)
    reader = csv.DictReader(stream, delimiter=delimiter)
    if reader.fieldnames is None:
        # An empty export means no responses yet.
        return [], IngestReport()

    missing = required_columns(schema) - set(reader.fieldnames)
    if missing:
        raise IngestError(f"export is missing required columns: {sorted(missing)}")

    report = IngestReport()
    by_id: dict[str, Response] = {}
    try:
        for row in reader:
            report.rows_read += 1
            if report.rows_read > limits.max_rows:
                raise IngestError(f"export exceeds max_rows={limits.max_rows}")
            if None in row:
                raise IngestError(f"row {report.rows_read} has more fields than the header")
            resp = _validate_row(row, schema, report)
            if resp is None:
                continue
            existing = by_id.get(resp.response_id)
            if existing is not None:
                report.duplicate_ids += 1
                if existing != resp:
                    report.conflicting_duplicates += 1
                continue
            by_id[resp.response_id] = resp
    except csv.Error as exc:
        raise IngestError(f"malformed CSV near row {report.rows_read}: {exc}") from exc

    report.valid = len(by_id)
    return list(by_id.values()), report


def _validate_row(row: dict[str, str], schema: Schema, report: IngestReport) -> Response | None:
    rid = (row.get("id") or "").strip()
    if not rid or not (row.get("submitdate") or "").strip():
        report.incomplete += 1
        return None
    submit = _parse_submit_date(row["submitdate"])
    if submit is None:
        report.invalid_date += 1
        return None
    if (row.get(schema.consent_code) or "").strip() != "Y":
        report.no_consent += 1
        return None

    answers: dict[str, str] = {}
    for q in schema.singles:
        value = (row.get(q.code) or "").strip()
        if not value and not q.required:
            value = NOT_ANSWERED
        if value not in q.options and not (value == NOT_ANSWERED and not q.required):
            if q.code == STATE:
                report.invalid_state += 1
            elif q.code == INDUSTRY:
                report.invalid_industry += 1
            else:
                report.invalid_answer += 1
            return None
        answers[q.code] = value

    selections: dict[str, frozenset[str]] = {}
    for q in schema.multis:
        chosen = frozenset(o for o in q.options if (row.get(q.column(o)) or "").strip() == "Y")
        if (q.required and not chosen) or (q.max_answers and len(chosen) > q.max_answers):
            report.invalid_answer += 1
            return None
        selections[q.code] = chosen

    return Response(rid, submit, answers, selections)


def detect_delimiter(text: str) -> str:
    """LimeSurvey's CSV export uses ";" by default; files saved elsewhere may use ","."""
    header = text.split("\n", 1)[0]
    return ";" if header.count(";") > header.count(",") else ","


def parse_export_text(text: str, schema: Schema, **kwargs) -> tuple[list[Response], IngestReport]:
    text = text.lstrip("﻿")
    kwargs.setdefault("delimiter", detect_delimiter(text))
    return parse_export(io.StringIO(text), schema, **kwargs)
