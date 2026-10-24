"""Command-line entry point: fetch export -> validate -> aggregate -> publish.

Exit codes: 0 published, 2 refused/invalid input (previous release kept),
3 LimeSurvey unreachable (previous release kept), 4 another run in progress.
"""

from __future__ import annotations

import argparse
import fcntl
import logging
import os
import sys
from pathlib import Path

from .aggregate import Policy, aggregate
from .ingest import IngestError, Limits, parse_export_text
from .limesurvey import LimeSurveyError, RemoteControl
from .publish import PublishRefused, check_drop, publish
from .schema import load_schema

log = logging.getLogger("itv_aggregator")


def _secret(name: str) -> str:
    """Read NAME from NAME_FILE (container secret) or NAME; never logged."""
    path = os.environ.get(f"{name}_FILE")
    if path:
        return Path(path).read_text(encoding="utf-8").strip()
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"missing required setting {name} or {name}_FILE")
    return value


def _load_export(args) -> str:
    if args.csv:
        return Path(args.csv).read_text(encoding="utf-8-sig")
    client = RemoteControl(
        os.environ["ITV_LS_URL"],
        _secret("ITV_LS_USER"),
        _secret("ITV_LS_PASSWORD"),
        allow_http=os.environ.get("ITV_LS_ALLOW_HTTP") == "1",
    )
    return client.export_responses_csv(int(os.environ["ITV_LS_SURVEY_ID"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="itv-aggregator")
    parser.add_argument("--schema", default=os.environ.get("ITV_SCHEMA", "survey/questionnaire-v1.json"))
    parser.add_argument("--out", default=os.environ.get("ITV_OUT_DIR", "public-stats"))
    parser.add_argument("--csv", help="read a LimeSurvey CSV export file instead of the API")
    parser.add_argument("--min-cohort", type=int, default=int(os.environ.get("ITV_MIN_COHORT", "20")))
    parser.add_argument("--rounding", type=int, default=int(os.environ.get("ITV_ROUNDING", "5")),
                        help="round published counts to the nearest multiple (differencing protection)")
    parser.add_argument("--max-drop", type=float, default=0.10,
                        help="refuse if valid responses fall by more than this fraction")
    parser.add_argument("--allow-drop", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.min_cohort < 2:
        parser.error("--min-cohort must be at least 2")
    schema = load_schema(args.schema)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / ".lock", "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log.warning("another aggregator run holds the lock; skipping")
            return 4
        return _run(args, schema, out_dir)


def _run(args, schema, out_dir: Path) -> int:
    try:
        text = _load_export(args)
    except LimeSurveyError as exc:
        log.error("export failed, keeping previous release: %s", exc)
        return 3

    try:
        responses, report = parse_export_text(text, schema, limits=Limits())
        if not args.allow_drop:
            check_drop(out_dir, len(responses), args.max_drop)
    except (IngestError, PublishRefused) as exc:
        log.error("not publishing, keeping previous release: %s", exc)
        return 2

    # Counts only: no response IDs, answers or free text in logs.
    log.info(
        "rows=%d valid=%d incomplete=%d no_consent=%d invalid_state=%d invalid_industry=%d "
        "invalid_answer=%d invalid_date=%d duplicates=%d conflicting_duplicates=%d",
        report.rows_read, report.valid, report.incomplete, report.no_consent, report.invalid_state,
        report.invalid_industry, report.invalid_answer, report.invalid_date, report.duplicate_ids,
        report.conflicting_duplicates,
    )
    aggregates = aggregate(responses, schema, Policy(min_cohort=args.min_cohort, rounding=args.rounding))
    release = publish(aggregates, out_dir, survey_version=schema.survey_version,
                      min_cohort=args.min_cohort, rounding=args.rounding)
    log.info("published release %s", release.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
