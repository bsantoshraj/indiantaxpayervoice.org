"""Origin-side check of Cloudflare Access tokens for the LimeSurvey admin.

Cloudflare Access authenticates administrators at the edge and attaches a
signed JWT (``Cf-Access-Jwt-Assertion``) to each request. nginx asks
``/access/check`` before proxying the admin hostname, so the admin stays closed
even if the Access application or policy were misconfigured or bypassed: the
token must be signed by our team's keys, be issued for our application (aud),
be unexpired, and name an allowed email address.

Fails closed in staging and production. Locally, with no Access settings, the
check allows requests (there is no Cloudflare in front of a laptop).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

import jwt

PROTECTED_ENVS = ("staging", "production")
HEADER = "Cf-Access-Jwt-Assertion"


@dataclass
class AccessConfig:
    env: str = "production"
    team_domain: str = ""  # e.g. indiantaxpayervoice.cloudflareaccess.com
    audiences: tuple[str, ...] = ()
    allowed_emails: frozenset[str] = frozenset()

    @classmethod
    def from_env(cls) -> "AccessConfig":
        split = lambda name: [v.strip() for v in os.environ.get(name, "").split(",") if v.strip()]
        return cls(
            env=os.environ.get("ITV_ENV", "production"),
            team_domain=os.environ.get("ITV_ACCESS_TEAM_DOMAIN", "").strip(),
            audiences=tuple(split("ITV_ACCESS_AUD")),
            allowed_emails=frozenset(e.lower() for e in split("ITV_ACCESS_ALLOWED_EMAILS")),
        )

    @property
    def configured(self) -> bool:
        return bool(self.team_domain and self.audiences and self.allowed_emails)


class AccessVerifier:
    def __init__(self, cfg: AccessConfig, signing_key: Callable[[str], object] | None = None):
        self.cfg = cfg
        if signing_key is None and cfg.team_domain:
            client = jwt.PyJWKClient(f"https://{cfg.team_domain}/cdn-cgi/access/certs",
                                     cache_jwk_set=True, lifespan=300, timeout=5)
            signing_key = lambda token: client.get_signing_key_from_jwt(token).key
        self._signing_key = signing_key

    def allows(self, token: str | None) -> bool:
        if not self.cfg.configured:
            return self.cfg.env not in PROTECTED_ENVS  # local development only
        if not token or len(token) > 8_192:
            return False
        try:
            claims = jwt.decode(
                token,
                self._signing_key(token),
                algorithms=["RS256"],
                audience=list(self.cfg.audiences),
                issuer=f"https://{self.cfg.team_domain}",
                options={"require": ["exp", "iat", "aud", "iss", "email"]},
                leeway=30,
            )
        except (jwt.PyJWTError, OSError, ValueError):
            return False  # bad signature, wrong app, expired, or Cloudflare's keys unreachable
        return str(claims.get("email", "")).lower() in self.cfg.allowed_emails
