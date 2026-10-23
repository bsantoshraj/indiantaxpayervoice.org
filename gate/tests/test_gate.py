import base64
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import altcha
import pytest

from itv_gate.app import COOKIE, Config, State, make_pass, make_server, read_pass, safe_next, verify_pow, verify_turnstile

SECRET = "x" * 40


@pytest.fixture
def cfg():
    return Config(secret=SECRET.encode(), pow_cost=10, secure_cookie=False)


def solve(challenge_dict) -> str:
    challenge = altcha.Challenge.from_dict(challenge_dict)
    solution = altcha.solve_challenge(challenge)
    return altcha.Payload(challenge, solution).to_base64()


@pytest.fixture
def server(cfg):
    srv = make_server(cfg, host="127.0.0.1", port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)


def get(url, cookie=None):
    req = urllib.request.Request(url, headers={"Cookie": cookie} if cookie else {})
    try:
        with opener.open(req) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def post(url, fields):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(fields).encode(), method="POST")
    try:
        with opener.open(req) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def test_full_flow_issues_pass_and_check_accepts_it(server):
    status, _, body = get(server + "/gate/challenge")
    assert status == 200
    payload = solve(json.loads(body))
    status, headers, _ = post(server + "/gate/verify", {"altcha": payload, "next": "/index.php/123456?lang=en"})
    assert status == 303
    assert headers["Location"] == "/index.php/123456?lang=en"
    set_cookie = headers["Set-Cookie"]
    assert "HttpOnly" in set_cookie and "SameSite=Lax" in set_cookie
    cookie = set_cookie.split(";")[0]
    assert get(server + "/gate/check", cookie)[0] == 204


def test_check_rejects_missing_forged_and_expired_pass(server, cfg):
    assert get(server + "/gate/check")[0] == 401
    assert get(server + "/gate/check", f"{COOKIE}=abc.9999999999.deadbeef")[0] == 401
    expired = make_pass(cfg, now=time.time() - cfg.pass_ttl - 10)
    assert get(server + "/gate/check", f"{COOKIE}={expired}")[0] == 401


def test_pass_has_bounded_number_of_uses(cfg):
    state = State()
    pid = read_pass(cfg, make_pass(cfg))
    assert all(state.use_pass(pid, 3) for _ in range(3))
    assert state.use_pass(pid, 3) is False


def test_solution_cannot_be_replayed(cfg):
    state = State()
    from itv_gate.app import new_challenge
    payload = solve(new_challenge(cfg))
    assert verify_pow(cfg, state, payload) is True
    assert verify_pow(cfg, state, payload) is False


def test_tampered_or_garbage_payload_rejected(cfg):
    from itv_gate.app import new_challenge
    state = State()
    payload = json.loads(base64.b64decode(solve(new_challenge(cfg))))
    payload["challenge"]["parameters"]["cost"] = 1  # weaken the puzzle
    forged = base64.b64encode(json.dumps(payload).encode()).decode()
    assert verify_pow(cfg, state, forged) is False
    assert verify_pow(cfg, state, "not-base64!!") is False
    assert verify_pow(cfg, state, "") is False
    assert verify_pow(cfg, state, "A" * 9000) is False


def test_challenge_signed_with_other_secret_rejected(cfg):
    from itv_gate.app import new_challenge
    other = Config(secret=b"y" * 40, pow_cost=10)
    assert verify_pow(cfg, State(), solve(new_challenge(other))) is False


def test_failed_verification_shows_error_and_no_cookie(server):
    status, headers, body = post(server + "/gate/verify", {"altcha": "bogus", "next": "/index.php/1"})
    assert status == 403 and "Set-Cookie" not in headers
    assert b"did not complete" in body


@pytest.mark.parametrize("value,expected", [
    ("/index.php/648566?lang=en", "/index.php/648566?lang=en"),
    ("https://evil.example/", "/"), ("//evil.example/", "/"), ("/index.php//evil", "/"),
    ("/admin", "/"), (None, "/"), ("/index.php/\\evil", "/"),
])
def test_next_cannot_redirect_off_site(value, expected):
    assert safe_next(value) == expected


def test_gate_page_escapes_next_and_sets_csp(server):
    status, headers, body = get(server + "/gate/?next=/index.php/1%22%3E%3Cscript%3E")
    assert status == 200
    assert b"<script>alert" not in body and b'"><script>' not in body
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]


def test_turnstile_is_skipped_when_unconfigured_and_fails_closed(cfg):
    assert verify_turnstile(cfg, "") is True
    ts = Config(secret=SECRET.encode(), turnstile_site_key="site", turnstile_secret="secret")
    assert verify_turnstile(ts, "tok", post=lambda url, data: {"success": True}) is True
    assert verify_turnstile(ts, "tok", post=lambda url, data: {"success": False}) is False
    assert verify_turnstile(ts, "", post=lambda url, data: {"success": True}) is False

    def down(url, data):
        raise OSError("unreachable")
    assert verify_turnstile(ts, "tok", post=down) is False


def test_short_secret_refused(monkeypatch):
    monkeypatch.setenv("ITV_GATE_SECRET", "short")
    with pytest.raises(SystemExit):
        Config.from_env()


def test_disabled_gate_lets_requests_through_locally():
    cfg = Config(secret=SECRET.encode(), enabled=False)
    srv = make_server(cfg, host="127.0.0.1", port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    try:
        assert get(base + "/gate/check")[0] == 204
        status, headers, _ = get(base + "/gate/?next=/index.php/1")
        assert status == 303 and headers["Location"] == "/index.php/1"
    finally:
        srv.shutdown()


@pytest.mark.parametrize("env", ["staging", "production"])
def test_gate_cannot_be_disabled_in_staging_or_production(monkeypatch, env):
    monkeypatch.setenv("ITV_GATE_SECRET", SECRET)
    monkeypatch.setenv("ITV_ENV", env)
    monkeypatch.setenv("ITV_GATE_ENABLED", "0")
    with pytest.raises(SystemExit, match="cannot be disabled"):
        Config.from_env()


def test_gate_enabled_by_default(monkeypatch):
    monkeypatch.setenv("ITV_GATE_SECRET", SECRET)
    monkeypatch.delenv("ITV_GATE_ENABLED", raising=False)
    monkeypatch.delenv("ITV_ENV", raising=False)
    assert Config.from_env().enabled is True
