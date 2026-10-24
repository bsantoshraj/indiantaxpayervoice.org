from datetime import date

from itv_aggregator.aggregate import NONE, PUBLISHED, SUPPRESSED
from itv_aggregator.trends import load_history, record_total, save_history, weekly_trend

K = 20


def build(days_totals):
    history = []
    for d, total in days_totals:
        history = record_total(history, d, total)
    return history


def test_one_snapshot_per_day_latest_wins():
    h = build([(date(2026, 11, 2), 100), (date(2026, 11, 2), 120)])
    assert h == [{"date": "2026-11-02", "total": 120, "series": 1}]


def test_weekly_new_responses_from_week_end_totals():
    h = build([(date(2026, 11, 2), 100), (date(2026, 11, 8), 150),     # week of 2 Nov ends at 150
               (date(2026, 11, 10), 160), (date(2026, 11, 15), 200),   # week of 9 Nov: +50
               (date(2026, 11, 20), 210)])                             # week of 16 Nov: +10
    weeks = weekly_trend(h, K)["weeks"]
    assert [(w["week_start"], w["status"], w["new"], w["total"]) for w in weeks] == [
        ("2026-11-02", PUBLISHED, 150, 150), ("2026-11-09", PUBLISHED, 50, 200), ("2026-11-16", SUPPRESSED, None, 210)]
    assert weeks[0]["includes_earlier"] and not weeks[1]["includes_earlier"]


def test_quiet_week_is_none_not_suppressed():
    h = build([(date(2026, 11, 2), 100), (date(2026, 11, 9), 100)])
    assert weekly_trend(h, K)["weeks"][1]["status"] == NONE


def test_falling_total_starts_a_new_series_and_old_series_is_not_published():
    h = build([(date(2026, 11, 2), 300), (date(2026, 11, 9), 400), (date(2026, 11, 10), 0), (date(2026, 11, 17), 25)])
    assert [e["series"] for e in h] == [1, 1, 2, 2]
    weeks = weekly_trend(h, K)["weeks"]
    assert [(w["week_start"], w["new"], w["total"]) for w in weeks] == [("2026-11-09", 0, 0), ("2026-11-16", 25, 25)]
    assert all(w["new"] is None or w["new"] >= 0 for w in weeks)


def test_history_round_trip_and_bad_file(tmp_path):
    assert load_history(tmp_path) == []
    h = build([(date(2026, 11, 2), 40)])
    save_history(tmp_path, h)
    assert load_history(tmp_path) == h
    (tmp_path / "history" / "totals.json").write_text("not json")
    assert load_history(tmp_path) == []


def test_history_holds_only_dates_and_published_totals():
    h = build([(date(2026, 11, 2), 40)])
    assert set(h[0]) == {"date", "total", "series"}
