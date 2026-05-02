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

    # Download assets helper
    cache_dir_assets = os.path.join(script_dir, '.cache')
    os.makedirs(cache_dir_assets, exist_ok=True)

    def download_asset(name, url, cache_path):
        if not os.path.exists(cache_path) or os.path.getsize(cache_path) == 0:
            print(f'Downloading {name} from CDN...', file=sys.stderr)
            try:
                import urllib.request
                urllib.request.urlretrieve(url, cache_path)
                print(f'Downloaded: {os.path.getsize(cache_path)} bytes', file=sys.stderr)
            except Exception as e:
                print(f'WARNING: {name} download failed: {e}', file=sys.stderr)
                if os.path.exists(cache_path):
                    os.remove(cache_path)

    def inline_or_cdn(name, cache_path, url, wrap='script'):
        if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
            with open(cache_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f'{name} inline: {os.path.getsize(cache_path)} bytes', file=sys.stderr)
            if wrap == 'script':
                return '<script>' + content + '</script>'
            elif wrap == 'style':
                return '<style>' + content + '</style>'
        print(f'{name} via CDN (download failed)', file=sys.stderr)
        if wrap == 'script':
            return '<script src="' + url + '"></script>'
        elif wrap == 'style':
            return '<link rel="stylesheet" href="' + url + '">'
        return ''

    # ECharts
    echarts_path = os.path.join(cache_dir_assets, 'echarts.min.js')
    echarts_url = 'https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js'
    download_asset('ECharts', echarts_url, echarts_path)
    echarts_script = inline_or_cdn('ECharts', echarts_path, echarts_url, 'script')

    # Popper.js
    popper_path = os.path.join(cache_dir_assets, 'popper.min.js')
    popper_url = 'https://cdn.jsdelivr.net/npm/@popperjs/core@2/dist/umd/popper.min.js'
    download_asset('Popper.js', popper_url, popper_path)
    popper_script = inline_or_cdn('Popper.js', popper_path, popper_url, 'script')

    # Tippy.js
    tippy_path = os.path.join(cache_dir_assets, 'tippy-bundle.umd.min.js')
    tippy_url = 'https://cdn.jsdelivr.net/npm/tippy.js@6/dist/tippy-bundle.umd.min.js'
    download_asset('Tippy.js', tippy_url, tippy_path)
    tippy_script = inline_or_cdn('Tippy.js', tippy_path, tippy_url, 'script')

    # Tippy CSS
    tippy_css_path = os.path.join(cache_dir_assets, 'tippy.css')
    tippy_css_url = 'https://cdn.jsdelivr.net/npm/tippy.js@6/dist/tippy.css'
    download_asset('Tippy CSS', tippy_css_url, tippy_css_path)
    tippy_css = inline_or_cdn('Tippy CSS', tippy_css_path, tippy_css_url, 'style')

    tippy_scripts = popper_script + tippy_script

    # Replace placeholders and write output
    html = template.replace('{{{DATA}}}', data_json)
    html = html.replace('{{{ECHARTS_SCRIPT}}}', echarts_script)
    html = html.replace('{{{TIPPY_SCRIPTS}}}', tippy_scripts)
    html = html.replace('{{{TIPPY_CSS}}}', tippy_css)

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
