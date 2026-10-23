"""Survey gate: proof-of-work (ALTCHA) and optional Cloudflare Turnstile check
before a visitor can open the survey.

nginx calls ``/gate/check`` (auth_request) for every survey-taking request. A
visitor without a valid pass is sent to ``/gate/``, solves a challenge, and
receives a signed, short-lived, HttpOnly pass cookie. Each pass allows a
bounded number of survey requests, so every additional automated submission
costs a fresh proof of work.

This raises the cost of automated stuffing; it does not prove a respondent is
unique or human. Stores nothing about the visitor beyond in-memory counters.
"""

from __future__ import annotations

import hashlib
import hmac
import html
import json
import os
import secrets
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import altcha

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
WIDGET = "altcha-3.2.4.min.js"
COOKIE = "itv_pass"
TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


PROTECTED_ENVS = ("staging", "production")


@dataclass
class Config:
    secret: bytes
    enabled: bool = True
    pass_ttl: int = 2 * 60 * 60
    pass_max_requests: int = 60  # one survey is ~10 requests; allows a few retries
    challenge_ttl: int = 10 * 60
    pow_algorithm: str = "PBKDF2/SHA-256"
    pow_cost: int = 5_000
    secure_cookie: bool = False
    turnstile_site_key: str = ""
    turnstile_secret: str = ""

    @classmethod
    def from_env(cls) -> "Config":
        path = os.environ.get("ITV_GATE_SECRET_FILE")
        secret = Path(path).read_text().strip() if path else os.environ.get("ITV_GATE_SECRET", "")
        if len(secret) < 32:
            raise SystemExit("ITV_GATE_SECRET (or _FILE) must be at least 32 characters")
        env = os.environ.get("ITV_ENV", "production")
        enabled = os.environ.get("ITV_GATE_ENABLED", "1") == "1"
        if not enabled and env in PROTECTED_ENVS:
            raise SystemExit(f"the survey gate cannot be disabled in {env}")
        return cls(
            secret=secret.encode(),
            enabled=enabled,
            pow_cost=int(os.environ.get("ITV_GATE_POW_COST", "5000")),
            secure_cookie=os.environ.get("ITV_GATE_SECURE_COOKIE", "1") == "1",
            turnstile_site_key=os.environ.get("TURNSTILE_SITE_KEY", ""),
            turnstile_secret=os.environ.get("TURNSTILE_SECRET", ""),
        )

    @property
    def turnstile_enabled(self) -> bool:
        return bool(self.turnstile_site_key and self.turnstile_secret)


@dataclass
class State:
    """In-memory, single-instance state. Use a shared store if the gate is scaled out."""

    used_challenges: dict[str, float] = field(default_factory=dict)
    pass_uses: dict[str, int] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def consume_challenge(self, key: str, expires_at: float) -> bool:
        with self.lock:
            now = time.time()
            for k in [k for k, exp in self.used_challenges.items() if exp < now]:
                del self.used_challenges[k]
            if key in self.used_challenges:
                return False
            self.used_challenges[key] = expires_at
            return True

    def use_pass(self, pass_id: str, limit: int) -> bool:
        with self.lock:
            n = self.pass_uses.get(pass_id, 0) + 1
            self.pass_uses[pass_id] = n
            return n <= limit


# --- pass cookie: "<pass_id>.<expires>.<hmac>" --------------------------------

def make_pass(cfg: Config, now: float | None = None) -> str:
    pass_id = secrets.token_urlsafe(12)
    expires = int((now or time.time()) + cfg.pass_ttl)
    body = f"{pass_id}.{expires}"
    sig = hmac.new(cfg.secret, body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def read_pass(cfg: Config, value: str, now: float | None = None) -> str | None:
    """Return the pass id if the cookie is authentic and unexpired."""
    try:
        pass_id, expires, sig = value.split(".")
        expected = hmac.new(cfg.secret, f"{pass_id}.{expires}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected) or int(expires) < (now or time.time()):
            return None
        return pass_id
    except ValueError:
        return None


def safe_next(value: str | None) -> str:
    """Only allow redirects back into the survey, never to another site."""
    if value and value.startswith("/index.php/") and "//" not in value and "\\" not in value:
        return value
    return "/"


def new_challenge(cfg: Config) -> dict:
    return altcha.create_challenge(
        cfg.pow_algorithm,
        cfg.pow_cost,
        expires_at=int(time.time()) + cfg.challenge_ttl,
        hmac_secret=cfg.secret,
    ).to_dict()


def verify_pow(cfg: Config, state: State, payload: str) -> bool:
    if not payload or len(payload) > 8_000:
        return False
    try:
        parsed = altcha.Payload.from_base64(payload)
    except (ValueError, KeyError, TypeError):
        return False
    result = altcha.verify_solution(parsed, cfg.secret)
    if not result.verified or not parsed.challenge.signature:
        return False
    expires = parsed.challenge.parameters.expires_at or time.time() + cfg.challenge_ttl
    return state.consume_challenge(parsed.challenge.signature, float(expires))


def verify_turnstile(cfg: Config, token: str, post=None) -> bool:
    if not cfg.turnstile_enabled:
        return True
    if not token or len(token) > 2_048:
        return False
    data = urllib.parse.urlencode({"secret": cfg.turnstile_secret, "response": token}).encode()
    try:
        if post is None:
            with urllib.request.urlopen(TURNSTILE_VERIFY_URL, data=data, timeout=5) as resp:
                body = json.loads(resp.read())
        else:
            body = post(TURNSTILE_VERIFY_URL, data)
    except (OSError, ValueError):
        return False  # fail closed: the edge is unavailable or the response is malformed
    return body.get("success") is True


GATE_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Before you start · Indian Taxpayer Voice</title>
<style>
  :root {{ --navy:#0F3D56; --teal:#0E7C7B; --ink:#12232E; --muted:#56656F; --line:#DCE3E7; --sand:#F6F3EE; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color:var(--ink);
         background:var(--sand); min-height:100vh; display:grid; place-items:center; padding:16px; font-size:17px; line-height:1.6; }}
  main {{ background:#fff; border:1px solid var(--line); border-radius:16px; max-width:520px; width:100%; padding:28px; }}
  h1 {{ color:var(--navy); font-size:1.5rem; line-height:1.2; margin:0 0 .5rem; }}
  p {{ margin:.5rem 0 1rem; }}
  .muted {{ color:var(--muted); font-size:.92rem; }}
  altcha-widget {{ display:block; margin:1.25rem 0; --altcha-max-width: 100%; }}
  button {{ width:100%; font:inherit; font-weight:700; color:#fff; background:var(--teal); border:0; border-radius:999px;
           padding:.85rem 1.5rem; min-height:48px; cursor:pointer; }}
  button:disabled {{ background:#9DB4BD; cursor:not-allowed; }}
  button:focus-visible {{ outline:3px solid #2EC4B6; outline-offset:2px; }}
  .error {{ background:#FDECEC; border:1px solid #F2B8B8; color:#7A1F1F; border-radius:8px; padding:.6rem .8rem; }}
</style>
</head>
<body>
<main>
  <h1>Before you start</h1>
  <p>To protect the survey from automated submissions, your browser will complete a brief check. It takes a few seconds and does not ask for any personal information.</p>
  {error}
  <form method="post" action="/gate/verify">
    <input type="hidden" name="next" value="{next}">
    <altcha-widget auto="onload" name="altcha" language="en"></altcha-widget>
    {turnstile}
    <button type="submit" id="go" disabled>Continue to the survey</button>
  </form>
  <noscript><p class="error">This check needs JavaScript. Please enable it to take part.</p></noscript>
  <p class="muted">The check uses <a href="https://altcha.org/">ALTCHA</a>, an open-source tool hosted on this site.{turnstile_note}</p>
</main>
<script type="module" src="/gate/static/{widget}"></script>
<script>
  const widget = document.querySelector('altcha-widget');
  // ALTCHA 3 treats a relative value as inline challenge data, so pass an absolute URL.
  widget.setAttribute('challenge', new URL('/gate/challenge', location.href).href);
  const go = document.getElementById('go');
  const needsTurnstile = {needs_turnstile};
  let powOk = false, tsOk = !needsTurnstile;
  const update = () => {{ go.disabled = !(powOk && tsOk); }};
  widget.addEventListener('statechange', (e) => {{ powOk = e.detail && e.detail.state === 'verified'; update(); }});
  window.itvTurnstileOk = () => {{ tsOk = true; update(); }};
</script>
</body>
</html>
"""


def render_gate(cfg: Config, next_url: str, error: str = "") -> bytes:
    turnstile = turnstile_note = ""
    if cfg.turnstile_enabled:
        turnstile = (
            '<div class="cf-turnstile" data-sitekey="%s" data-callback="itvTurnstileOk"></div>'
            '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>'
            % html.escape(cfg.turnstile_site_key, quote=True)
        )
        turnstile_note = " It also uses Cloudflare Turnstile, which processes your IP address."
    return GATE_PAGE.format(
        next=html.escape(next_url, quote=True),
        error=f'<p class="error" role="alert">{html.escape(error)}</p>' if error else "",
        turnstile=turnstile,
        turnstile_note=turnstile_note,
        needs_turnstile="true" if cfg.turnstile_enabled else "false",
        widget=WIDGET,
    ).encode()


class Handler(BaseHTTPRequestHandler):
    cfg: Config
    state: State
    server_version = "itv-gate"
    sys_version = ""

    def log_message(self, fmt, *args):  # no IPs or query strings in logs
        pass

    def _send(self, code: int, body: bytes = b"", ctype: str = "text/plain; charset=utf-8", headers=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _csp(self) -> dict:
        ts = " https://challenges.cloudflare.com" if self.cfg.turnstile_enabled else ""
        frames = ts.strip() or "'none'"
        return {"Content-Security-Policy": (
            f"default-src 'self'; script-src 'self' 'unsafe-inline'{ts}; frame-src {frames};"
            " worker-src 'self' blob:; style-src 'self' 'unsafe-inline'; img-src 'self' data:;"
            " connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )}

    def _pass_cookie(self) -> str | None:
        jar = cookies.SimpleCookie()
        try:
            jar.load(self.headers.get("Cookie", ""))
        except cookies.CookieError:
            return None
        morsel = jar.get(COOKIE)
        return morsel.value if morsel else None

    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        if url.path == "/gate/check":
            if not self.cfg.enabled:
                return self._send(204)  # local development only; refused in staging/production
            value = self._pass_cookie()
            pass_id = read_pass(self.cfg, value) if value else None
            ok = pass_id is not None and self.state.use_pass(pass_id, self.cfg.pass_max_requests)
            return self._send(204 if ok else 401)
        if url.path == "/gate/challenge":
            return self._send(200, json.dumps(new_challenge(self.cfg)).encode(), "application/json")
        if url.path in ("/gate/", "/gate"):
            nxt = safe_next(urllib.parse.parse_qs(url.query).get("next", [None])[0])
            if not self.cfg.enabled:
                return self._send(303, b"", headers={"Location": nxt})
            return self._send(200, render_gate(self.cfg, nxt), "text/html; charset=utf-8", self._csp())
        if url.path == f"/gate/static/{WIDGET}":
            body = (STATIC_DIR / WIDGET).read_bytes()
            return self._send(200, body, "text/javascript; charset=utf-8",
                              {"Cache-Control": "public, max-age=31536000, immutable"})
        if url.path == "/gate/health":
            return self._send(200, b"ok\n")
        return self._send(404, b"not found\n")

    do_HEAD = do_GET

    def do_POST(self):
        if urllib.parse.urlsplit(self.path).path != "/gate/verify":
            return self._send(404, b"not found\n")
        length = int(self.headers.get("Content-Length") or 0)
        if length > 16_384:
            return self._send(413, b"too large\n")
        form = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8", "replace"))
        nxt = safe_next(form.get("next", [None])[0])
        if not verify_pow(self.cfg, self.state, form.get("altcha", [""])[0]) or not verify_turnstile(
            self.cfg, form.get("cf-turnstile-response", [""])[0]
        ):
            page = render_gate(self.cfg, nxt, "The check did not complete. Please try again.")
            return self._send(403, page, "text/html; charset=utf-8", self._csp())
        cookie = f"{COOKIE}={make_pass(self.cfg)}; Max-Age={self.cfg.pass_ttl}; Path=/; HttpOnly; SameSite=Lax"
        if self.cfg.secure_cookie:
            cookie += "; Secure"
        return self._send(303, b"", headers={"Location": nxt, "Set-Cookie": cookie})


def make_server(cfg: Config, host: str = "0.0.0.0", port: int = 8000) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"cfg": cfg, "state": State()})
    return ThreadingHTTPServer((host, port), handler)


def main() -> None:
    server = make_server(Config.from_env(), port=int(os.environ.get("PORT", "8000")))
    server.serve_forever()


if __name__ == "__main__":
    main()
