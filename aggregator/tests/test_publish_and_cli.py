import base64
import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from itv_aggregator import cli
from itv_aggregator.aggregate import Policy, aggregate
from itv_aggregator.limesurvey import LimeSurveyError, RemoteControl
from itv_aggregator.publish import ENDPOINTS, PublishRefused, check_drop, publish, sanitize_csv_cell

from conftest import SCHEMA_PATH, make_export, many

FORBIDDEN_KEYS = {"id", "response_id", "submitdate", "seed", "COMMENTS", "ipaddr", "token", "email", "answers", "selections"}


def walk_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from walk_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_keys(v)


def run_cli(tmp_path, rows, schema, *extra):
    export = tmp_path / "export.csv"
    export.write_text(make_export(schema, rows), encoding="utf-8")
    return cli.main(["--schema", str(SCHEMA_PATH), "--out", str(tmp_path / "out"), "--csv", str(export), *extra])


def test_cli_publishes_all_endpoints(tmp_path, schema):
    assert run_cli(tmp_path, many(25, state="TN", concerns=["HEALTH"]), schema) == 0
    stats = tmp_path / "out" / "current" / "v1" / "statistics"
    for name in ENDPOINTS:
        doc = json.loads((stats / f"{name}.json").read_text())
        assert doc["meta"]["min_cohort"] == 20
        assert "not statistically representative" in doc["meta"]["representativeness"]
    assert json.loads((stats / "summary.json").read_text())["data"]["valid_responses"] == 25


def test_public_output_contains_no_raw_fields_or_free_text(tmp_path, schema):
    secret = "My employer is ACME and my phone is 98xxxxxx01"
    rows = [dict(state="DL", COMMENTS=secret, id=900 + i) for i in range(30)]
    assert run_cli(tmp_path, rows, schema) == 0
    stats = tmp_path / "out" / "current" / "v1" / "statistics"
    for f in stats.iterdir():
        text = f.read_text()
        assert secret not in text
        assert "ACME" not in text
        assert "10:15" not in text, "submission times must not be published"
        if f.suffix == ".json":
            assert not FORBIDDEN_KEYS & set(walk_keys(json.loads(text)))


def test_generated_at_is_minute_precision(tmp_path, schema):
    now = datetime(2026, 11, 5, 9, 41, 37, 123456, tzinfo=timezone.utc)
    rel = publish(aggregate([], schema, Policy()), tmp_path, survey_version="v1", min_cohort=20, now=now)
    doc = json.loads((rel / "v1/statistics/summary.json").read_text())
    assert doc["meta"]["generated_at"] == "2026-11-05T09:41:00Z"


def test_new_release_replaces_current_atomically_and_old_ones_pruned(tmp_path, schema):
    agg = aggregate([], schema, Policy())
    for minute in range(12):
        now = datetime(2026, 11, 5, 9, minute, tzinfo=timezone.utc)
        last = publish(agg, tmp_path, survey_version="v1", min_cohort=20, now=now)
    assert (tmp_path / "current").resolve() == last
    assert (tmp_path / "current").readlink().is_absolute() is False
    assert len(list((tmp_path / "releases").iterdir())) == 10


def test_invalid_export_keeps_previous_release(tmp_path, schema):
    assert run_cli(tmp_path, many(25), schema) == 0
    before = (tmp_path / "out" / "current").resolve()
    bad = tmp_path / "bad.csv"
    bad.write_text("id,submitdate\n1,2026-11-02\n")
    code = cli.main(["--schema", str(SCHEMA_PATH), "--out", str(tmp_path / "out"), "--csv", str(bad)])
    assert code == 2
    assert (tmp_path / "out" / "current").resolve() == before


def test_concurrent_run_is_skipped(tmp_path, schema):
    import fcntl
    out = tmp_path / "out"
    out.mkdir()
    with open(out / ".lock", "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        assert run_cli(tmp_path, many(25), schema) == 4
    assert run_cli(tmp_path, many(25), schema) == 0


def test_sharp_drop_is_refused_unless_allowed(tmp_path, schema):
    assert run_cli(tmp_path, many(100), schema) == 0
    assert run_cli(tmp_path, many(40), schema) == 2
    assert run_cli(tmp_path, many(40), schema, "--allow-drop") == 0
    with pytest.raises(PublishRefused):
        check_drop(tmp_path / "out", 1, 0.1)


@pytest.mark.parametrize("value,expected", [
    ("=HYPERLINK(\"http://x\")", "'=HYPERLINK(\"http://x\")"),
    ("+91", "'+91"), ("-5", "'-5"), ("@SUM(A1)", "'@SUM(A1)"),
    ("Maharashtra", "Maharashtra"), (None, ""), (42, "42"),
])
def test_csv_formula_injection_is_neutralised(value, expected):
    assert sanitize_csv_cell(value) == expected


# --- LimeSurvey RemoteControl client against a local fake server -------------

class FakeLimeSurvey(BaseHTTPRequestHandler):
    export_result = None
    fail_auth = False
    calls: list[str] = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeLimeSurvey.calls.append(body["method"])
        result = {
            "get_session_key": {"status": "Invalid user name or password"} if self.fail_auth else "sess",
            "export_responses": self.export_result,
            "release_session_key": "OK",
        }[body["method"]]
        out = json.dumps({"id": body["id"], "result": result, "error": None}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *args):
        pass


@pytest.fixture
def fake_ls():
    FakeLimeSurvey.calls = []
    FakeLimeSurvey.fail_auth = False
    server = HTTPServer(("127.0.0.1", 0), FakeLimeSurvey)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/index.php/admin/remotecontrol"
    server.shutdown()


def test_remotecontrol_export_and_session_release(fake_ls, schema):
    csv_text = make_export(schema, many(3))
    FakeLimeSurvey.export_result = base64.b64encode(csv_text.encode()).decode()
    client = RemoteControl(fake_ls, "exporter", "pw", allow_http=True)
    assert client.export_responses_csv(123456) == csv_text
    assert FakeLimeSurvey.calls == ["get_session_key", "export_responses", "release_session_key"]


def test_remotecontrol_no_data_means_empty(fake_ls):
    FakeLimeSurvey.export_result = {"status": "No Data, survey table does not exist."}
    assert RemoteControl(fake_ls, "u", "p", allow_http=True).export_responses_csv(1) == ""


def test_remotecontrol_auth_failure_and_unknown_status(fake_ls):
    FakeLimeSurvey.export_result = {"status": "No permission"}
    with pytest.raises(LimeSurveyError, match="No permission"):
        RemoteControl(fake_ls, "u", "p", allow_http=True).export_responses_csv(1)
    FakeLimeSurvey.fail_auth = True
    with pytest.raises(LimeSurveyError, match="authentication"):
        RemoteControl(fake_ls, "u", "p", allow_http=True).export_responses_csv(1)


def test_remotecontrol_unreachable_does_not_leak_credentials():
    client = RemoteControl("http://127.0.0.1:9/x", "u", "s3cret-pw", timeout=2, allow_http=True)
    with pytest.raises(LimeSurveyError) as exc:
        client.export_responses_csv(1)
    assert "s3cret-pw" not in str(exc.value)


def test_remotecontrol_requires_https_by_default():
    with pytest.raises(LimeSurveyError, match="HTTPS"):
        RemoteControl("http://survey.example/x", "u", "p")


def test_cli_returns_3_when_limesurvey_down(tmp_path, monkeypatch):
    monkeypatch.setenv("ITV_LS_URL", "http://127.0.0.1:9/x")
    monkeypatch.setenv("ITV_LS_ALLOW_HTTP", "1")
    monkeypatch.setenv("ITV_LS_USER", "u")
    monkeypatch.setenv("ITV_LS_PASSWORD", "p")
    monkeypatch.setenv("ITV_LS_SURVEY_ID", "1")
    assert cli.main(["--schema", str(SCHEMA_PATH), "--out", str(tmp_path / "out")]) == 3
    assert not (tmp_path / "out" / "current").exists()
