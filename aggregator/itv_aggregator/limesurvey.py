"""Minimal client for LimeSurvey's documented RemoteControl 2 JSON-RPC API.

Uses a dedicated LimeSurvey account that only needs response-export
permission on the published survey. The database is never queried directly.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request


class LimeSurveyError(Exception):
    pass


class RemoteControl:
    def __init__(
        self, url: str, username: str, password: str, timeout: float = 60.0, allow_http: bool = False
    ):
        if not url.startswith("https://") and not (allow_http and url.startswith("http://")):
            raise LimeSurveyError("RemoteControl URL must use HTTPS (allow_http is for the local stack only)")
        self.url = url
        self.username = username
        self.password = password
        self.timeout = timeout
        self._next_id = 0

    def _call(self, method: str, *params):
        self._next_id += 1
        payload = json.dumps({"method": method, "params": list(params), "id": self._next_id})
        req = urllib.request.Request(
            self.url,
            data=payload.encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            # Do not echo request bodies: they contain credentials.
            raise LimeSurveyError(f"{method} failed: {type(exc).__name__}") from exc
        if body.get("error"):
            raise LimeSurveyError(f"{method} returned an error")
        return body.get("result")

    def export_responses_csv(self, survey_id: int) -> str:
        key = self._call("get_session_key", self.username, self.password)
        if not isinstance(key, str):
            raise LimeSurveyError("authentication failed")
        try:
            result = self._call(
                "export_responses", key, survey_id, "csv", None, "complete", "code", "short"
            )
        finally:
            try:
                self._call("release_session_key", key)
            except LimeSurveyError:
                pass
        if isinstance(result, dict):
            status = str(result.get("status", ""))
            # LimeSurvey reports an empty response table this way.
            if status.startswith("No Data"):
                return ""
            raise LimeSurveyError(f"export_responses status: {status or 'unknown'}")
        if not isinstance(result, str):
            raise LimeSurveyError("unexpected export_responses result")
        return base64.b64decode(result).decode("utf-8-sig")
