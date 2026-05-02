# Panel Collapse & Tippy.js Tooltip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add collapsible left panel and replace browser-native `title` tooltips with Tippy.js styled tooltips.

**Architecture:** CSS class toggle for panel collapse with localStorage persistence; Tippy.js + Popper.js downloaded at build time and inlined into the single-file HTML, same pattern as ECharts.

**Tech Stack:** Tippy.js 6, Popper.js 2 (UMD bundles), vanilla CSS/JS

---

### Task 1: Add Tippy.js + Popper.js download to build.py

**Files:**
- Modify: `src/build.py:44-72`

- [ ] **Step 1: Add download helpers for Popper.js, Tippy.js bundle, and Tippy CSS**

In `build.py`, after the ECharts download block (line 57), add a `download_asset` helper function and download 3 more assets. Add `{{{TIPPY_SCRIPTS}}}` and `{{{TIPPY_CSS}}}` placeholders to template replacement.

Replace the section from line 44 to line 72 with:

```python
    # Download assets helper
    cache_dir = os.path.join(script_dir, '.cache')
    os.makedirs(cache_dir, exist_ok=True)

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
    echarts_path = os.path.join(cache_dir, 'echarts.min.js')
    echarts_url = 'https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js'
    download_asset('ECharts', echarts_url, echarts_path)
    echarts_script = inline_or_cdn('ECharts', echarts_path, echarts_url, 'script')

    # Popper.js
    popper_path = os.path.join(cache_dir, 'popper.min.js')
    popper_url = 'https://cdn.jsdelivr.net/npm/@popperjs/core@2/dist/umd/popper.min.js'
    download_asset('Popper.js', popper_url, popper_path)
    popper_script = inline_or_cdn('Popper.js', popper_path, popper_url, 'script')

    # Tippy.js
    tippy_path = os.path.join(cache_dir, 'tippy-bundle.umd.min.js')
    tippy_url = 'https://cdn.jsdelivr.net/npm/tippy.js@6/dist/tippy-bundle.umd.min.js'
    download_asset('Tippy.js', tippy_url, tippy_path)
    tippy_script = inline_or_cdn('Tippy.js', tippy_path, tippy_url, 'script')

    # Tippy CSS
    tippy_css_path = os.path.join(cache_dir, 'tippy.css')
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
```

- [ ] **Step 2: Add `{{{TIPPY_CSS}}}` and `{{{TIPPY_SCRIPTS}}}` placeholders to template.html**

- [ ] **Step 3: Run `python src/build.py` and verify no errors, and that Popper/Tippy/CSS files appear in `.cache/`**

---

### Task 2: Add panel collapse HTML, CSS, and JS

**Files:**
- Modify: `src/template.html` (CSS section + HTML + JS)

- [ ] **Step 1: Add collapse CSS**

After the `.left-panel` rule (line 15), add:

```css
.left-panel.collapsed { width: 32px; overflow: hidden; }
.left-panel.collapsed .panel-header span { display: none; }
.left-panel.collapsed .ticker-filter,
.left-panel.collapsed .ticker-list,
.left-panel.collapsed .verdict-toggle,
.left-panel.collapsed .verdict-body { display: none; }
.panel-toggle { background: none; border: none; cursor: pointer; font-size: 14px; color: #6c757d; padding: 0 2px; line-height: 1; flex-shrink: 0; }
.panel-toggle:hover { color: #1a73e8; }
.left-panel.collapsed .panel-header { justify-content: center; padding: 10px 0; }
.left-panel.collapsed .panel-toggle { font-size: 16px; }
```

Modify `.panel-header` to be flex layout:

```css
.panel-header { padding: 10px 12px; border-bottom: 1px solid #eee; font-size: 11px; color: #6c757d; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; display: flex; align-items: center; justify-content: space-between; }
```

- [ ] **Step 2: Modify left-panel HTML to include toggle button**

Replace:
```html
<div class="panel-header">Tickers (勾选对比 / 点击详情)</div>
```
With:
```html
<div class="panel-header"><span>Tickers (勾选对比 / 点击详情)</span><button class="panel-toggle" id="panelToggle">◀</button></div>
```

- [ ] **Step 3: Add panel collapse state and toggle JS**

Add `panelCollapsed` to state object and load/save from localStorage. Add `togglePanel()` function and bind it in `init()`.

In the state object, add `panelCollapsed: false,`.

Add after the `loadFilters()` function:

```javascript
const PANEL_KEY = 'stock-screener-panel-collapsed';

function loadPanelState() {
  try {
    state.panelCollapsed = localStorage.getItem(PANEL_KEY) === 'true';
  } catch (e) {}
  if (state.panelCollapsed) {
    document.querySelector('.left-panel').classList.add('collapsed');
    document.getElementById('panelToggle').textContent = '▶';
  }
}

function togglePanel() {
  state.panelCollapsed = !state.panelCollapsed;
  const panel = document.querySelector('.left-panel');
  const btn = document.getElementById('panelToggle');
  if (state.panelCollapsed) {
    panel.classList.add('collapsed');
    btn.textContent = '▶';
  } else {
    panel.classList.remove('collapsed');
    btn.textContent = '◀';
  }
  try { localStorage.setItem(PANEL_KEY, String(state.panelCollapsed)); } catch (e) {}
  // Resize charts after panel toggle
  setTimeout(() => { chartInstances.forEach(c => { try { c.resize(); } catch(e) {} }); }, 300);
}
```

In `init()`, add `loadPanelState();` after `loadFilters();`, and add:
```javascript
document.getElementById('panelToggle').addEventListener('click', togglePanel);
```

- [ ] **Step 4: Build and verify panel toggle works**

---

### Task 3: Replace `title` attributes with `data-tippy-content` and initialize Tippy.js

**Files:**
- Modify: `src/template.html` (CSS + 4 JS locations + init)

- [ ] **Step 1: Replace `[title]` CSS rule**

Replace:
```css
[title] { text-decoration: underline dotted #adb5bd; text-underline-offset: 3px; cursor: help; }
```
With:
```css
[data-tippy-content] { text-decoration: underline dotted #adb5bd; text-underline-offset: 3px; cursor: help; }
```

- [ ] **Step 2: Add `{{{TIPPY_CSS}}}` placeholder in `<head>` and `{{{TIPPY_SCRIPTS}}}` before `</head>`**

Add `{{{TIPPY_CSS}}}` right after the `</style>` closing tag, and `{{{TIPPY_SCRIPTS}}}` right before `</head>`.

- [ ] **Step 3: Replace all `title=` with `data-tippy-content=` in JS**

4 locations:

1. Summary table header (line ~613):
   `title="' + c.zh + '"` → `data-tippy-content="' + c.zh + '"`

2. Key ratios table (line ~976):
   `title="' + rk.zh + '"` → `data-tippy-content="' + rk.zh + '"`

3. Munger criterion (line ~1048):
   `title="' + (c.zh || '') + '"` → `data-tippy-content="' + (c.zh || '') + '"`

4. ROIC detail header (line ~1090):
   `title="' + h.zh + '"` → `data-tippy-content="' + h.zh + '"`

- [ ] **Step 4: Add Tippy.js initialization in `init()`**

At the end of `init()`, add:
```javascript
if (typeof tippy === 'function') {
  tippy('[data-tippy-content]', { theme: 'light-border', maxWidth: 280, delay: [200, 0], allowHTML: false });
}
```

Also add a `refreshTooltips()` helper for after dynamic renders:
```javascript
function refreshTooltips() {
  if (typeof tippy === 'function') {
    tippy('[data-tippy-content]', { theme: 'light-border', maxWidth: 280, delay: [200, 0], allowHTML: false });
  }
}
```

Call `refreshTooltips()` at the end of `renderContent()`.

- [ ] **Step 5: Build and verify tooltips work**

Run `python src/build.py`, open `munger-dashboard.html`, hover over summary table headers, ratio labels, munger criteria, and ROIC detail headers to confirm styled tooltips appear.

- [ ] **Step 6: Commit all changes**

```bash
git add src/template.html src/build.py && git commit -m "feat: collapsible left panel and Tippy.js styled tooltips"
```
