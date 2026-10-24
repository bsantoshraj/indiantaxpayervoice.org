# Indian Taxpayer Voice: Phase 2 status report

**Status on 2026-10-24:** the aggregation pipeline, the public statistics API, the
differencing protection, the tile-grid state/UT map and five concern heat maps are
built and live on staging. **Phase 2 is not complete:** trends over time, filters and
tooltips for the heat maps, a manual screen-reader check, and the privacy review
before launch remain. See [Remaining work](#6-remaining-work-to-close-phase-2).

Phase 2 in the project brief (§12) is "Aggregation and public statistics"; the
requirements for maps and heat maps are in §8. Phase 1 status:
[phase-1-report.md](phase-1-report.md). How it works: [how-it-works.md](how-it-works.md).

Markers: ✅ done and verified · ◐ partly done · ❌ not done.

## 1. Phase 2 scope (brief §12)

| Item | Status | State on staging |
|---|---|---|
| Controlled LimeSurvey integration | ✅ | RemoteControl API, called over the internal network by a `stats-exporter` account that can only export this one survey. No public route to raw data |
| Precomputed aggregate statistics | ✅ | Hourly aggregator: validation, dedupe, small-group suppression (k = 20) with complementary suppression, rounding, atomic publish; a suspicious drop keeps the previous release |
| Public statistics API / static publishing | ✅ | `stats-staging…/v1/statistics/{summary, states, industries, breakdowns, distributions, trends}` and `states.csv`; read-only (WAF allows only GET/HEAD), cached by Cloudflare per the origin's headers |
| Public counters and heat maps | ◐ | Counters ✅, tile-grid map ✅, heat maps by sector, income, gender, age and employment ✅. Trends ❌ |
| Suppression and privacy tests | ✅ | 61 aggregator tests, including synthetic-data tests for rounding and differencing |
| Metric definitions and refresh intervals | ✅ | Methodology page: counting rules, suppression, rounding, hourly refresh, limitations, corrections |

## 2. Map and heat-map requirements (brief §8)

| Requirement | Status | How |
|---|---|---|
| Properly licensed map asset | ✅ | Tile-grid map: one equal tile per state/UT, no boundaries, so no boundary data or Survey of India licensing (owner decision) |
| Keyboard-accessible, with a tabular alternative | ✅ | Tiles are focusable with a visible focus ring and tooltip; the state table stays below the map; heat maps are real tables |
| Filters and explanatory tooltips | ◐ | Map tooltips ✅; heat-map filters ❌ |
| Counts, percentages and denominators understandable | ✅ | Each tile and heat-map row shows its count; captions state the denominator; rounding is explained on the page and in the methodology |
| Respondent-reported state, never inferred from IP | ✅ | Only the answered state is used; stated on the methodology page |
| Voluntary nature and limitations labelled | ✅ | "Not statistically representative" note under every statistic |
| Minimum cohort of 20, privacy review before launch | ◐ | k = 20 enforced; **privacy review not yet done** |
| Suppress or combine small groups | ✅ | Primary and complementary suppression; rare income bands and gender groups are hidden in the heat maps |
| Consider differencing across filters and updates | ✅ | Hourly releases, counts rounded to 5, whole percentages from rounded figures; demographic questions never crossed with each other or with state |
| No precise locations; never invent data | ✅ | State level only; states with no responses are shown as such |
| Multi-select effect on totals documented | ✅ | Heat-map captions, notes in the API and the methodology page |
| Insufficient data distinct from zero | ✅ | "Not shown" (hatched) versus "No responses" (dashed) on the map and in the tables |

## 3. Acceptance criteria (Phase 0 report §9)

| Criterion | Status | Evidence |
|---|---|---|
| No public file contains IDs, timestamps finer than a week, or free text | ✅ | Tested in the aggregator suite; the only time in a release is the refresh time (minute precision) |
| Suppression verified on synthetic data in staging | ◐ | Verified on synthetic releases **locally** (1,112 and 1,200 responses): small groups hidden, complementary suppression, rounding. Not run on staging, to avoid publishing fabricated figures on a public URL; a staging dry run that does not publish is proposed instead |
| Map and charts pass keyboard and screen-reader checks | ◐ | Keyboard focus and tooltip verified in a real browser; screen-reader text present for every tile and cell. **Manual screen-reader test (NVDA or TalkBack) not done** |

## 4. What was built

- **Differencing protection** (`aggregator/itv_aggregator/aggregate.py`): counts and denominators rounded to the nearest 5 (`ITV_ROUNDING`); percentages are whole numbers from the rounded figures; suppression decided on exact counts; weekly trend counts suppressed and rounded too; releases hourly (`ITV_AGG_INTERVAL`, 3600 s; 300 s locally).
- **Tile-grid map** (`[itv_state_map]`): 36 tiles on a 9 × 7 grid; five shades; hatched "not shown" and dashed "no responses" tiles; a list with a full text description per tile; text contrast at least 5.2:1.
- **Heat maps** (`[itv_heatmap question=…]`): sector, income band, gender, age band and employment type against the seven concerns; shaded table cells (five levels) with a legend; short column headings with full wording for screen readers.
- **Statistics page:** counters, the map, the state table and "Concerns by group" with the five heat maps; each carries the refresh time, the minimum group size and the rounding note.

## 5. Verified results (2026-10-24)

| Check | Result |
|---|---|
| Aggregator tests | 61 passed (rounding, differencing, suppression on exact counts, trends) |
| Synthetic releases (local) | Map: 12 states shown in five shades, 4 hidden, 20 with no responses; values rounded (22 → 20, 24 → 25). Heat maps: top income bands and "another gender identity" cells hidden; complementary suppression visible |
| Responsive check, 14 pages × 7 widths | 98/98 PASS after the map and heat maps |
| Phone layout | No horizontal scroll at 375 px (a 444 px overflow from screen-reader text in scrollable tables was found and fixed) |
| Staging after deploy | Statistics page shows 36 tiles and 5 heat maps; release metadata `rounding: 5`; aggregator interval 3600 s; smoke tests pass |

**Remaining privacy risk (documented):** a state changing from "no responses" to "not
shown" reveals that someone from that state answered. Showing zero separately from
insufficient data is a requirement; hourly releases blur when it happened.

## 6. Remaining work to close Phase 2

- [ ] **Trends over time** from the change in totals between releases (responses carry no dates), with the same suppression and rounding
- [ ] **Heat-map filters** (for example, choose a question or concern) as progressive enhancement, without creating new cross-tabulations
- [ ] **Manual screen-reader test** of the map and heat maps (NVDA on Windows or TalkBack on Android)
- [ ] **Privacy review before launch** (brief §8): minimum group size, rounding, the zero-versus-hidden signal, and the free-text comments, ideally by someone independent
- [ ] **Staging verification without publishing**: run the aggregator on synthetic data into a temporary directory on staging and check the output, so no fabricated figures appear publicly
- [ ] Optional: publish statistics to Spaces/CDN if production traffic needs it (Cloudflare already caches the static files)
