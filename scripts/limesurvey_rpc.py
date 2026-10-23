"""Admin RemoteControl calls used by setup-local-survey.sh (local stack only).

Reads LS_URL, LS_ADMIN_USER, LS_ADMIN_PASSWORD and STRUCTURE from the
environment and prints only the new survey ID.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.request


def call(url: str, method: str, *params):
    body = json.dumps({"method": method, "params": list(params), "id": 1}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        out = json.loads(resp.read())
    if out.get("error"):
        raise SystemExit(f"{method}: error")
    return out["result"]


def import_and_activate() -> int:
    url = os.environ["LS_URL"]
    key = call(url, "get_session_key", os.environ["LS_ADMIN_USER"], os.environ["LS_ADMIN_PASSWORD"])
    if not isinstance(key, str):
        raise SystemExit("authentication failed")
    try:
        with open(os.environ["STRUCTURE"], "rb") as fh:
            data = base64.b64encode(fh.read()).decode()
        old = os.environ.get("REPLACE_SID")
        if old and old.isdigit():
            # Local rebuild: drop the previous copy (and its local test responses).
            call(url, "delete_survey", key, int(old))
        sid = call(url, "import_survey", key, data, "txt")
        if not isinstance(sid, int):
            raise SystemExit(f"import_survey failed: {sid}")
        result = call(url, "activate_survey", key, sid)
        if not (isinstance(result, dict) and result.get("status") == "OK"):
            raise SystemExit(f"activate_survey failed: {result}")
        return sid
    finally:
        call(url, "release_session_key", key)


if __name__ == "__main__":
    if sys.argv[1:] != ["import-and-activate"]:
        raise SystemExit("usage: limesurvey_rpc.py import-and-activate")
    print(import_and_activate())
