import pytest

from itv_aggregator.ingest import IngestError, Limits, parse_export_text

from conftest import make_export, many


def test_valid_rows_are_parsed(schema):
    text = make_export(schema, [{"state": "KA", "industry": "EDU", "concerns": ["HEALTH", "JOBLOSS"]}])
    responses, report = parse_export_text(text, schema)
    assert report.valid == 1
    r = responses[0]
    assert (r.state, r.industry, r.concerns) == ("KA", "EDU", frozenset({"HEALTH", "JOBLOSS"}))
    assert r.answers["INCOME"] == "NA"
    assert str(r.submit_date) == "2026-11-02"


def test_empty_export_means_zero_responses(schema):
    responses, report = parse_export_text("", schema)
    assert responses == [] and report.valid == 0


def test_incomplete_and_unconsented_rows_are_excluded(schema):
    text = make_export(schema, [{"submitdate": ""}, {"consent": "N"}, {"consent": ""}, {}])
    responses, report = parse_export_text(text, schema)
    assert report.valid == 1
    assert report.incomplete == 1
    assert report.no_consent == 2


def test_unknown_codes_are_rejected(schema):
    rows = [{"state": "XX"}, {"industry": "=CMD()"}, {"submitdate": "yesterday"}]
    responses, report = parse_export_text(make_export(schema, rows), schema)
    assert responses == []
    assert (report.invalid_state, report.invalid_industry, report.invalid_date) == (1, 1, 1)


def test_unknown_concern_columns_and_values_are_ignored(schema):
    text = make_export(schema, [{"concerns": ["HEALTH"], "CONCERN[FAKE]": "Y"}],
                       extra_columns=("CONCERN[FAKE]", "COMMENTS"))
    responses, _ = parse_export_text(text, schema)
    assert responses[0].concerns == frozenset({"HEALTH"})


def test_optional_questions_blank_become_not_answered(schema):
    rows = [{"INCOME": "B2", "GENDER": "PNTS"}, {}]
    responses, report = parse_export_text(make_export(schema, rows), schema)
    assert report.valid == 2
    by_id = {r.response_id: r for r in responses}
    assert by_id["1"].answers["INCOME"] == "B2" and by_id["1"].answers["GENDER"] == "PNTS"
    assert by_id["2"].answers["INCOME"] == "NA" and by_id["2"].answers["AGEBAND"] == "NA"


def test_unknown_optional_answer_code_is_rejected(schema):
    responses, report = parse_export_text(make_export(schema, [{"INCOME": "B9"}, {"GENDER": "=1+1"}]), schema)
    assert responses == [] and report.invalid_answer == 2


def test_required_concern_must_be_selected(schema):
    responses, report = parse_export_text(make_export(schema, [{"concerns": []}]), schema)
    assert responses == [] and report.invalid_answer == 1


def test_priority_limited_to_three(schema):
    rows = [{"PRIORITY": ["UNEMP", "HINS", "OOP"]}, {"PRIORITY": ["UNEMP", "HINS", "OOP", "SPEND"]}]
    responses, report = parse_export_text(make_export(schema, rows), schema)
    assert report.valid == 1 and report.invalid_answer == 1
    assert responses[0].selections["PRIORITY"] == frozenset({"UNEMP", "HINS", "OOP"})


def test_duplicate_ids_from_retries_are_counted_once(schema):
    rows = [{"id": 7}, {"id": 7}, {"id": 7, "state": "GA"}, {"id": 8}]
    responses, report = parse_export_text(make_export(schema, rows), schema)
    assert report.valid == 2
    assert report.duplicate_ids == 2
    assert report.conflicting_duplicates == 1
    # First occurrence wins.
    assert next(r for r in responses if r.response_id == "7").state == "MH"


def test_missing_required_column_refuses_whole_export(schema):
    text = make_export(schema, [{}]).replace(",STATE,", ",STATE_RENAMED,", 1)
    with pytest.raises(IngestError, match="missing required columns"):
        parse_export_text(text, schema)


def test_oversized_field_is_rejected(schema):
    text = make_export(schema, [{"COMMENTS": "x" * 500}])
    with pytest.raises(IngestError, match="malformed CSV"):
        parse_export_text(text, schema, limits=Limits(max_field_chars=100))


def test_too_many_rows_is_rejected(schema):
    text = make_export(schema, many(6))
    with pytest.raises(IngestError, match="max_rows"):
        parse_export_text(text, schema, limits=Limits(max_rows=5))


def test_ragged_row_is_rejected(schema):
    text = make_export(schema, [{}]).rstrip("\n") + ",unexpected\n"
    with pytest.raises(IngestError, match="more fields"):
        parse_export_text(text, schema)


def test_bom_is_tolerated(schema):
    responses, _ = parse_export_text("﻿" + make_export(schema, [{}]), schema)
    assert len(responses) == 1


def test_semicolon_export_as_produced_by_limesurvey(schema):
    import csv, io
    rows = list(csv.reader(io.StringIO(make_export(schema, [{"state": "KA"}, {"state": "GA"}]))))
    buf = io.StringIO()
    csv.writer(buf, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\n").writerows(rows)
    responses, report = parse_export_text(buf.getvalue(), schema)
    assert report.valid == 2 and {r.state for r in responses} == {"KA", "GA"}


def test_limesurvey_anonymised_placeholder_date_becomes_unknown(schema):
    responses, report = parse_export_text(make_export(schema, [{"submitdate": "1980-01-01 00:00:00"}]), schema)
    assert report.valid == 1 and responses[0].submit_date is None
