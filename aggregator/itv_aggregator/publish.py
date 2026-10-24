"""Write aggregates as a static, versioned release and switch to it atomically.

Layout under ``out_dir``::

    releases/<release-id>/v1/statistics/{summary,states,industries,trends}.json
    releases/<release-id>/v1/statistics/states.csv
    current -> releases/<release-id>      (relative symlink, swapped atomically)

The web server serves ``current``; a failed run never touches it.
"""

from __future__ import annotations

import csv
import io
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

ENDPOINTS = ("summary", "states", "industries", "breakdowns", "distributions", "trends")
CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
KEEP_RELEASES = 10


class PublishRefused(Exception):
    pass


def sanitize_csv_cell(value: object) -> str:
    """Neutralise spreadsheet formula injection (OWASP CSV injection guidance)."""
    text = "" if value is None else str(value)
    if text.startswith(CSV_FORMULA_PREFIXES):
        return "'" + text
    return text


def _states_csv(states_doc: dict) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["code", "name", "status", "count", "percent"])
    for row in states_doc["states"]:
        writer.writerow(
            sanitize_csv_cell(row[col]) for col in ("code", "name", "status", "count", "percent")
        )
    return buf.getvalue()


def current_release(out_dir: Path) -> Path | None:
    link = out_dir / "current"
    return link.resolve() if link.is_symlink() else None


def previous_total(out_dir: Path) -> int | None:
    release = current_release(out_dir)
    if release is None:
        return None
    try:
        doc = json.loads((release / "v1/statistics/summary.json").read_text(encoding="utf-8"))
        return int(doc["data"]["valid_responses"])
    except (OSError, ValueError, KeyError):
        return None


def check_drop(out_dir: Path, new_total: int, max_drop_fraction: float) -> None:
    """Refuse to publish if valid responses fell sharply, e.g. after a partial export."""
    prev = previous_total(out_dir)
    if prev and new_total < prev * (1 - max_drop_fraction):
        raise PublishRefused(
            f"valid responses fell from {prev} to {new_total}; "
            "investigate or re-run with --allow-drop"
        )


def publish(
    aggregates: dict[str, dict],
    out_dir: Path,
    *,
    survey_version: str,
    min_cohort: int,
    rounding: int = 5,
    now: datetime | None = None,
) -> Path:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    release_id = now.strftime("%Y%m%dT%H%M%S%fZ")
    meta = {
        "api_version": "v1",
        "survey_version": survey_version,
        # Minute precision: the refresh time, never a respondent's submission time.
        "generated_at": now.replace(second=0, microsecond=0).isoformat().replace("+00:00", "Z"),
        "min_cohort": min_cohort,
        "rounding": rounding,  # published counts are multiples of this
        "representativeness": (
            "Voluntary online survey. Results describe people who chose to respond "
            "and are not statistically representative of Indian taxpayers."
        ),
        "methodology_url": "/survey-methodology/",
    }

    releases = out_dir / "releases"
    staging = releases / f".staging-{release_id}"
    stats_dir = staging / "v1" / "statistics"
    stats_dir.mkdir(parents=True)
    for name in ENDPOINTS:
        body = json.dumps({"meta": meta, "data": aggregates[name]}, ensure_ascii=False, indent=2)
        (stats_dir / f"{name}.json").write_text(body + "\n", encoding="utf-8")
    (stats_dir / "states.csv").write_text(_states_csv(aggregates["states"]), encoding="utf-8")

    final = releases / release_id
    staging.rename(final)
    tmp_link = out_dir / f".current-{release_id}"
    tmp_link.symlink_to(Path("releases") / release_id)
    os.replace(tmp_link, out_dir / "current")
    _prune(releases, keep=KEEP_RELEASES, active=final)
    return final


def _prune(releases: Path, keep: int, active: Path) -> None:
    done = sorted(p for p in releases.iterdir() if p.is_dir() and not p.name.startswith("."))
    for old in done[:-keep]:
        if old != active:
            shutil.rmtree(old)
