import threading
import time
import urllib.error
import urllib.request

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from itv_gate.access import HEADER, AccessConfig, AccessVerifier
from itv_gate.app import Config, make_server

TEAM = "team.cloudflareaccess.com"
AUD = "a" * 64
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def token(key=KEY, alg="RS256", **overrides):
    now = int(time.time())
    claims = {"aud": [AUD], "iss": f"https://{TEAM}", "email": "hello@example.org",
              "iat": now, "exp": now + 300, "sub": "u1"}
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm=alg, headers={"kid": "k1"})


@pytest.fixture
def verifier():
    cfg = AccessConfig(env="staging", team_domain=TEAM, audiences=(AUD,),
                       allowed_emails=frozenset({"hello@example.org"}))
    return AccessVerifier(cfg, signing_key=lambda _t: KEY.public_key())


def test_valid_token_for_allowed_email(verifier):
    assert verifier.allows(token())
    assert verifier.allows(token(email="HELLO@example.org"))  # email case-insensitive


@pytest.mark.parametrize("bad", [
    {"aud": ["b" * 64]},                      # another Access application
    {"iss": "https://evil.cloudflareaccess.com"},
    {"exp": int(time.time()) - 120},          # expired beyond leeway
    {"email": "someone@example.org"},         # authenticated but not allowed
    {"email": None},                          # service token / no identity
])
def test_rejects_wrong_claims(verifier, bad):
    assert not verifier.allows(token(**bad))


def test_rejects_wrong_signer_and_algorithm_tricks(verifier):
    assert not verifier.allows(token(key=OTHER_KEY))
    assert not verifier.allows(jwt.encode({"aud": [AUD]}, "secret", algorithm="HS256"))
    assert not verifier.allows(token().rsplit(".", 1)[0] + ".")  # signature stripped
    assert not verifier.allows(None) and not verifier.allows("") and not verifier.allows("x" * 9000)


def test_unreachable_keys_fail_closed():
    def boom(_t):
        raise jwt.PyJWKClientError("certs unreachable")
    cfg = AccessConfig(env="staging", team_domain=TEAM, audiences=(AUD,), allowed_emails=frozenset({"hello@example.org"}))
    assert not AccessVerifier(cfg, signing_key=boom).allows(token())


@pytest.mark.parametrize("env,expected", [("local", True), ("staging", False), ("production", False)])
def test_unconfigured_allows_only_locally(env, expected):
    assert AccessVerifier(AccessConfig(env=env)).allows(None) is expected


def test_from_env(monkeypatch):
    monkeypatch.setenv("ITV_ENV", "staging")
    monkeypatch.setenv("ITV_ACCESS_TEAM_DOMAIN", TEAM)
    monkeypatch.setenv("ITV_ACCESS_AUD", f" {AUD} , ")
    monkeypatch.setenv("ITV_ACCESS_ALLOWED_EMAILS", "Hello@Example.org,ops@example.org")
    cfg = AccessConfig.from_env()
    assert cfg.configured and cfg.audiences == (AUD,)
    assert cfg.allowed_emails == {"hello@example.org", "ops@example.org"}


def test_check_endpoint(verifier):
    srv = make_server(Config(secret=b"x" * 40), host="127.0.0.1", port=0, access=verifier)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_port}/access/check"

    def status(headers):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code

    try:
        assert status({HEADER: token()}) == 204
        assert status({HEADER: token(email="someone@example.org")}) == 403
        assert status({}) == 403
    finally:
        srv.shutdown()
