"""Build script: parse YAML, compute metrics, assemble HTML.
Called by build.sh with script_dir as first argument.
"""

import sys
import json
import os
import pathlib


def main():
    script_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_dir = os.path.join(script_dir, 'src')
    sys.path.insert(0, src_dir)

    from parse import parse_cache_dir
    from compute import compute_all, build_summary, classify_tickers

    # Parse all YAML files
    cache_dir = os.path.join(script_dir, 'roic_cache')
    raw = parse_cache_dir(cache_dir)
    if not raw:
        print("ERROR: No valid YAML files parsed", file=sys.stderr)
        sys.exit(1)
    print(f"Parsed {len(raw)} tickers", file=sys.stderr)

    # Compute all metrics
    results = [compute_all(t) for t in raw]
    summary = build_summary(results)
    classification = classify_tickers(results)
    data = {
        'tickers': results,
        'summary': summary,
        'classification': classification,
    }
    data_json = json.dumps(data, ensure_ascii=False)
    print(f"Computed metrics: {len(data_json)} bytes JSON", file=sys.stderr)

    # Read template
    template_path = os.path.join(script_dir, 'src', 'template.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # Read ECharts
    echarts_path = os.path.join(script_dir, '.cache', 'echarts.min.js')
    echarts_url = 'https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js'
    if os.path.exists(echarts_path) and os.path.getsize(echarts_path) > 0:
        with open(echarts_path, 'r', encoding='utf-8') as f:
            echarts_js = f.read()
        echarts_script = '<script>' + echarts_js + '</script>'
        print(f"ECharts inline: {os.path.getsize(echarts_path)} bytes", file=sys.stderr)
    else:
        echarts_script = '<script src="' + echarts_url + '"></script>'
        print("ECharts via CDN", file=sys.stderr)

    # Replace placeholders and write output
    html = template.replace('{{{DATA}}}', data_json)
    html = html.replace('{{{ECHARTS_SCRIPT}}}', echarts_script)

    output_path = os.path.join(script_dir, 'munger-dashboard.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    size = pathlib.Path(output_path).stat().st_size
    if size > 1048576:
        human = f"{size / 1048576:.1f}MB"
    elif size > 1024:
        human = f"{size / 1024:.1f}KB"
    else:
        human = f"{size}B"
    print(f"Generated {output_path} ({human})")


if __name__ == '__main__':
    main()
