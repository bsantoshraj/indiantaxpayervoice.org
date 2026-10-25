"""Split the articles doc's Markdown export into research/articles/, one file per article.

Takes either the raw .md export or the docs connector's JSON export result
({"data": {"bytes_b64": ...}}). Files are named NN-slug.md from each
"## N. Title" heading; the doc's opening section goes to 00-how-to-use.md.

Usage:
    python3 -I research/scripts/split_articles.py <export.md | export.json>
"""

from __future__ import annotations

import base64
import json
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "articles"


def load(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    if raw.lstrip().startswith("{"):
        data = json.loads(raw)["data"]
        text = base64.b64decode(data["bytes_b64"]).decode("utf-8")
        if len(text.encode("utf-8")) != data["bytes"]:
            raise ValueError("export is truncated")
        return text
    return raw


def slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower().replace("₹", "rs ")).strip("-")[:60].rstrip("-")


def main(path: str) -> None:
    parts = re.split(r"(?m)^(?=## \d+\. )", load(Path(path)))
    OUT.mkdir(exist_ok=True)
    (OUT / "00-how-to-use.md").write_text(parts[0], encoding="utf-8")
    for part in parts[1:]:
        number, title = re.match(r"## (\d+)\. (.*)", part).groups()
        name = f"{int(number):02d}-{slug(title)}.md"
        for old in OUT.glob(f"{int(number):02d}-*.md"):
            if old.name != name:
                old.unlink()  # the title changed
        (OUT / name).write_text("# " + part[3:], encoding="utf-8")
        print(name)


if __name__ == "__main__":
    main(sys.argv[1])
