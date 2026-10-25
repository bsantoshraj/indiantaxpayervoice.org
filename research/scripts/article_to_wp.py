"""Convert an article from research/articles/ into WordPress block HTML.

The web version keeps the article and its references and drops what is only for
the owner: the "Owner check" note and the LinkedIn / X / WhatsApp posts.
Repository paths in backticks (`research/...`) become links to the file on
GitHub, so readers can open the evidence.

Charts: research/charts/manifest.json lists, per article number, the section
heading each chart goes under; the SVG is placed inline directly below it and
the section's table stays as the chart's text version. --chart "Heading
start=path.svg" (repeatable) overrides the manifest. Chart paths are relative
to the repository root.

Prints JSON {"title", "slug", "content"} for the staging upload.

Usage:
    python3 -I research/scripts/article_to_wp.py --slug how-many-indians-actually-pay-income-tax
    python3 -I research/scripts/article_to_wp.py research/articles/11-*.md \
        --chart "Who pays=research/charts/a11-who-pays.svg"
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

REPO = "https://github.com/bsantoshraj/indiantaxpayervoice.org/blob/main/"
ROOT = Path(__file__).resolve().parent.parent.parent
SOCIAL = {"**LinkedIn**", "**X**", "**WhatsApp / Facebook**", "**WhatsApp**"}


def inline(text: str) -> str:
    text = text.replace("\\[", "[").replace("\\]", "]")
    out, last = [], 0
    # Tokens: `code`, [text](url), bare URL, **bold**, *italic*
    pattern = re.compile(r"`([^`]+)`|\[([^\]]+)\]\((https?://[^)\s]+)\)|(https?://[^\s)]+)"
                         r"|\*\*(.+?)\*\*|\*(.+?)\*")
    for m in pattern.finditer(text):
        out.append(html.escape(text[last:m.start()], quote=False))
        code, label, url, bare, bold, italic = m.groups()
        if code:
            if code.startswith("research/"):
                out.append(f'<a href="{REPO}{html.escape(code)}"><code>{html.escape(code)}</code></a>')
            else:
                out.append(f"<code>{html.escape(code)}</code>")
        elif label:
            out.append(f'<a href="{html.escape(url)}">{inline(label)}</a>')
        elif bare:
            trail = ""
            while bare[-1] in ".,;":
                bare, trail = bare[:-1], bare[-1] + trail
            out.append(f'<a href="{html.escape(bare)}">{html.escape(bare)}</a>{trail}')
        elif bold:
            out.append(f"<strong>{inline(bold)}</strong>")
        else:
            out.append(f"<em>{inline(italic)}</em>")
        last = m.end()
    out.append(html.escape(text[last:], quote=False))
    return "".join(out)


def block(kind: str, inner: str, attrs: str = "") -> str:
    return f"<!-- wp:{kind}{attrs} -->\n{inner}\n<!-- /wp:{kind} -->"


def figure(svg_path: str) -> str:
    svg = (ROOT / svg_path).read_text(encoding="utf-8").strip()
    return block("html", f'<figure class="itv-chart" style="margin:1.5rem 0">{svg}</figure>')


def convert(markdown: str, charts: dict[str, str] | None = None) -> dict:
    charts = charts or {}
    lines = markdown.splitlines()
    title = re.sub(r"^#\s+(\d+\.\s+)?", "", lines[0]).strip()
    blocks, i, skipping = [], 1, False
    while i < len(lines):
        line = lines[i]
        if line.strip() in SOCIAL:
            skipping = True
        if line.startswith("### References"):
            skipping = False
        if skipping or not line.strip():
            i += 1
            continue
        if line.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i].lstrip(">").strip())
                i += 1
            text = " ".join(q for q in quote if q)
            if not text.startswith("Owner check"):
                blocks.append(block("quote", f'<blockquote class="wp-block-quote"><p>{inline(text)}</p></blockquote>'))
            continue
        if line.startswith("### "):
            blocks.append(block("heading", f'<h2 class="wp-block-heading">{inline(line[4:])}</h2>'))
            for start, path in charts.items():
                if line[4:].startswith(start):
                    blocks.append(figure(path))
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            head = "".join(f"<th>{inline(c)}</th>" for c in rows[0])
            body = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
            blocks.append(block("table", f'<figure class="wp-block-table"><table><thead><tr>{head}</tr></thead>'
                                         f"<tbody>{body}</tbody></table></figure>"))
            continue
        elif re.match(r"\d+\. ", line):
            first = int(line.split(".")[0])
            items = []
            while i < len(lines) and re.match(r"\d+\. ", lines[i]):
                items.append(block("list-item", f"<li>{inline(lines[i].split('. ', 1)[1])}</li>"))
                i += 1
            start = f' start="{first}"' if first != 1 else ""
            attrs = ' {"ordered":true' + (f',"start":{first}' if first != 1 else "") + "}"
            blocks.append(block("list", f'<ol class="wp-block-list"{start}>' + "".join(items) + "</ol>", attrs))
            continue
        elif line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(block("list-item", f"<li>{inline(lines[i][2:])}</li>"))
                i += 1
            blocks.append(block("list", '<ul class="wp-block-list">' + "".join(items) + "</ul>"))
            continue
        else:
            blocks.append(block("paragraph", f"<p>{inline(line)}</p>"))
        i += 1
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower().replace("₹", "rs ")).strip("-")[:70].rstrip("-")
    return {"title": title, "slug": slug, "content": "\n\n".join(blocks) + "\n"}


def convert_file(source: Path, wanted: dict[str, str] | None = None) -> dict:
    if not wanted:
        manifest = json.loads((ROOT / "research/charts/manifest.json").read_text(encoding="utf-8"))
        wanted = manifest.get(str(int(source.name[:2])), {})
    result = convert(source.read_text(encoding="utf-8"), wanted)
    placed = result["content"].count("itv-chart")
    if placed != len(wanted):
        sys.exit(f"{source.name}: placed {placed} of {len(wanted)} charts: check the heading names")
    return result


def by_slug(slug: str) -> dict:
    """The article in research/articles whose website slug is `slug`."""
    for source in sorted((ROOT / "research/articles").glob("[0-9][0-9]-*.md")):
        if not source.name.startswith("00-"):
            result = convert_file(source)
            if result["slug"] == slug:
                return result
    sys.exit(f"No article with slug '{slug}' in research/articles.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--slug"]:
        print(json.dumps(by_slug(args[1]), ensure_ascii=False))
        sys.exit()
    source, wanted = args[0], {}
    for flag, value in zip(args[1::2], args[2::2]):
        if flag != "--chart" or "=" not in value:
            sys.exit(f"unexpected argument {flag} {value}")
        heading, path = value.split("=", 1)
        wanted[heading] = path
    print(json.dumps(convert_file(Path(source), wanted), ensure_ascii=False))
