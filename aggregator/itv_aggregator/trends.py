"""Weekly trends from the change in the published total between releases.

Responses carry no dates (the survey is anonymised), so trends never come from
response times. Instead every release records that day's *published* total,
which is already rounded and therefore reveals nothing new, and the trend is the
change in that total from week to week.

* One snapshot per UTC day; a later release the same day replaces it.
* A total that falls (for example, staging's survey was rebuilt) starts a new
  series; only the current series is published, so there are no negative weeks.
* Weekly new responses below ``min_cohort`` are published as "suppressed" so a
  quiet week cannot point at a few people. The first week of a series counts
  everything up to that point and is flagged as such.

The history lives outside the published release (``<out>/history``).
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path

from .aggregate import NONE, PUBLISHED, SUPPRESSED

HISTORY_FILE = Path("history") / "totals.json"
KEEP_DAYS = 800  # a little over two years: the survey-response retention period


def load_history(out_dir: Path) -> list[dict]:
    try:
        data = json.loads((out_dir / HISTORY_FILE).read_text(encoding="utf-8"))
        return [e for e in data if isinstance(e, dict) and {"date", "total", "series"} <= e.keys()]
    except (OSError, ValueError):
        return []


def save_history(out_dir: Path, history: list[dict]) -> None:
    path = out_dir / HISTORY_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(history, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def record_total(history: list[dict], day: date, total: int) -> list[dict]:
    """Return history with today's published total recorded (one entry per day)."""
    entries = sorted((e for e in history if e["date"] != day.isoformat()), key=lambda e: e["date"])
    series = entries[-1]["series"] if entries else 1
    if entries and total < entries[-1]["total"]:
        series += 1  # the total fell: a new survey, so a new series
    entries.append({"date": day.isoformat(), "total": total, "series": series})
    return entries[-KEEP_DAYS:]


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def weekly_trend(history: list[dict], min_cohort: int) -> dict:
    current = [e for e in history if history and e["series"] == history[-1]["series"]]
    week_end: dict[date, int] = {}
    for e in sorted(current, key=lambda e: e["date"]):
        week_end[_week_start(date.fromisoformat(e["date"]))] = e["total"]  # last snapshot of the week

    weeks, previous = [], 0
    for i, (start, cumulative) in enumerate(sorted(week_end.items())):
        new = max(cumulative - previous, 0)
        previous = cumulative
        if new == 0:
            status, shown = NONE, 0
        elif new < min_cohort:
            status, shown = SUPPRESSED, None
        else:
            status, shown = PUBLISHED, new
        weeks.append({"week_start": start.isoformat(), "status": status, "new": shown,
                      "total": cumulative, "includes_earlier": i == 0})
    return {
        "granularity": "week",
        "basis": ("Weekly change in the published total of valid responses. Responses carry no "
                  "dates, so this is measured between scheduled updates, not from response times."),
        "weeks": weeks,
    }
