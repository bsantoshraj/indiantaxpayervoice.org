from datetime import date

import pytest

from itv_aggregator.aggregate import NONE, PUBLISHED, SUPPRESSED, Policy, aggregate, protect_partition

from conftest import resp

K = 20


def by_code(rows, key="code"):
    return {r[key]: r for r in rows}


# --- protect_partition -------------------------------------------------------

def test_no_small_cells_means_nothing_suppressed():
    assert protect_partition({"a": 30, "b": 25, "c": 0}, K) == set()


def test_single_small_cell_gets_a_complement():
    hidden = protect_partition({"a": 100, "b": 40, "c": 3, "d": 0}, K)
    assert hidden == {"c", "b"}
    # The hidden total is large enough that "c" cannot be isolated.
    assert 3 + 40 >= K


def test_complement_accumulates_until_threshold():
    hidden = protect_partition({"a": 5, "b": 6, "c": 7, "d": 50, "e": 60}, K)
    assert hidden == {"a", "b", "c", "d"}


def test_two_small_cells_summing_over_threshold_still_both_hidden():
    assert protect_partition({"a": 12, "b": 15, "c": 80}, K) == {"a", "b"}


def test_zero_cells_never_suppressed():
    assert "z" not in protect_partition({"z": 0, "a": 3, "b": 90}, K)


def test_forced_cells_are_hidden_with_complement():
    hidden = protect_partition({"a": 50, "b": 60, "c": 70}, K, forced=["a"])
    assert len(hidden) == 2 and "a" in hidden


def test_everything_hidden_when_total_below_threshold():
    assert protect_partition({"a": 4, "b": 3}, K) == {"a", "b"}


# --- aggregate ---------------------------------------------------------------

def test_zero_responses_produce_honest_empty_state(schema):
    out = aggregate([], schema, Policy(K))
    assert out["summary"]["valid_responses"] == 0
    assert out["summary"]["states_represented"] == 0
    assert all(s["status"] == NONE for s in out["states"]["states"])
    assert out["trends"]["weeks"] == []


def test_counts_and_percentages(schema):
    rs = [resp(i, "MH", "ITSW", ["HEALTH"]) for i in range(30)]
    rs += [resp(100 + i, "KA", "EDU", ["HEALTH", "JOBLOSS"]) for i in range(30)]
    out = aggregate(rs, schema, Policy(K))
    states = by_code(out["states"]["states"])
    assert states["MH"] == {"code": "MH", "name": "Maharashtra", "status": PUBLISHED, "count": 30, "percent": 50.0}
    assert states["GA"]["status"] == NONE
    concerns = by_code(out["summary"]["concerns"])
    assert concerns["HEALTH"]["count"] == 60 and concerns["HEALTH"]["percent"] == 100.0
    assert concerns["JOBLOSS"]["count"] == 30 and concerns["JOBLOSS"]["percent"] == 50.0
    assert out["summary"]["states_represented"] == 2
    edu = by_code(out["industries"]["groups"])["EDU"]
    assert by_code(edu["concerns"])["JOBLOSS"]["percent"] == 100.0  # row percentage


def test_small_state_is_suppressed_and_not_derivable(schema):
    rs = [resp(i, "MH") for i in range(50)] + [resp(100 + i, "KA") for i in range(25)]
    rs += [resp(200, "LD")]
    out = aggregate(rs, schema, Policy(K))
    states = by_code(out["states"]["states"])
    assert states["LD"] == {"code": "LD", "name": "Lakshadweep", "status": SUPPRESSED, "count": None, "percent": None}
    published = sum(s["count"] for s in states.values() if s["status"] == PUBLISHED)
    hidden = out["summary"]["valid_responses"] - published
    assert hidden >= K, "suppressed states must not be recoverable from total minus published"


def test_heatmap_columns_cannot_be_differenced(schema):
    rs = [resp(i, industry="ITSW", concerns=["HEALTH"]) for i in range(40)]
    rs += [resp(100 + i, industry="FIN", concerns=["HEALTH"]) for i in range(30)]
    rs += [resp(200 + i, industry="FIN", concerns=["TAXCOMP"]) for i in range(10)]
    rs += [resp(300 + i, industry="EDU", concerns=["HEALTH"]) for i in range(25)]
    rs += [resp(400 + i, industry="EDU", concerns=["TAXCOMP"]) for i in range(5)]
    rs += [resp(500, industry="AGRI", concerns=["HEALTH"])]
    out = aggregate(rs, schema, Policy(K))
    national = by_code(out["summary"]["concerns"])["HEALTH"]["count"]
    cells = [by_code(i["concerns"])["HEALTH"] for i in out["industries"]["groups"]]
    published = sum(c["count"] for c in cells if c["status"] == PUBLISHED)
    assert national - published >= K


def test_concern_below_threshold_hidden_everywhere(schema):
    rs = [resp(i, concerns=["RETIRE"] if i < 3 else ["COSTLIV"]) for i in range(50)]
    out = aggregate(rs, schema, Policy(K))
    assert by_code(out["summary"]["concerns"])["RETIRE"]["status"] == SUPPRESSED
    for ind in out["industries"]["groups"]:
        assert by_code(ind["concerns"])["RETIRE"]["status"] in (SUPPRESSED, NONE)


def test_multi_select_percentages_can_exceed_100(schema):
    rs = [resp(i, concerns=["HEALTH", "JOBLOSS", "COSTLIV"]) for i in range(25)]
    out = aggregate(rs, schema, Policy(K))
    assert sum(c["percent"] for c in out["summary"]["concerns"] if c["percent"]) == pytest.approx(300.0)


def test_trends_bucket_by_week_without_precise_times(schema):
    rs = [resp(1, d=date(2026, 11, 2)), resp(2, d=date(2026, 11, 8)), resp(3, d=date(2026, 11, 9))]
    weeks = aggregate(rs, schema, Policy(K))["trends"]["weeks"]
    assert weeks == [{"week_start": "2026-11-02", "count": 2}, {"week_start": "2026-11-09", "count": 1}]


def test_demographic_breakdown_includes_not_answered_and_suppresses(schema):
    rs = [resp(i, INCOME="B2", concerns=["JOBLOSS"]) for i in range(40)]
    rs += [resp(100 + i, INCOME="B4", concerns=["HEALTH"]) for i in range(3)]
    rs += [resp(200 + i, concerns=["HEALTH"]) for i in range(30)]  # INCOME left blank
    out = aggregate(rs, schema, Policy(K))
    income = next(b for b in out["breakdowns"]["breakdowns"] if b["question"] == "INCOME")
    groups = by_code(income["groups"])
    assert groups["B2"]["count"] == 40
    assert groups["NA"]["label"] == "Not answered"
    assert groups["B4"]["status"] == SUPPRESSED
    published = sum(g["count"] for g in groups.values() if g["status"] == PUBLISHED)
    assert len(rs) - published >= K
    assert by_code(groups["B2"]["concerns"])["JOBLOSS"]["percent"] == 100.0


def test_breakdowns_are_never_crossed_with_state_or_each_other(schema):
    out = aggregate([resp(i, GENDER="W", INCOME="B1") for i in range(30)], schema, Policy(K))
    codes = [b["question"] for b in out["breakdowns"]["breakdowns"]]
    assert codes == ["EMPTYPE", "INCOME", "GENDER", "AGEBAND"]
    for b in out["breakdowns"]["breakdowns"]:
        for g in b["groups"]:
            assert set(g) == {"code", "label", "status", "count", "percent", "concerns"}
            assert {c["code"] for c in g["concerns"]} == set(schema.concerns)


def test_distributions_partition_and_multi_select(schema):
    rs = [resp(i, BUFFER="LT1") for i in range(25)] + [resp(100 + i, BUFFER="M6") for i in range(4)]
    rs += [resp(200 + i, BUFFER="M1") for i in range(60)]
    out = aggregate(rs, schema, Policy(K))
    dist = {d["question"]: d for d in out["distributions"]["questions"]}
    buffer = by_code(dist["BUFFER"]["options"])
    assert buffer["M1"]["count"] == 60
    # M6 (4) is primary-suppressed; LT1 (25) is hidden with it so M6 = total - M1 cannot be derived.
    assert buffer["M6"]["status"] == SUPPRESSED and buffer["LT1"]["status"] == SUPPRESSED
    assert buffer["NA"]["status"] == NONE
    assert set(dist) == {"BUFFER", "HCOVER", "PRIORITY"}
    assert "up to 3" in dist["PRIORITY"]["note"]


def test_withheld_dates_are_not_published_as_a_week(schema):
    rs = [resp(1, d=date(2026, 11, 2)), resp(2, d=None), resp(3, d=None)]
    trends = aggregate(rs, schema, Policy(K))["trends"]
    assert trends["weeks"] == [{"week_start": "2026-11-02", "count": 1}]
    assert trends["date_not_recorded"] == 2
