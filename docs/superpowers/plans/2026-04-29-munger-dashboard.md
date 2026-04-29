# Munger Analysis Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained HTML dashboard that reads cached ROIC YAML data, computes Munger-style metrics, and presents them in an interactive left-right split layout.

**Architecture:** `build.sh` reads `roic_cache/*.yaml`, runs an embedded Python script (hand-written YAML parser, zero deps) to parse data and compute all metrics, then embeds the JSON + ECharts + HTML into a single `munger-dashboard.html` file.

**Tech Stack:** Bash, Python 3 (stdlib only), ECharts 5, vanilla HTML/CSS/JS

---

## File Structure

```
stock/
├── build.sh                  # Build script: YAML → JSON → HTML
├── src/
│   ├── parse.py              # Hand-written YAML parser + data organizer
│   ├── compute.py            # ROIC, net cash, CAGR, key ratios, Munger screening
│   └── template.html         # HTML template with CSS + JS (ECharts + interactivity)
├── munger-dashboard.html     # Generated output (do not edit manually)
├── roic_cache/               # Existing YAML data (read-only)
└── docs/superpowers/
    ├── specs/2026-04-29-munger-dashboard-design.md
    └── plans/2026-04-29-munger-dashboard.md   # This file
```

---

### Task 1: Hand-written YAML Parser

**Files:**
- Create: `src/parse.py`

This module parses the specific YAML format produced by `opencli roic financials`. Each record is 5 lines: `- ticker:`, `  statement:`, `  fiscalYear:`, `  item:`, `  value:`.

- [ ] **Step 1: Write the parser module**

```python
# src/parse.py
"""Hand-written YAML parser for opencli roic financials output.
Zero external dependencies. Handles the specific long-format YAML:
  - ticker: DAVE
    statement: income
    fiscalYear: 2019
    item: Sales/Revenue/Turnover
    value: 76
"""

import sys
import os
import json


def parse_file(path):
    """Parse a single YAML file into a dict:
    {ticker: str, data: {statement: {item: {year: value}}}}
    """
    records = []
    cur = {}

    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')

            if line.startswith('- ticker:'):
                if cur:
                    records.append(cur)
                cur = {'ticker': line[len('- ticker:'):].strip()}

            elif line.startswith('  statement:'):
                cur['statement'] = line[len('  statement:'):].strip()

            elif line.startswith('  fiscalYear:'):
                cur['fiscalYear'] = int(line[len('  fiscalYear:'):].strip())

            elif line.startswith('  item:'):
                # Item values may be quoted: '- Cost of Revenue' or '+ Cash & Cash Equivalents'
                raw = line[len('  item:'):].strip()
                # Strip surrounding quotes if present
                if (raw.startswith("'") and raw.endswith("'")) or \
                   (raw.startswith('"') and raw.endswith('"')):
                    raw = raw[1:-1]
                cur['item'] = raw

            elif line.startswith('  value:'):
                raw = line[len('  value:'):].strip()
                if raw == 'null':
                    cur['value'] = None
                else:
                    cur['value'] = float(raw)

    if cur:
        records.append(cur)

    if not records:
        return None

    # Organize: statement -> item -> {year: value}
    ticker = records[0]['ticker']
    data = {}
    for r in records:
        stmt = r['statement']
        item = r['item']
        year = r['fiscalYear']
        val = r['value']
        data.setdefault(stmt, {}).setdefault(item, {})[year] = val

    return {'ticker': ticker, 'data': data}


def parse_cache_dir(cache_dir):
    """Parse all .yaml files in cache_dir, return list of ticker dicts."""
    results = []
    for fname in sorted(os.listdir(cache_dir)):
        if not fname.endswith('.yaml'):
            continue
        path = os.path.join(cache_dir, fname)
        parsed = parse_file(path)
        if parsed:
            results.append(parsed)
    return results


if __name__ == '__main__':
    # When run standalone, parse cache dir and output JSON
    cache_dir = sys.argv[1] if len(sys.argv) > 1 else './roic_cache'
    results = parse_cache_dir(cache_dir)
    print(json.dumps(results, ensure_ascii=False))
```

- [ ] **Step 2: Test the parser against real data**

Run: `python src/parse.py ./roic_cache | python -c "import sys,json; d=json.load(sys.stdin); print(f'Parsed {len(d)} tickers'); [print(f'  {t[\"ticker\"]}: {sum(len(items) for items in t[\"data\"].values())} items') for t in d]"`

Expected: Prints 22 tickers with item counts per ticker (hundreds to thousands each).

- [ ] **Step 3: Commit**

```bash
git add src/parse.py
git commit -m "feat: add hand-written YAML parser for roic_cache data"
```

---

### Task 2: Metrics Computation Module

**Files:**
- Create: `src/compute.py`

Computes all derived metrics from parsed data: ROIC per year, net cash, CAGR, key ratios, Munger screening results.

- [ ] **Step 1: Write the compute module**

```python
# src/compute.py
"""Compute Munger-style metrics from parsed roic_cache data.
All formulas match the design spec exactly.
"""

import statistics
import json
import sys


TAX_RATE = 0.25

# Item name constants — must match roic.ai output exactly
ITEM_REVENUE = 'Sales/Revenue/Turnover'
ITEM_EBIT = 'EBIT'
ITEM_TOTAL_EQUITY = 'Total Equity'
ITEM_LT_DEBT = '+ LT Debt'
ITEM_ST_DEBT = '+ ST Debt'
ITEM_CASH = '+ Cash & Cash Equivalents'
ITEM_TOTAL_ASSETS = 'Total Assets'
ITEM_GROSS_PROFIT = 'Gross Profit'
ITEM_OPERATING_INCOME = 'Operating Income (Loss)'
ITEM_FCF = 'Free Cash Flow'
ITEM_NET_INCOME = 'Net Income, GAAP'
ITEM_CAP_EX = 'Capital Expenditures'
ITEM_CURRENT_RATIO = 'Current Ratio'


def _get(data, statement, item, year, default=None):
    """Safely get a value from organized data."""
    return data.get(statement, {}).get(item, {}).get(year, default)


def _get_latest(data, statement, item, years, default=None):
    """Get the most recent non-None value for an item."""
    for y in reversed(years):
        v = _get(data, statement, item, y)
        if v is not None:
            return v
    return default


def compute_roic_series(data):
    """Compute ROIC for every year that has sufficient data.
    Returns dict {year: roic_percent or None}
    """
    revenue_years = sorted(data.get('income', {}).get(ITEM_REVENUE, {}).keys())
    result = {}
    for y in revenue_years:
        ebit = _get(data, 'income', ITEM_EBIT, y)
        eq = _get(data, 'balance', ITEM_TOTAL_EQUITY, y)
        ltd = _get(data, 'balance', ITEM_LT_DEBT, y) or 0
        std = _get(data, 'balance', ITEM_ST_DEBT, y) or 0
        cash = _get(data, 'balance', ITEM_CASH, y) or 0

        if ebit is None or eq is None:
            result[y] = None
            continue

        ic = eq + ltd + std - cash
        if ic <= 0:
            result[y] = None
            continue

        result[y] = ebit * (1 - TAX_RATE) / ic * 100

    return result


def compute_net_cash(data, year):
    """Compute net cash and NetC% for a given year."""
    ltd = _get(data, 'balance', ITEM_LT_DEBT, year) or 0
    std = _get(data, 'balance', ITEM_ST_DEBT, year) or 0
    cash = _get(data, 'balance', ITEM_CASH, year) or 0
    assets = _get(data, 'balance', ITEM_TOTAL_ASSETS, year) or 0

    net_cash = cash - ltd - std
    net_cash_pct = (net_cash / assets * 100) if assets else None
    return net_cash, net_cash_pct


def compute_cagr(data):
    """Compute Revenue CAGR from first to last year."""
    rev = data.get('income', {}).get(ITEM_REVENUE, {})
    if not rev:
        return None
    years = sorted(rev.keys())
    if len(years) < 2:
        return None
    start_val = rev.get(years[0])
    end_val = rev.get(years[-1])
    n = years[-1] - years[0]
    if start_val is None or end_val is None or start_val <= 0 or end_val <= 0 or n <= 0:
        return None
    return ((end_val / start_val) ** (1 / n) - 1) * 100


def compute_key_ratios(data):
    """Compute key ratios for the most recent year with revenue data."""
    rev_years = sorted(data.get('income', {}).get(ITEM_REVENUE, {}).keys())
    if not rev_years:
        return {}
    y = rev_years[-1]

    revenue = _get(data, 'income', ITEM_REVENUE, y)
    gross_profit = _get(data, 'income', ITEM_GROSS_PROFIT, y)
    op_income = _get(data, 'income', ITEM_OPERATING_INCOME, y)
    fcf = _get(data, 'cashflow', ITEM_FCF, y)
    net_income = _get(data, 'income', ITEM_NET_INCOME, y)
    capex = _get(data, 'cashflow', ITEM_CAP_EX, y)
    current_ratio = _get(data, 'balance', ITEM_CURRENT_RATIO, y)

    ratios = {}
    if revenue and revenue != 0:
        if gross_profit is not None:
            ratios['gross_margin'] = gross_profit / revenue * 100
        if op_income is not None:
            ratios['operating_margin'] = op_income / revenue * 100
        if capex is not None:
            ratios['capex_ratio'] = capex / revenue * 100
    if net_income and net_income != 0 and fcf is not None:
        ratios['fcf_to_ni'] = fcf / net_income
    if current_ratio is not None:
        ratios['current_ratio'] = current_ratio

    ratios['_year'] = y
    return ratios


def compute_roic_detail(data):
    """Year-by-year ROIC calculation detail for verification.
    Returns list of dicts with all intermediate values.
    """
    rev_years = sorted(data.get('income', {}).get(ITEM_REVENUE, {}).keys())
    rows = []
    for y in rev_years:
        revenue = _get(data, 'income', ITEM_REVENUE, y)
        ebit = _get(data, 'income', ITEM_EBIT, y)
        eq = _get(data, 'balance', ITEM_TOTAL_EQUITY, y)
        ltd = _get(data, 'balance', ITEM_LT_DEBT, y)
        std = _get(data, 'balance', ITEM_ST_DEBT, y)
        cash = _get(data, 'balance', ITEM_CASH, y)

        nopat = ebit * (1 - TAX_RATE) if ebit is not None else None
        ic = None
        if eq is not None:
            ic = eq + (ltd or 0) + (std or 0) - (cash or 0)
        roic = None
        if nopat is not None and ic is not None and ic > 0:
            roic = nopat / ic * 100

        rows.append({
            'year': y,
            'revenue': revenue,
            'ebit': ebit,
            'total_equity': eq,
            'lt_debt': ltd,
            'st_debt': std,
            'cash': cash,
            'nopat': nopat,
            'ic': ic,
            'roic': roic,
        })
    return rows


def munger_screen(roic_series, net_cash_pct, cagr):
    """Evaluate 5 Munger screening criteria. Returns dict with pass/fail per criterion + total."""
    valid_roics = [v for v in roic_series.values() if v is not None]

    c1 = min(valid_roics) >= 10 if valid_roics else False
    c2 = sum(1 for v in valid_roics if v < 10) <= 3 if valid_roics else False
    c3 = statistics.median(valid_roics) >= 20 if valid_roics else False
    c4 = net_cash_pct is not None and net_cash_pct > 0
    c5 = cagr is not None and cagr > 5

    criteria = [
        {'name': 'MinROIC ≥ 10%', 'pass': c1, 'value': min(valid_roics) if valid_roics else None},
        {'name': '<10y ≤ 3', 'pass': c2, 'value': sum(1 for v in valid_roics if v < 10) if valid_roics else None},
        {'name': 'ROICmed ≥ 20%', 'pass': c3, 'value': statistics.median(valid_roics) if valid_roics else None},
        {'name': 'NetC% > 0', 'pass': c4, 'value': net_cash_pct},
        {'name': 'CAGR > 5%', 'pass': c5, 'value': cagr},
    ]
    total = sum(1 for c in criteria if c['pass'])
    return {'criteria': criteria, 'total': total}


def compute_all(ticker_data):
    """Compute all metrics for one ticker. Returns comprehensive dict."""
    data = ticker_data['data']
    ticker = ticker_data['ticker']

    # Revenue years (determines data span)
    rev_years = sorted(data.get('income', {}).get(ITEM_REVENUE, {}).keys())
    n_years = len(rev_years)

    # ROIC
    roic_series = compute_roic_series(data)
    valid_roics = [v for v in roic_series.values() if v is not None]

    # Net cash (latest year)
    latest_year = rev_years[-1] if rev_years else None
    net_cash, net_cash_pct = (None, None) if latest_year is None else compute_net_cash(data, latest_year)

    # CAGR
    cagr = compute_cagr(data)

    # Key ratios
    key_ratios = compute_key_ratios(data)

    # ROIC detail
    roic_detail = compute_roic_detail(data)

    # Munger screen
    screen = munger_screen(roic_series, net_cash_pct, cagr)

    # ROIC statistics
    roic_stats = {}
    if valid_roics:
        recent5 = [roic_series.get(y) for y in rev_years[-5:]]
        recent5 = [v for v in recent5 if v is not None]
        roic_stats = {
            'min': min(valid_roics),
            'max': max(valid_roics),
            'mean': statistics.mean(valid_roics),
            'median': statistics.median(valid_roics),
            'stdev': statistics.stdev(valid_roics) if len(valid_roics) > 1 else 0,
            'recent5_mean': statistics.mean(recent5) if recent5 else None,
            'negative_years': sum(1 for v in valid_roics if v < 0),
            'lt10_years': sum(1 for v in valid_roics if v < 10),
            'lt20_years': sum(1 for v in valid_roics if v < 20),
        }

    return {
        'ticker': ticker,
        'n_years': n_years,
        'year_start': rev_years[0] if rev_years else None,
        'year_end': rev_years[-1] if rev_years else None,
        'short_history': n_years < 20,
        'cagr': cagr,
        'roic_median': roic_stats.get('median'),
        'roic_recent5': roic_stats.get('recent5_mean'),
        'roic_min': roic_stats.get('min'),
        'lt10_years': roic_stats.get('lt10_years', 0),
        'net_cash': net_cash,
        'net_cash_pct': net_cash_pct,
        'roic_stats': roic_stats,
        'key_ratios': key_ratios,
        'roic_detail': roic_detail,
        'roic_series': roic_series,
        'munger_screen': screen,
        'raw_data': data,
    }


def build_summary(ticker_results):
    """Build the summary table rows (Mode C) from all ticker results."""
    rows = []
    for t in ticker_results:
        rows.append({
            'ticker': t['ticker'],
            'n_years': t['n_years'],
            'short_history': t['short_history'],
            'cagr': t['cagr'],
            'roic_median': t['roic_median'],
            'roic_recent5': t['roic_recent5'],
            'roic_min': t['roic_min'],
            'lt10_years': t['lt10_years'],
            'net_cash_pct': t['net_cash_pct'],
            'screen_total': t['munger_screen']['total'],
        })
    # Sort by ROIC median descending
    rows.sort(key=lambda x: x['roic_median'] or -999, reverse=True)
    return rows


def classify_tickers(ticker_results):
    """Classify tickers into candidate/edge/eliminated."""
    candidate = []
    edge = []
    eliminated = []
    for t in ticker_results:
        total = t['munger_screen']['total']
        name = t['ticker']
        if total == 5:
            candidate.append(name)
        elif total >= 3:
            edge.append(name)
        else:
            eliminated.append(name)
    return {'candidate': candidate, 'edge': edge, 'eliminated': eliminated}


if __name__ == '__main__':
    # When run standalone, read JSON from stdin (piped from parse.py), compute, output JSON
    raw = json.load(sys.stdin)
    results = [compute_all(t) for t in raw]
    summary = build_summary(results)
    classification = classify_tickers(results)
    output = {
        'tickers': results,
        'summary': summary,
        'classification': classification,
    }
    print(json.dumps(output, ensure_ascii=False))
```

- [ ] **Step 2: Test the compute module end-to-end**

Run: `python src/parse.py ./roic_cache | python src/compute.py | python -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d[\"tickers\"])} tickers computed'); print(f'Classification: {d[\"classification\"]}'); [print(f'  {r[\"ticker\"]}: CAGR={r[\"cagr\"]:.1f}%, ROICmed={r[\"roic_median\"]:.1f}%, NetC%={r[\"net_cash_pct\"]:.1f}%, Screen={r[\"screen_total\"]}/5, ShortHist={r[\"short_history\"]}') for r in d['summary']]"`

Expected: 22 tickers with computed metrics, classification into candidate/edge/eliminated, short_history=True for tickers like DAVE with <20 years.

- [ ] **Step 3: Commit**

```bash
git add src/compute.py
git commit -m "feat: add metrics computation module (ROIC, CAGR, Munger screening)"
```

---

### Task 3: HTML Template — Structure + CSS + Left Panel

**Files:**
- Create: `src/template.html`

This is the HTML template. The build script will replace `{{DATA}}` with JSON and `{{ECHARTS}}` with either inline or CDN ECharts. This task creates the layout shell, CSS theme, and left panel.

- [ ] **Step 1: Write the HTML template with layout, CSS, and left panel**

Create `src/template.html` with the following structure. Key design decisions:
- Left panel: fixed 220px width, full height, scrollable ticker list, verdict at bottom
- Right panel: flex fill, sub-tabs at top, content area below
- All CSS inline (no external files)
- All JS inline
- `{{DATA}}` placeholder for JSON data
- `{{ECHARTS_SCRIPT}}` placeholder for ECharts (inline or CDN)

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Munger Analysis Dashboard</title>
{{{ECHARTS_SCRIPT}}}
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8f9fa; color: #212529; font-size: 13px; }

/* Layout */
.app { display: flex; height: 100vh; overflow: hidden; }
.left-panel { width: 220px; background: #fff; border-right: 1px solid #dee2e6; display: flex; flex-direction: column; flex-shrink: 0; }
.right-panel { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }

/* Top bar */
.top-bar { background: #fff; padding: 10px 20px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #dee2e6; }
.top-bar h1 { font-size: 16px; font-weight: 600; color: #1a73e8; }
.top-bar .meta { font-size: 11px; color: #6c757d; }

/* Left panel */
.panel-header { padding: 10px 12px; border-bottom: 1px solid #eee; font-size: 11px; color: #6c757d; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
.ticker-list { flex: 1; overflow-y: auto; padding: 4px 0; }
.ticker-item { display: flex; align-items: center; padding: 5px 12px; cursor: pointer; transition: background 0.15s; }
.ticker-item:hover { background: #f0f4ff; }
.ticker-item.selected { background: #e8f0fe; }
.ticker-item input[type="checkbox"] { margin-right: 6px; cursor: pointer; accent-color: #1a73e8; }
.ticker-name { flex: 1; font-size: 12px; font-weight: 500; cursor: pointer; }
.ticker-name.active { color: #1a73e8; font-weight: 700; }
.ticker-mini { font-size: 11px; font-weight: 600; min-width: 36px; text-align: right; }
.ticker-warn { color: #fbbc04; font-size: 10px; margin-left: 2px; }
.ticker-years { font-size: 10px; color: #adb5bd; margin-left: 4px; }

/* Verdict */
.verdict { padding: 10px 12px; border-top: 1px solid #eee; font-size: 11px; line-height: 1.6; }
.verdict-candidate { color: #34a853; font-weight: 600; }
.verdict-edge { color: #fbbc04; }
.verdict-eliminated { color: #ea4335; }

/* Sub tabs */
.sub-tabs { display: flex; background: #fff; border-bottom: 1px solid #dee2e6; flex-shrink: 0; }
.sub-tab { padding: 8px 16px; font-size: 12px; color: #6c757d; cursor: pointer; border-bottom: 2px solid transparent; transition: color 0.15s, border-color 0.15s; user-select: none; }
.sub-tab:hover { color: #1a73e8; }
.sub-tab.active { color: #1a73e8; font-weight: 600; border-bottom-color: #1a73e8; }

/* Content area */
.content-area { flex: 1; overflow-y: auto; padding: 16px; }

/* Tables */
table { width: 100%; border-collapse: collapse; }
th { background: #e8f0fe; color: #1a73e8; text-align: left; padding: 6px 8px; font-size: 11px; font-weight: 600; cursor: pointer; user-select: none; white-space: nowrap; }
th:hover { background: #d2e3fc; }
th .sort-arrow { margin-left: 4px; font-size: 10px; }
td { padding: 5px 8px; border-bottom: 1px solid #eee; font-size: 11px; }
tr:hover { background: #f8f9fa; }
tr.highlight { background: #e8f0fe; }

/* Color coding */
.val-good { color: #34a853; font-weight: 600; }
.val-warn { color: #fbbc04; }
.val-bad { color: #ea4335; font-weight: 600; }
.val-null { color: #adb5bd; }

/* Chart containers */
.charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
.chart-box { background: #fff; border: 1px solid #dee2e6; border-radius: 6px; padding: 8px; }
.chart-box .chart-title { font-size: 12px; font-weight: 600; color: #1a73e8; margin-bottom: 4px; padding-left: 4px; }

/* Detail page */
.screen-card { background: #fff; border: 1px solid #dee2e6; border-radius: 6px; padding: 12px; margin-bottom: 12px; }
.screen-criteria { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
.criterion { padding: 8px; border-radius: 4px; text-align: center; font-size: 11px; }
.criterion.pass { background: #e6f4ea; color: #34a853; }
.criterion.fail { background: #fce8e6; color: #ea4335; }
.criterion .c-label { font-weight: 600; margin-bottom: 2px; }
.criterion .c-value { font-size: 13px; font-weight: 700; }

.stats-row { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.stat-chip { background: #fff; border: 1px solid #dee2e6; border-radius: 4px; padding: 6px 10px; font-size: 11px; }
.stat-chip .stat-label { color: #6c757d; }
.stat-chip .stat-value { font-weight: 600; margin-left: 4px; }

/* Warning banner */
.warn-banner { background: #fef7e0; border: 1px solid #fbbc04; border-radius: 4px; padding: 8px 12px; font-size: 12px; color: #e37400; margin-bottom: 12px; }

/* Statement sub-tabs */
.stmt-tabs { display: flex; gap: 4px; margin-bottom: 8px; }
.stmt-tab { padding: 4px 10px; font-size: 11px; border-radius: 3px; cursor: pointer; background: #e8f0fe; color: #1a73e8; }
.stmt-tab.active { background: #1a73e8; color: #fff; }

/* Empty state */
.empty-state { display: flex; align-items: center; justify-content: center; min-height: 200px; color: #adb5bd; font-size: 13px; }

/* Ratios table highlight */
.ratio-best { color: #34a853; font-weight: 700; }
.ratio-worst { color: #ea4335; font-weight: 700; }
</style>
</head>
<body>
<div class="app">
  <!-- Left Panel -->
  <div class="left-panel">
    <div class="panel-header">Tickers（勾选对比 / 点击详情）</div>
    <div class="ticker-list" id="tickerList"></div>
    <div class="verdict" id="verdict"></div>
  </div>

  <!-- Right Panel -->
  <div class="right-panel">
    <div class="top-bar">
      <h1>🧠 Munger Analysis</h1>
      <div class="meta" id="metaInfo"></div>
    </div>
    <div class="sub-tabs" id="subTabs">
      <div class="sub-tab active" data-tab="summary">📊 汇总排名</div>
      <div class="sub-tab" data-tab="compare">📈 图表对比</div>
      <div class="sub-tab" data-tab="detail">🔍 深度详情</div>
    </div>
    <div class="content-area" id="contentArea"></div>
  </div>
</div>

<script>
// ========= DATA =========
const DATA = {{{DATA}}};

// ========= STATE =========
let state = {
  checkedTickers: new Set(),    // multi-select (checkboxes)
  activeTicker: null,           // single-select (click name)
  activeTab: 'summary',        // summary | compare | detail
  sortColumn: 'roic_median',   // summary table sort
  sortAsc: false,              // sort direction
  activeStatement: 'income',   // detail: income | balance | cashflow
};

const MAX_COMPARE = 8;

// ========= INIT =========
function init() {
  renderTickerList();
  renderVerdict();
  renderMetaInfo();
  renderContent();
  bindSubTabs();
}

// ========= LEFT PANEL =========
function renderTickerList() {
  const list = document.getElementById('tickerList');
  list.innerHTML = '';
  for (const t of DATA.summary) {
    const div = document.createElement('div');
    div.className = 'ticker-item' + (state.checkedTickers.has(t.ticker) ? ' selected' : '');

    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = state.checkedTickers.has(t.ticker);
    cb.addEventListener('change', (e) => { e.stopPropagation(); toggleCheck(t.ticker); });

    const name = document.createElement('span');
    name.className = 'ticker-name' + (state.activeTicker === t.ticker ? ' active' : '');
    name.textContent = t.ticker;
    name.addEventListener('click', (e) => { e.stopPropagation(); selectTicker(t.ticker); });

    const mini = document.createElement('span');
    mini.className = 'ticker-mini';
    mini.textContent = t.roic_median != null ? t.roic_median.toFixed(1) : '—';
    mini.style.color = t.roic_median >= 20 ? '#34a853' : t.roic_median >= 10 ? '#fbbc04' : '#ea4335';

    div.appendChild(cb);
    div.appendChild(name);

    if (t.short_history) {
      const warn = document.createElement('span');
      warn.className = 'ticker-warn';
      warn.textContent = '⚠️';
      warn.title = '仅 ' + t.n_years + ' 年数据';
      div.appendChild(warn);
      const yrs = document.createElement('span');
      yrs.className = 'ticker-years';
      yrs.textContent = t.n_years + 'y';
      div.appendChild(yrs);
    }

    div.appendChild(mini);
    list.appendChild(div);
  }
}

function renderVerdict() {
  const el = document.getElementById('verdict');
  const c = DATA.classification;
  el.innerHTML =
    '<div class="verdict-candidate">✅ 候选: ' + (c.candidate.join(', ') || '—') + '</div>' +
    '<div class="verdict-edge">⚠️ 边缘: ' + (c.edge.join(', ') || '—') + '</div>' +
    '<div class="verdict-eliminated">❌ 淘汰: ' + (c.eliminated.join(', ') || '—') + '</div>';
}

function renderMetaInfo() {
  document.getElementById('metaInfo').textContent =
    DATA.tickers.length + ' tickers · roic_cache/';
}

function toggleCheck(ticker) {
  if (state.checkedTickers.has(ticker)) {
    state.checkedTickers.delete(ticker);
  } else {
    if (state.checkedTickers.size >= MAX_COMPARE) {
      alert('最多同时对比 ' + MAX_COMPARE + ' 支股票');
      renderTickerList();
      return;
    }
    state.checkedTickers.add(ticker);
  }
  renderTickerList();
  if (state.activeTab === 'compare') renderContent();
  if (state.activeTab === 'summary') renderContent(); // update highlights
}

function selectTicker(ticker) {
  state.activeTicker = ticker;
  state.activeTab = 'detail';
  renderTickerList();
  setActiveTab('detail');
  renderContent();
}

// ========= SUB TABS =========
function bindSubTabs() {
  document.querySelectorAll('.sub-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      state.activeTab = tab.dataset.tab;
      setActiveTab(tab.dataset.tab);
      renderContent();
    });
  });
}

function setActiveTab(name) {
  document.querySelectorAll('.sub-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === name);
  });
}

// ========= CONTENT ROUTER =========
function renderContent() {
  const area = document.getElementById('contentArea');
  switch (state.activeTab) {
    case 'summary': renderSummary(area); break;
    case 'compare': renderCompare(area); break;
    case 'detail':  renderDetail(area);  break;
  }
}

// ========= SUMMARY TAB =========
function renderSummary(area) {
  let rows = [...DATA.summary];
  // Sort
  const col = state.sortColumn;
  rows.sort((a, b) => {
    let va = a[col], vb = b[col];
    if (va == null) va = -9999;
    if (vb == null) vb = -9999;
    return state.sortAsc ? va - vb : vb - va;
  });

  const arrow = (col) => state.sortColumn === col ? (state.sortAsc ? ' ▲' : ' ▼') : '';
  const cols = [
    {key:'ticker',label:'Ticker'}, {key:'n_years',label:'Yrs'}, {key:'cagr',label:'CAGR%'},
    {key:'roic_median',label:'ROICmed'}, {key:'roic_recent5',label:'Recent5'},
    {key:'roic_min',label:'MinROIC'}, {key:'lt10_years',label:'<10y'},
    {key:'net_cash_pct',label:'NetC%'}, {key:'screen_total',label:'✅'}
  ];

  let html = '<table><thead><tr>';
  for (const c of cols) {
    html += '<th data-col="' + c.key + '">' + c.label + '<span class="sort-arrow">' + arrow(c.key) + '</span></th>';
  }
  html += '</tr></thead><tbody>';

  for (const r of rows) {
    const hl = state.checkedTickers.has(r.ticker) ? ' class="highlight"' : '';
    const warn = r.short_history ? ' ⚠️' : '';
    const yrsStyle = r.short_history ? ' style="color:#adb5bd"' : '';
    const fmt = (v, d=1) => v != null ? v.toFixed(d) : '<span class="val-null">—</span>';
    const colorVal = (v, good, bad) => {
      if (v == null) return '<span class="val-null">—</span>';
      return v >= good ? '<span class="val-good">' + v.toFixed(1) + '</span>' :
             v <= bad ? '<span class="val-bad">' + v.toFixed(1) + '</span>' :
             v.toFixed(1);
    };

    html += '<tr' + hl + '>';
    html += '<td><strong>' + r.ticker + '</strong>' + warn + '</td>';
    html += '<td' + yrsStyle + '>' + r.n_years + '</td>';
    html += '<td>' + fmt(r.cagr) + '</td>';
    html += '<td>' + colorVal(r.roic_median, 20, 0) + '</td>';
    html += '<td>' + colorVal(r.roic_recent5, 20, 0) + '</td>';
    html += '<td>' + colorVal(r.roic_min, 10, 0) + '</td>';
    html += '<td>' + r.lt10_years + '</td>';
    html += '<td>' + colorVal(r.net_cash_pct, 0, -20) + '</td>';
    html += '<td>' + r.screen_total + '/5</td>';
    html += '</tr>';
  }
  html += '</tbody></table>';
  area.innerHTML = html;

  // Bind sort
  area.querySelectorAll('th').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.dataset.col;
      if (state.sortColumn === col) state.sortAsc = !state.sortAsc;
      else { state.sortColumn = col; state.sortAsc = col === 'ticker'; }
      renderSummary(area);
    });
  });
}

// ========= COMPARE TAB =========
function renderCompare(area) {
  const selected = Array.from(state.checkedTickers);
  if (selected.length === 0) {
    area.innerHTML = '<div class="empty-state">请在左侧勾选 ticker 进行对比</div>';
    return;
  }

  const tickers = selected.map(t => DATA.tickers.find(x => x.ticker === t)).filter(Boolean);
  if (tickers.length === 0) return;

  let html = '<div class="charts-grid">';
  html += '<div class="chart-box"><div class="chart-title">ROIC 时序折线图</div><div id="chartRoic" style="height:280px;"></div></div>';
  html += '<div class="chart-box"><div class="chart-title">营收/EBIT 增长曲线</div><div id="chartGrowth" style="height:280px;"></div></div>';
  html += '<div class="chart-box"><div class="chart-title">关键指标柱状图</div><div id="chartBar" style="height:280px;"></div></div>';
  html += '<div class="chart-box"><div class="chart-title">雷达图（多维对比）</div><div id="chartRadar" style="height:280px;"></div></div>';
  html += '</div>';

  // Key ratios table
  html += renderRatiosTable(tickers);

  area.innerHTML = html;

  // Render charts after DOM update
  setTimeout(() => {
    renderRoicChart(tickers);
    renderGrowthChart(tickers);
    renderBarChart(tickers);
    renderRadarChart(tickers);
  }, 50);
}

const CHART_COLORS = ['#1a73e8','#34a853','#ea4335','#fbbc04','#9c27b0','#00bcd4','#ff5722','#607d8b'];

function renderRoicChart(tickers) {
  const dom = document.getElementById('chartRoic');
  if (!dom || typeof echarts === 'undefined') return;
  const chart = echarts.init(dom);
  const series = tickers.map((t, i) => ({
    name: t.ticker,
    type: 'line',
    data: Object.entries(t.roic_series).map(([y,v]) => [parseInt(y), v]),
    connectNulls: false,
    itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] },
  }));
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, textStyle: { fontSize: 10 } },
    grid: { top: 10, right: 20, bottom: 40, left: 50 },
    xAxis: { type: 'value', name: 'Year', nameLocation: 'center', nameGap: 25 },
    yAxis: { type: 'value', name: 'ROIC%', nameLocation: 'end',
      axisLine: { lineStyle: { color: '#dee2e6' } },
      splitLine: { lineStyle: { color: '#f0f0f0' } }
    },
    series: series,
    markLine: {
      silent: true,
      data: [
        { yAxis: 10, lineStyle: { color: '#fbbc04', type: 'dashed' }, label: { formatter: '10%', fontSize: 10 } },
        { yAxis: 20, lineStyle: { color: '#34a853', type: 'dashed' }, label: { formatter: '20%', fontSize: 10 } },
      ]
    }
  });
  window.addEventListener('resize', () => chart.resize());
}

function renderGrowthChart(tickers) {
  const dom = document.getElementById('chartGrowth');
  if (!dom || typeof echarts === 'undefined') return;
  const chart = echarts.init(dom);
  const series = [];
  tickers.forEach((t, i) => {
    const rev = t.raw_data.income?.['Sales/Revenue/Turnover'] || {};
    const ebit = t.raw_data.income?.['EBIT'] || {};
    series.push({
      name: t.ticker + ' Revenue',
      type: 'line',
      data: Object.entries(rev).map(([y,v]) => [parseInt(y), v]),
      itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] },
    });
    series.push({
      name: t.ticker + ' EBIT',
      type: 'line',
      lineStyle: { type: 'dashed' },
      data: Object.entries(ebit).map(([y,v]) => v != null ? [parseInt(y), v] : [parseInt(y), null]).filter(x => x[1] !== null),
      itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length], opacity: 0.6 },
    });
  });
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, textStyle: { fontSize: 9 }, type: 'scroll' },
    grid: { top: 10, right: 20, bottom: 40, left: 60 },
    xAxis: { type: 'value', name: 'Year', nameLocation: 'center', nameGap: 25 },
    yAxis: { type: 'log', name: '$M (log)', nameLocation: 'end',
      axisLine: { lineStyle: { color: '#dee2e6' } },
      splitLine: { lineStyle: { color: '#f0f0f0' } }
    },
    series: series,
  });
  window.addEventListener('resize', () => chart.resize());
}

function renderBarChart(tickers) {
  const dom = document.getElementById('chartBar');
  if (!dom || typeof echarts === 'undefined') return;
  const chart = echarts.init(dom);
  const names = tickers.map(t => t.ticker);
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, textStyle: { fontSize: 10 } },
    grid: { top: 10, right: 20, bottom: 40, left: 50 },
    xAxis: { type: 'category', data: names },
    yAxis: { type: 'value',
      axisLine: { lineStyle: { color: '#dee2e6' } },
      splitLine: { lineStyle: { color: '#f0f0f0' } }
    },
    series: [
      { name: 'NetC%', type: 'bar', data: tickers.map(t => t.net_cash_pct), itemStyle: { color: '#34a853' } },
      { name: 'ROICmed', type: 'bar', data: tickers.map(t => t.roic_median), itemStyle: { color: '#1a73e8' } },
      { name: 'MinROIC', type: 'bar', data: tickers.map(t => t.roic_min), itemStyle: { color: '#ea4335' } },
    ],
  });
  window.addEventListener('resize', () => chart.resize());
}

function renderRadarChart(tickers) {
  const dom = document.getElementById('chartRadar');
  if (!dom || typeof echarts === 'undefined') return;
  const chart = echarts.init(dom);
  const indicators = [
    { name: 'ROIC 稳定性', max: 100 },
    { name: '增长', max: 100 },
    { name: '净现金', max: 100 },
    { name: 'FCF 质量', max: 100 },
    { name: '轻资产度', max: 100 },
  ];
  const series = tickers.map((t, i) => {
    const n_years = t.n_years || 1;
    const bad_yrs = t.lt10_years || 0;
    const stability = Math.max(0, 100 - (bad_yrs / n_years * 100));
    const growth = Math.min(100, (t.cagr || 0) * 5);
    const netCash = Math.min(100, Math.max(0, (t.net_cash_pct || 0) + 20));
    const fcfNi = t.key_ratios.fcf_to_ni;
    const fcfQuality = Math.min(100, (fcfNi != null ? Math.max(0, fcfNi) * 80 : 50));
    const capexRatio = t.key_ratios.capex_ratio;
    const lightAsset = Math.min(100, Math.max(0, capexRatio != null ? 100 - capexRatio * 5 : 50));
    return {
      name: t.ticker,
      type: 'radar',
      data: [{ value: [stability, growth, netCash, fcfQuality, lightAsset], name: t.ticker }],
      itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] },
      areaStyle: { opacity: 0.15 },
    };
  });
  chart.setOption({
    tooltip: {},
    legend: { bottom: 0, textStyle: { fontSize: 10 } },
    radar: { indicator: indicators, radius: '60%', splitArea: { areaStyle: { color: ['rgba(26,115,232,0.02)','rgba(26,115,232,0.04)'] } } },
    series: series,
  });
  window.addEventListener('resize', () => chart.resize());
}

function renderRatiosTable(tickers) {
  const ratioKeys = [
    { key: 'gross_margin', label: 'Gross Margin %' },
    { key: 'operating_margin', label: 'Operating Margin %' },
    { key: 'fcf_to_ni', label: 'FCF / Net Income' },
    { key: 'capex_ratio', label: 'CapEx / Revenue %' },
    { key: 'current_ratio', label: 'Current Ratio' },
  ];
  let html = '<table><thead><tr><th>指标</th>';
  for (const t of tickers) html += '<th>' + t.ticker + '</th>';
  html += '</tr></thead><tbody>';

  for (const rk of ratioKeys) {
    html += '<tr><td>' + rk.label + '</td>';
    const vals = tickers.map(t => t.key_ratios[rk.key]);
    // Find best/worst (higher is better for all except capex_ratio)
    const nonNull = vals.filter(v => v != null);
    const isLowerBetter = rk.key === 'capex_ratio';
    let bestVal = null, worstVal = null;
    if (nonNull.length > 1) {
      bestVal = isLowerBetter ? Math.min(...nonNull) : Math.max(...nonNull);
      worstVal = isLowerBetter ? Math.max(...nonNull) : Math.min(...nonNull);
    }
    for (const v of vals) {
      if (v == null) {
        html += '<td class="val-null">—</td>';
      } else {
        let cls = '';
        if (bestVal != null && v === bestVal) cls = ' class="ratio-best"';
        else if (worstVal != null && v === worstVal) cls = ' class="ratio-worst"';
        const fmt = rk.key === 'current_ratio' || rk.key === 'fcf_to_ni' ? v.toFixed(2) : v.toFixed(1);
        html += '<td' + cls + '>' + fmt + '</td>';
      }
    }
    html += '</tr>';
  }
  html += '</tbody></table>';
  return html;
}

// ========= DETAIL TAB =========
function renderDetail(area) {
  if (!state.activeTicker) {
    area.innerHTML = '<div class="empty-state">请在左侧点击 ticker 名查看详情</div>';
    return;
  }
  const t = DATA.tickers.find(x => x.ticker === state.activeTicker);
  if (!t) return;

  let html = '';

  // Warning banner
  if (t.short_history) {
    html += '<div class="warn-banner">⚠️ ' + t.ticker + ' 仅有 ' + t.n_years + ' 年数据（建议 ≥20 年），结论可靠性受限</div>';
  }

  // Munger screen
  html += '<div class="screen-card"><h3 style="margin-bottom:8px;font-size:13px;color:#1a73e8;">芒格筛选</h3>';
  html += '<div class="screen-criteria">';
  for (const c of t.munger_screen.criteria) {
    html += '<div class="criterion ' + (c.pass ? 'pass' : 'fail') + '">';
    html += '<div class="c-label">' + (c.pass ? '✅' : '❌') + ' ' + c.name + '</div>';
    html += '<div class="c-value">' + (c.value != null ? (typeof c.value === 'number' ? c.value.toFixed(1) : c.value) : '—') + '</div>';
    html += '</div>';
  }
  html += '</div></div>';

  // Stats
  const s = t.roic_stats;
  if (s && Object.keys(s).length > 0) {
    html += '<div class="stats-row">';
    const chips = [
      ['Min', s.min], ['Max', s.max], ['Mean', s.mean], ['Median', s.median],
      ['Stdev', s.stdev], ['负值年', s.negative_years], ['<10%年', s.lt10_years], ['<20%年', s.lt20_years],
    ];
    for (const [label, val] of chips) {
      html += '<div class="stat-chip"><span class="stat-label">' + label + '</span><span class="stat-value">' + (val != null ? (typeof val === 'number' ? val.toFixed(1) : val) : '—') + '</span></div>';
    }
    html += '</div>';
  }

  // ROIC detail table
  html += '<div class="screen-card"><h3 style="margin-bottom:8px;font-size:13px;color:#1a73e8;">ROIC 计算明细（逐年验证）</h3>';
  html += '<div style="overflow-x:auto;"><table><thead><tr>';
  html += '<th>Year</th><th>Revenue</th><th>EBIT</th><th>Total Equity</th><th>LT Debt</th><th>ST Debt</th><th>Cash</th><th>NOPAT</th><th>IC</th><th>ROIC%</th>';
  html += '</tr></thead><tbody>';
  for (const r of t.roic_detail) {
    const f = (v) => v != null ? v.toFixed(0) : '<span class="val-null">—</span>';
    let roicClass = 'val-null';
    if (r.roic != null) roicClass = r.roic >= 20 ? 'val-good' : r.roic >= 10 ? '' : r.roic < 0 ? 'val-bad' : 'val-warn';
    const roicVal = r.roic != null ? '<span class="' + roicClass + '">' + r.roic.toFixed(1) + '</span>' : '<span class="val-null">—</span>';
    html += '<tr><td>' + r.year + '</td><td>' + f(r.revenue) + '</td><td>' + f(r.ebit) + '</td><td>' + f(r.total_equity) + '</td><td>' + f(r.lt_debt) + '</td><td>' + f(r.st_debt) + '</td><td>' + f(r.cash) + '</td><td>' + f(r.nopat) + '</td><td>' + f(r.ic) + '</td><td>' + roicVal + '</td></tr>';
  }
  html += '</tbody></table></div></div>';

  // Three statements
  html += '<div class="screen-card"><h3 style="margin-bottom:8px;font-size:13px;color:#1a73e8;">三大报表原始数据</h3>';
  html += '<div class="stmt-tabs" id="stmtTabs">';
  for (const s of ['income','balance','cashflow']) {
    html += '<div class="stmt-tab' + (state.activeStatement === s ? ' active' : '') + '" data-stmt="' + s + '">' + s.charAt(0).toUpperCase() + s.slice(1) + '</div>';
  }
  html += '</div>';
  html += '<div id="stmtContent"></div></div>';

  area.innerHTML = html;

  // Bind statement tabs
  document.querySelectorAll('.stmt-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      state.activeStatement = tab.dataset.stmt;
      document.querySelectorAll('.stmt-tab').forEach(t => t.classList.toggle('active', t.dataset.stmt === state.activeStatement));
      renderStatement(t);
    });
  });
  renderStatement(t);
}

function renderStatement(t) {
  const el = document.getElementById('stmtContent');
  if (!el) return;
  const stmt = state.activeStatement;
  const stmtData = t.raw_data[stmt];
  if (!stmtData) { el.innerHTML = '<div class="empty-state">无数据</div>'; return; }

  const items = Object.keys(stmtData);
  if (items.length === 0) { el.innerHTML = '<div class="empty-state">无数据</div>'; return; }

  // Get all years
  const yearsSet = new Set();
  for (const item of items) {
    for (const y of Object.keys(stmtData[item])) yearsSet.add(parseInt(y));
  }
  const years = Array.from(yearsSet).sort((a,b) => b-a);

  let html = '<div style="overflow-x:auto;"><table><thead><tr><th>Item</th>';
  for (const y of years) html += '<th>' + y + '</th>';
  html += '</tr></thead><tbody>';

  for (const item of items) {
    html += '<tr><td>' + item + '</td>';
    for (const y of years) {
      const v = stmtData[item][y];
      html += '<td>' + (v != null ? v.toFixed(0) : '<span class="val-null">—</span>') + '</td>';
    }
    html += '</tr>';
  }
  html += '</tbody></table></div>';
  el.innerHTML = html;
}

// ========= BOOT =========
document.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>
```

- [ ] **Step 2: Verify template renders with placeholder data**

Manually replace `{{{DATA}}}` with a small JSON and `{{{ECHARTS_SCRIPT}}}` with a CDN script tag, open in browser to verify layout renders correctly. This step is informal — the build script in Task 5 will do the full integration test.

- [ ] **Step 3: Commit**

```bash
git add src/template.html
git commit -m "feat: add HTML template with layout, CSS, left panel, and all JS"
```

---

### Task 4: Build Script

**Files:**
- Create: `build.sh`

The build script orchestrates: parse YAML → compute metrics → download ECharts → assemble HTML.

- [ ] **Step 1: Write build.sh**

```bash
#!/usr/bin/env bash
# build.sh — Generate munger-dashboard.html from roic_cache/ YAML data
# Usage: bash build.sh
# Output: ./munger-dashboard.html
# Requires: Python 3 (stdlib only), curl or wget (for ECharts download)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CACHE_DIR="$SCRIPT_DIR/roic_cache"
OUTPUT="$SCRIPT_DIR/munger-dashboard.html"
TEMPLATE="$SCRIPT_DIR/src/template.html"
ECHARTS_CACHE="$SCRIPT_DIR/.cache/echarts.min.js"
ECHARTS_URL="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"

# Detect Python
PYTHON=""
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "ERROR: Python 3 not found" >&2
    exit 1
fi

# Check cache dir
if [ ! -d "$CACHE_DIR" ]; then
    echo "ERROR: $CACHE_DIR not found" >&2
    exit 1
fi

yaml_count=$(find "$CACHE_DIR" -name "*.yaml" | wc -l | tr -d ' ')
echo "Found $yaml_count YAML files in $CACHE_DIR"

# Step 1: Parse + Compute
echo "Parsing YAML and computing metrics..."
# Build file list with absolute Windows paths on Git Bash, or normal paths on macOS/Linux
FILE_ARGS=""
for f in "$CACHE_DIR"/*.yaml; do
    [ -s "$f" ] || continue
    if [[ "${OSTYPE:-}" == msys* || "${OSTYPE:-}" == cygwin* || "${OSTYPE:-}" == mingw* || -n "${MSYSTEM:-}" ]]; then
        FILE_ARGS="$FILE_ARGS $(cygpath -w "$f")"
    else
        FILE_ARGS="$FILE_ARGS $f"
    fi
done

DATA_JSON=$($PYTHON -c "
import sys, json, os
sys.path.insert(0, os.path.join(r'$(cygpath -w "$SCRIPT_DIR" 2>/dev/null || echo "$SCRIPT_DIR")', 'src'))
from parse import parse_file
from compute import compute_all, build_summary, classify_tickers

files = '''$FILE_ARGS'''.split()
raw = [parse_file(f) for f in files if f]
raw = [r for r in raw if r is not None]
results = [compute_all(t) for t in raw]
summary = build_summary(results)
classification = classify_tickers(results)
output = {
    'tickers': results,
    'summary': summary,
    'classification': classification,
}
print(json.dumps(output, ensure_ascii=False))
" 2>&1)

if [ $? -ne 0 ]; then
    echo "ERROR: Python computation failed" >&2
    echo "$DATA_JSON" >&2
    exit 1
fi

DATA_SIZE=$(echo "$DATA_JSON" | wc -c | tr -d ' ')
echo "Computed metrics: ${DATA_SIZE} bytes JSON"

# Step 2: Download ECharts (cached)
echo "Preparing ECharts..."
mkdir -p "$(dirname "$ECHARTS_CACHE")"
if [ ! -s "$ECHARTS_CACHE" ]; then
    echo "Downloading ECharts from CDN..."
    if command -v curl &>/dev/null; then
        curl -sL "$ECHARTS_URL" -o "$ECHARTS_CACHE"
    elif command -v wget &>/dev/null; then
        wget -q "$ECHARTS_URL" -O "$ECHARTS_CACHE"
    else
        echo "WARNING: No curl/wget, will use CDN fallback" >&2
    fi
fi

if [ -s "$ECHARTS_CACHE" ]; then
    ECHARTS_SCRIPT='<script>'"$(cat "$ECHARTS_CACHE")"'</script>'
    echo "ECharts embedded inline ($(wc -c < "$ECHARTS_CACHE" | tr -d ' ') bytes)"
else
    ECHARTS_SCRIPT='<script src="'"$ECHARTS_URL"'"></script>'
    echo "ECharts via CDN (download failed)"
fi

# Step 3: Assemble HTML
echo "Assembling HTML..."
TEMPLATE_CONTENT=$(cat "$TEMPLATE")

# Replace placeholders — use Python for safe JSON embedding
FINAL_HTML=$($PYTHON -c "
import sys, json

template = '''$(cat "$TEMPLATE")'''
data_json = json.dumps(json.loads(sys.stdin.read()), ensure_ascii=False)
echarts_script = '''$ECHARTS_SCRIPT'''

html = template.replace('{{{DATA}}}', data_json)
html = html.replace('{{{ECHARTS_SCRIPT}}}', echarts_script)
sys.stdout.write(html)
" <<< "$DATA_JSON")

echo "$FINAL_HTML" > "$OUTPUT"
OUTPUT_SIZE=$(wc -c < "$OUTPUT" | tr -d ' ')
echo "✅ Generated $OUTPUT ($OUTPUT_SIZE bytes)"
```

- [ ] **Step 2: Test build script**

Run: `bash build.sh`

Expected: Generates `munger-dashboard.html` in the project root, prints progress messages and final file size.

- [ ] **Step 3: Open the generated HTML in a browser and verify**

Open `munger-dashboard.html` in browser. Check:
1. Left panel shows 22 tickers with color-coded ROIC median
2. DAVE shows ⚠️ (only 7 years)
3. 汇总排名 tab shows sortable table
4. Check a few tickers, click 图表对比 — charts render
5. Click a ticker name — 深度详情 tab opens with ROIC detail table
6. Statement sub-tabs show raw data

- [ ] **Step 4: Commit**

```bash
git add build.sh
git commit -m "feat: add build script to generate munger-dashboard.html"
```

---

### Task 5: Integration Test + Polish

**Files:**
- Modify: `src/template.html` (fix any issues found)
- Modify: `build.sh` (fix any issues found)

- [ ] **Step 1: Full end-to-end test**

Run: `bash build.sh && echo "Build OK"`

Open `munger-dashboard.html` in browser. Systematically verify every feature:

1. **Left panel**: ticker list renders, checkboxes work, clicking name activates detail tab, ⚠️ shows on short-history tickers, verdict section at bottom
2. **汇总排名**: table sorts on column click, checked tickers highlighted, all values reasonable
3. **图表对比**: check 2-3 tickers, all 4 charts render, key ratios table shows with color coding
4. **深度详情**: click a ticker name, ROIC detail table shows, Munger screen card shows pass/fail, stats chips display, statement tabs switch between Income/Balance/Cashflow, raw data shows
5. **Edge cases**: uncheck all → empty state in compare tab; no ticker selected → empty state in detail tab; check 9 tickers → alert about max 8

- [ ] **Step 2: Fix any rendering or data issues found**

Common issues to check:
- Null values displaying correctly as "—"
- Negative ROIC values colored red
- Statement data for all three types
- Chart resize on window resize
- Sort toggle direction

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete Munger Analysis Dashboard v1"
```

---

## Spec Coverage Check

| Spec Requirement | Task |
|---|---|
| Left-right split layout | Task 3 (template) |
| Light theme CSS | Task 3 (template) |
| Ticker list with checkbox + click | Task 3 (template) |
| Multi-select max 8 | Task 3 (template) |
| Single-select for detail | Task 3 (template) |
| <20 years ⚠️ flag | Task 2 (compute), Task 3 (template) |
| Munger screening verdict | Task 2 (compute), Task 3 (template) |
| 📊 汇总排名 sortable table | Task 3 (template) |
| 📈 ROIC 折线图 | Task 3 (template) |
| 📈 增长曲线 semi-log | Task 3 (template) |
| 📈 柱状图 | Task 3 (template) |
| 📈 雷达图 | Task 3 (template) |
| Key ratios comparison table | Task 3 (template) |
| 🔍 Munger screen card | Task 3 (template) |
| 🔍 ROIC detail table | Task 3 (template) |
| 🔍 Statistics summary | Task 3 (template) |
| 🔍 Three statements | Task 3 (template) |
| ROIC formula (EBIT*(1-25%)/IC) | Task 2 (compute) |
| Net cash computation | Task 2 (compute) |
| CAGR computation | Task 2 (compute) |
| Key ratios computation | Task 2 (compute) |
| Munger 5 criteria | Task 2 (compute) |
| Hand-written YAML parser | Task 1 (parse.py) |
| build.sh cross-platform | Task 4 (build.sh) |
| ECharts inline + CDN fallback | Task 4 (build.sh) |
| Self-contained HTML output | Task 4 (build.sh) |
