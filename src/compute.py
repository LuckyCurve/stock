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
    """Safely get a value from organized data. Year can be int or str."""
    d = data.get(statement, {}).get(item, {})
    if year in d:
        return d[year]
    # Try string key (JSON dict keys are strings)
    if str(year) in d:
        return d[str(year)]
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
    years = sorted(int(y) for y in rev.keys())
    if len(years) < 2:
        return None
    start_val = rev.get(years[0]) if years[0] in rev else rev.get(str(years[0]))
    end_val = rev.get(years[-1]) if years[-1] in rev else rev.get(str(years[-1]))
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
        {'name': 'MinROIC ≥ 10%', 'pass': c1, 'value': min(valid_roics) if valid_roics else None, 'zh': '历史最低 ROIC 是否 ≥ 10%'},
        {'name': '<10y ≤ 3', 'pass': c2, 'value': sum(1 for v in valid_roics if v < 10) if valid_roics else None, 'zh': 'ROIC 低于 10% 的年数是否 ≤ 3'},
        {'name': 'ROICmed ≥ 20%', 'pass': c3, 'value': statistics.median(valid_roics) if valid_roics else None, 'zh': 'ROIC 中位数是否 ≥ 20%'},
        {'name': 'NetC% > 0', 'pass': c4, 'value': net_cash_pct, 'zh': '净现金占总资产比例是否 > 0（正值=净现金企业）'},
        {'name': 'CAGR > 5%', 'pass': c5, 'value': cagr, 'zh': '营收年复合增长率是否 > 5%'},
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
