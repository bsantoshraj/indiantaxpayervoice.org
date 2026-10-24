"""Turn validated responses into public aggregates with small-cohort suppression.

Suppression model (see docs/phase-0-report.md, "Public statistics"):

* Primary: any non-zero cell below ``min_cohort`` is suppressed.
* Complementary: whenever a set of cells partitions a published total, extra
  cells are suppressed (smallest first) until the suppressed cells together
  hold at least ``min_cohort`` respondents, so a hidden cell cannot be
  recovered by subtracting the visible ones from the total.
* Zero cells are published as ``none`` so "no responses" stays distinct from
  "suppressed".
* Demographic questions are only ever published one at a time against the
  concern list, never crossed with state or with each other.

A minimum cell size reduces, but does not eliminate, re-identification risk.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Mapping

from .ingest import Response
from .schema import CONCERN, INDUSTRY, Question, Schema

PUBLISHED = "published"
SUPPRESSED = "suppressed"
NONE = "none"


@dataclass(frozen=True)
class Policy:
    min_cohort: int = 20


def protect_partition(
    counts: Mapping[str, int], min_cohort: int, forced: Iterable[str] = ()
) -> set[str]:
    """Return the keys to suppress in a partition of a published total."""
    suppressed = {k for k, v in counts.items() if 0 < v < min_cohort}
    suppressed |= {k for k in forced if counts.get(k, 0) > 0}
    if not suppressed:
        return suppressed
    candidates = sorted(
        (k for k, v in counts.items() if v > 0 and k not in suppressed),
        key=lambda k: (counts[k], k),
    )
    while sum(counts[k] for k in suppressed) < min_cohort and candidates:
        suppressed.add(candidates.pop(0))
    # A single hidden cell is always recoverable as total minus the rest.
    if len(suppressed) == 1 and candidates:
        suppressed.add(candidates.pop(0))
    return suppressed


def _cell(count: int, denominator: int, hidden: bool) -> dict:
    if count == 0:
        return {"status": NONE, "count": 0, "percent": 0.0}
    if hidden:
        return {"status": SUPPRESSED, "count": None, "percent": None}
    pct = round(100.0 * count / denominator, 1) if denominator else None
    return {"status": PUBLISHED, "count": count, "percent": pct}


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _multi_counts(responses: list[Response], q: Question, k: int) -> tuple[Counter, set[str]]:
    counts = Counter(o for r in responses for o in r.selections.get(q.code, ()))
    hidden = {o for o in q.options if 0 < counts.get(o, 0) < k}
    return counts, hidden


def _breakdown(
    responses: list[Response], q: Question, concerns: dict[str, str],
    hidden_concerns: set[str], k: int,
) -> dict:
    """One demographic question against the concern list, with row percentages."""
    groups = q.groups()
    counts = Counter(r.answers[q.code] for r in responses)
    full = {g: counts.get(g, 0) for g in groups}
    hidden_groups = protect_partition(full, k)

    # Each concern column partitions the national concern count across groups.
    cross = Counter((r.answers[q.code], c) for r in responses for c in r.concerns)
    hidden_cross: set[tuple[str, str]] = set()
    for c in concerns:
        column = {g: cross.get((g, c), 0) for g in groups}
        forced = set(hidden_groups) | (set(column) if c in hidden_concerns else set())
        hidden_cross |= {(g, c) for g in protect_partition(column, k, forced)}

    return {
        "question": q.code,
        "text": q.text,
        "denominator": len(responses),
        "groups": [
            {
                "code": g,
                "label": label,
                **_cell(full[g], len(responses), g in hidden_groups),
                "concerns": [
                    {"code": c, **_cell(cross.get((g, c), 0), full[g], (g, c) in hidden_cross)}
                    for c in concerns
                ],
            }
            for g, label in groups.items()
        ],
    }


def _distribution(responses: list[Response], q: Question, k: int) -> dict:
    total = len(responses)
    if q.type == "multi":
        counts, hidden = _multi_counts(responses, q, k)
        options = q.options
        note = f"Respondents could choose up to {q.max_answers}." if q.max_answers else "Respondents could choose several."
    else:
        options = q.groups()
        raw = Counter(r.answers[q.code] for r in responses)
        counts = Counter({o: raw.get(o, 0) for o in options})
        hidden = protect_partition(counts, k)
        note = None
    out = {
        "question": q.code,
        "text": q.text,
        "denominator": total,
        "options": [
            {"code": o, "label": label, **_cell(counts.get(o, 0), total, o in hidden)}
            for o, label in options.items()
        ],
    }
    if note:
        out["note"] = note
    return out


def aggregate(responses: list[Response], schema: Schema, policy: Policy) -> dict[str, dict]:
    k = policy.min_cohort
    total = len(responses)
    concern_q = schema.questions[CONCERN]
    concern_counts, hidden_concerns = _multi_counts(responses, concern_q, k)

    state_counts = Counter(r.state for r in responses)
    states_full = {s: state_counts.get(s, 0) for s in schema.states}
    hidden_states = protect_partition(states_full, k)
    industry_counts = Counter(r.industry for r in responses)

    summary = {
        "valid_responses": total,
        "states_represented": sum(1 for v in states_full.values() if v > 0),
        "states_total": len(schema.states),
        "industries_represented": sum(1 for i in schema.industries if industry_counts.get(i, 0) > 0),
        "concerns": [
            {"code": c, "label": label, **_cell(concern_counts.get(c, 0), total, c in hidden_concerns)}
            for c, label in schema.concerns.items()
        ],
        "notes": [
            "Respondents may choose more than one concern, so concern percentages can sum to more than 100%.",
            "Percentages use valid responses as the denominator.",
        ],
    }

    states = {
        "denominator": total,
        "states": [
            {"code": s, "name": name, **_cell(states_full[s], total, s in hidden_states)}
            for s, name in schema.states.items()
        ],
    }

    industries = _breakdown(responses, schema.questions[INDUSTRY], schema.concerns, hidden_concerns, k)
    breakdowns = {
        "notes": [
            "Each question is shown separately against the concern list; questions are never combined with each other or with state.",
            "Concern percentages are the share of that group's respondents.",
        ],
        "breakdowns": [
            _breakdown(responses, q, schema.concerns, hidden_concerns, k)
            for q in schema.by_role("breakdown") if q.code != INDUSTRY
        ],
    }
    distributions = {
        "questions": [
            _distribution(responses, q, k)
            for q in schema.questions.values()
            if q.role == "distribution" or (q.role == "measure" and q.code != CONCERN)
        ],
    }

    weekly = Counter(_week_start(r.submit_date) for r in responses if r.submit_date)
    trends = {
        "granularity": "week",
        "weeks": [{"week_start": w.isoformat(), "count": n} for w, n in sorted(weekly.items())],
        # Anonymised LimeSurvey surveys do not record dates; never invent them.
        "date_not_recorded": sum(1 for r in responses if r.submit_date is None),
    }

    return {
        "summary": summary, "states": states, "industries": industries,
        "breakdowns": breakdowns, "distributions": distributions, "trends": trends,
    }
