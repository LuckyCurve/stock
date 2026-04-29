# Munger Analysis Dashboard Design

## Overview

A self-contained HTML dashboard for Munger-style long-term investment analysis. Reads cached financial data from `roic_cache/`, computes ROIC and key metrics, and presents them in an interactive left-right split layout with light theme and mixed Chinese/English labels.

**Trigger**: Run `bash build.sh` in terminal after updating cache. Outputs a single `munger-dashboard.html` file.

## Architecture

```
roic_cache/*.yaml  →  build.sh  →  munger-dashboard.html
                        │
                        └─ Python (hand-written YAML parser, zero deps)
                           - Parse all YAML files
                           - Compute ROIC, net cash, CAGR, key ratios
                           - Compute Munger screening results
                           - Embed JSON data + ECharts + HTML into single file
```

## Layout: Left-Right Split, Light Theme

### Left Panel (fixed, ~220px width)

**Ticker list** (scrollable):
- Each row: checkbox + ticker name + mini ROIC median indicator (color-coded: green ≥20%, yellow 10-20%, red <10%)
- **Selection modes**:
  - Click ticker name → single-select (drives 深度详情 Tab)
  - Check checkbox → multi-select (drives 图表对比 Tab), max 8 tickers, warn on overflow
- Tickers with <20 years of data: show ⚠️ icon next to name + grey year count
- Checked tickers highlighted with light blue background

**Bottom section** — Munger screening verdict:
- ✅ 候选: [tickers passing all 5]
- ⚠️ 边缘: [tickers passing 3-4]
- ❌ 淘汰: [tickers with hard flaws]

### Right Panel (flex, with sub-tabs)

Three sub-tabs: `📊 汇总排名` | `📈 图表对比` | `🔍 深度详情`

---

## Sub-Tab 1: 📊 汇总排名

Full ticker summary table (Mode C from munger-analysis skill):

| Column | Description |
|--------|-------------|
| Ticker | Stock symbol, ⚠️ if <20 years |
| Yrs | Number of years of data |
| CAGR% | Revenue compound annual growth rate |
| ROICmed | Median ROIC across all years |
| Recent5 | Mean ROIC of last 5 years |
| MinROIC | Lowest ROIC year |
| <10y | Number of years ROIC < 10% |
| NetC% | Net cash as % of total assets |
| ✅ | Munger screen pass count (0-5) |

- **Sortable columns**: click header to sort ascending/descending
- **Row highlighting**: checked tickers get light blue background
- **<20 years flag**: ticker name gets ⚠️ suffix, Yrs column in grey

---

## Sub-Tab 2: 📈 图表对比

Only shows data for **checkbox-selected** tickers (max 8).

### Charts (ECharts, 2×2 grid)

1. **ROIC 时序折线图** — Core chart. All selected tickers overlaid, x-axis = fiscal year, y-axis = ROIC%. Tooltip shows all series. Reference lines at 10% and 20%.

2. **营收/EBIT 增长曲线** — Semi-log y-axis. Revenue and EBIT as separate series per ticker. Legend to toggle visibility.

3. **柱状图** — Grouped bars comparing: Net Cash %, ROIC median, Min ROIC across selected tickers. Color-coded (green/yellow/red by threshold).

4. **雷达图** — 5 dimensions per ticker:
   - ROIC 稳定性 (scored by: 100 - normalized bad_years count)
   - 增长 (CAGR normalized)
   - 净现金 (NetC% normalized)
   - FCF 质量 (FCF/NI ratio normalized, capped at 1.2)
   - 轻资产度 (100 - CapEx/Revenue*10, capped)

### Key Ratios Comparison Table

Below charts, for all selected tickers:

| Metric | T1 | T2 | ... |
|--------|----|----|-----|
| Gross Margin % | | | |
| Operating Margin % | | | |
| FCF / Net Income | | | |
| CapEx / Revenue | | | |
| Current Ratio | | | |

Color-coded: green = best in row, red = worst in row.

---

## Sub-Tab 3: 🔍 深度详情

Shows data for the **single-selected** ticker (clicked name in left panel).

### Top: Munger Screening + Statistics Summary

- Pass/fail for each of 5 screening criteria with values
- ROIC statistics: min / max / mean / median / stdev
- Distribution: negative years / <10% years / <20% years
- ⚠️ warning if <20 years of data

### Middle: ROIC Calculation Detail Table (year-by-year)

| Year | Revenue | EBIT | Total Equity | LT Debt | ST Debt | Cash | NOPAT | IC | ROIC% |
|------|---------|------|-------------|---------|---------|------|-------|----|-------|

- NOPAT = EBIT × (1 - 0.25)
- IC = Total Equity + LT Debt + ST Debt - Cash
- ROIC% = NOPAT / IC × 100 (null if IC ≤ 0)
- ROIC% column color-coded: green ≥20, yellow 10-20, red <10, grey null
- Allows full verification of how each year's ROIC was computed

### Bottom: Three Statements (sub-sub-tabs)

Three clickable tabs: `Income` | `Balance` | `Cashflow`

- Full raw data table: Year × Item, exactly as in YAML
- All items from the original data, no filtering
- Null values shown as "—" in grey
- Allows spot-checking any line item

---

## Computed Metrics

### ROIC Formula

```
NOPAT = EBIT × (1 - 25%)
IC (Invested Capital) = Total Equity + LT Debt + ST Debt - Cash
ROIC = NOPAT / IC × 100
```

- IC ≤ 0 → ROIC = null (skip in statistics)
- Cash field: use `+ Cash & Cash Equivalents` (strict, not the broader "Cash, Cash Equivalents & STI")

### Net Cash

```
Net Cash = Cash - LT Debt - ST Debt
NetC% = Net Cash / Total Assets × 100
```

Positive = net cash company (Munger prefers).

### CAGR

```
CAGR = (End Revenue / Start Revenue) ^ (1 / Years) - 1
```

Based on Revenue. If start or end is null or ≤ 0, CAGR = null.

### Key Ratios

| Ratio | Formula | Source Items |
|--------|---------|-------------|
| Gross Margin % | Gross Profit / Revenue × 100 | `Gross Profit` / `Sales/Revenue/Turnover` |
| Operating Margin % | Operating Income / Revenue × 100 | `Operating Income (Loss)` / `Sales/Revenue/Turnover` |
| FCF / Net Income | Free Cash Flow / Net Income | `Free Cash Flow` / `Net Income, GAAP` |
| CapEx / Revenue | Capital Expenditures / Revenue × 100 | `Capital Expenditures` / `Sales/Revenue/Turnover` |
| Current Ratio | (from data) | `Current Ratio` |

### Munger Screening (5 criteria)

| # | Criterion | Pass |
|---|-----------|------|
| 1 | MinROIC ≥ 10% | Minimum ROIC across all years ≥ 10 |
| 2 | <10y ≤ 3 | Years with ROIC < 10% is at most 3 |
| 3 | ROICmed ≥ 20% | Median ROIC ≥ 20 |
| 4 | NetC% > 0 | Net cash positive |
| 5 | CAGR > 5% | Revenue CAGR > 5% |

- 5/5 → ✅ 候选
- 3-4/5 → ⚠️ 边缘
- 0-2/5 → ❌ 淘汰

### <20 Years Flag

Tickers with fewer than 20 years of data (based on Revenue years available):
- Left panel: ⚠️ icon + grey year count next to ticker name
- Summary table: ⚠️ suffix on ticker name, Yrs in grey
- Deep detail: ⚠️ warning banner at top

---

## Build Script: build.sh

**Input**: `./roic_cache/*.yaml`
**Output**: `./munger-dashboard.html`
**Platform**: Windows Git Bash + macOS

### Steps

1. Find all `.yaml` files in `./roic_cache/`
2. Run embedded Python script:
   a. Hand-written YAML parser (no pyyaml dependency) — parse each file into `{ticker, statement, fiscalYear, item, value}` records
   b. Organize data by ticker → statement → item → {year: value}
   c. Compute all metrics (ROIC per year, net cash, CAGR, key ratios, Munger screening)
   d. Output as JSON to stdout
3. Embed JSON into HTML template as `const DATA = <json>;`
4. Embed ECharts library inline (download at build time and embed into HTML) so the file is fully self-contained and works offline. Fallback: if download fails, use CDN `<script>` tag as fallback.
5. Write `munger-dashboard.html`

### Python YAML Parser

Hand-written, handles only the specific format used by `opencli roic financials`:

```yaml
- ticker: DAVE
  statement: income
  fiscalYear: 2019
  item: Sales/Revenue/Turnover
  value: 76
```

Parser logic:
- Line starting with `- ticker:` → new record
- Lines with `  key: value` → set field on current record
- `value: null` → Python None
- `value: <number>` → float
- Accumulate records, group by ticker

### Cross-platform Considerations

- `build.sh` uses `#!/usr/bin/env bash` shebang
- Uses `python3` or `python` (try python3 first, fall back to python)
- Uses `cygpath -w` on Windows for file paths passed to Python
- No external Python packages required
- Output path is relative (`./munger-dashboard.html`)

---

## Visual Theme: Light

- Background: `#f8f9fa`
- Card/panel background: `#ffffff`
- Primary accent: `#1a73e8` (blue)
- Positive/good: `#34a853` (green)
- Warning: `#fbbc04` (yellow)
- Negative/bad: `#ea4335` (red)
- Muted text: `#6c757d`
- Border: `#dee2e6`
- Active tab: blue underline + blue text
- Hover states on rows and buttons

---

## File Structure

```
stock/
├── roic_cache/           # YAML data (existing)
│   ├── DECK.yaml
│   ├── FIZZ.yaml
│   └── ...
├── build.sh              # Build script (new)
├── munger-dashboard.html # Output (new, generated)
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-04-29-munger-dashboard-design.md  # This file
```
