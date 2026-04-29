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
