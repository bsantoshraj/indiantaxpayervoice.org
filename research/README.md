# Research

Evidence behind the articles: the sources each figure comes from, their
checksums, the scripts that turn official tables into the numbers we quote,
and the articles themselves.

| Path | What it holds |
|---|---|
| `articles/` | The articles, one file per article, exported from the drafts doc |
| `sources.csv` | Every source cited: article, publisher, title, date, URL, where the copy is kept |
| `sources/` | Copies of official and openly licensed sources (government reports, World Bank, RBI) |
| `sources/local/` | Copies of news and commercial pages. Gitignored: kept as evidence on the admin machine, not republished |
| `sources/harvest-log.csv` | When each copy was taken, whether directly or from the Internet Archive, and its SHA-256 |
| `SHA256SUMS` | Checksums of every copy, committed or local (`sha256sum -c SHA256SUMS` from this folder) |
| `scripts/` | `harvest.sh` downloads the sources; `cbdt_tables.py` extracts CBDT tables to CSV; `analyse_ay2023_24.py` computes the Article 11 figures; `analyse_timeseries.py` combines every year (AY 2012-13 to 2023-24) into `data/timeseries.csv`; `fiscal_drag.py` indexes the July 2014 limits to prices (`data/fiscal-drag.csv`); `article12_long_loan.py` is Article 12's second example (`data/a12-long-loan.csv`); `article14_housing.py` builds Article 14's sales split, chart and interest-share table; `charts_article11.py` / `charts_article12.py` / `charts_timeseries.py` draw the charts; `split_articles.py` splits the drafts doc export into `articles/`; `article_to_wp.py` converts an article for WordPress and `wp_article.sh` puts articles into WordPress as drafts or publishes one (see docs/ci-cd.md, "Publish an article") |
| `charts/` | Generated SVG charts, embedded inline in the website version of each article; `manifest.json` says which section heading each goes under |
| `data/` | Generated CSVs and `ay2023-24-summary.md`. Do not edit by hand; re-run the scripts |

## Reproduce

```sh
research/scripts/harvest.sh            # keeps existing copies; delete one to capture it again
for f in research/sources/a1[13]-cbdt-itr-stats-ay*.pdf; do python3 -I research/scripts/cbdt_tables.py "$f"; done
python3 -I research/scripts/analyse_ay2023_24.py && python3 -I research/scripts/analyse_timeseries.py
for c in charts_article11 charts_article12 charts_timeseries; do python3 -I research/scripts/$c.py; done
```

Articles reach WordPress through `wp_article.sh`, run where the Compose stack is:
`drafts` (every article; staging does this on each deploy) or `publish <slug>`
(production, only from the approved workflow). The end-to-end release flow is in
[docs/ci-cd.md](../docs/ci-cd.md#publish-an-article-controlled-release).

`cbdt_tables.py` needs `pdftotext` (poppler-utils). Every extracted table is
checked against its own printed total and the script stops if they differ.

## Rules

- Cite only pages we opened, and keep a copy with its checksum.
- Prefer the primary dataset to a summary of it. When a secondary copy disagrees
  with the primary, use the primary and record the difference here.
- Mark our own calculations as ours, and estimates as estimates.
- Content stays non-partisan: say what the data shows ("not published",
  "revised", "inconsistent with"), not motives.

## Known issues in sources

- **Rajya Sabha Unstarred Q. 2478 (17 Dec 2024), as reproduced by TaxGuru:**
  the ₹50 lakh–₹1 crore row of "All Taxpayers – Range of Returned Income,
  AY 2023-24" shows 6,27,580 returns. CBDT's own report (table 1.10) prints
  5,27,580, which also matches the row's average and the table total.
- **Deccan Herald (Article 2)** blocks both direct and archived downloads; no
  copy is kept. The same figures should be checked against the Lok Sabha
  answer on sansad.in.
- **incometaxindia.gov.in** refuses scripted downloads, so CBDT reports are
  taken from the Internet Archive; the checksums identify exactly which copy.
  All twelve years (AY 2012-13 to 2023-24) are captured; for AY 2018-19 and
  2021-22 the newest archive copy was not a PDF, so `harvest.sh` used the newest
  good snapshot from the archive's index (recorded in `harvest-log.csv`). A mirror
  on dit-live.taxmann.com was not used: its certificate had expired.
- **Older CBDT reports** (AY 2012-13 to 2018-19) print amounts in whole crore,
  so a table's rows can differ from its printed total by up to half a crore per
  row; counts always match exactly. AY 2018-19 prints losses as `- 48,255`, and
  AY 2012-13 to 2015-16 wrap one range label across two lines; `cbdt_tables.py`
  handles all three. Every year uses the same 24 income ranges.
- **CBDT house-property tables (2.3)** give one row for all losses, so the
  number of filers whose loss exceeds the Rs 2 lakh cap is not published there.
