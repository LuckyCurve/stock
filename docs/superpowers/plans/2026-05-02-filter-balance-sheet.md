# 自定义筛选面板 + 资产负债结构图 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为汇总排名 tab 添加可折叠的 9 项筛选面板，为深度详情 tab 添加堆叠柱状资产负债结构图（含绝对值/归一化切换）。

**Architecture:** 两个功能完全独立，均只修改 `src/template.html`（CSS + JS），不涉及 Python 端。筛选面板是纯前端过滤逻辑；资产负债图从已有 `raw_data.balance` 提取 4 个时间序列。

**Tech Stack:** 纯 HTML/CSS/JS（已有 ECharts 5）

---

## 文件变更映射

| 文件 | 操作 | 职责 |
|---|---|---|
| `src/template.html` | 修改 | 全部变更：新增 CSS、state 字段、筛选面板 HTML/JS、资产负债图 HTML/JS |
| `munger-dashboard.html` | 重新生成 | `python src/build.py` 的构建产物 |

---

### Task 1: 筛选面板 — CSS 样式

**Files:**
- Modify: `src/template.html` — `<style>` 区块

在 `<style>` 末尾（`/* Scrollbar */` 注释前）添加筛选面板相关 CSS：

- [ ] **Step 1: 添加筛选面板 CSS**

在 `/* Tooltip hint for hover-able labels */` 注释之前插入：

```css
/* Filter panel */
.filter-panel { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px; }
.filter-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.filter-title { font-size: 12px; font-weight: 600; color: #1a73e8; display: flex; align-items: center; gap: 4px; }
.filter-title .badge { width: 6px; height: 6px; border-radius: 50%; background: #1a73e8; display: none; }
.filter-title .badge.active { display: inline-block; }
.filter-reset { font-size: 11px; color: #ea4335; cursor: pointer; border: 1px solid #ea4335; border-radius: 3px; padding: 2px 8px; background: #fff; transition: background 0.15s, color 0.15s; }
.filter-reset:hover { background: #ea4335; color: #fff; }
.filter-body { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: flex-end; }
.filter-item { display: flex; flex-direction: column; gap: 2px; }
.filter-item .filter-label { font-size: 10px; color: #6c757d; }
.filter-item input[type="number"] { width: 60px; padding: 3px 5px; border: 1px solid #dee2e6; border-radius: 3px; font-size: 11px; text-align: right; outline: none; }
.filter-item input[type="number"]:focus { border-color: #1a73e8; box-shadow: 0 0 0 2px rgba(26,115,232,0.15); }
.filter-item input[type="number"].filter-active { border-color: #1a73e8; background: #e8f0fe; color: #1a73e8; font-weight: 600; }
.filter-item select { padding: 3px 5px; border: 1px solid #dee2e6; border-radius: 3px; font-size: 11px; outline: none; }
.filter-item select:focus { border-color: #1a73e8; }
.filter-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 6px; font-size: 11px; color: #6c757d; }
.filter-toggle { font-size: 11px; color: #1a73e8; cursor: pointer; user-select: none; padding: 2px 8px; border: 1px solid #dee2e6; border-radius: 3px; background: #fff; transition: background 0.15s; }
.filter-toggle:hover { background: #e8f0fe; }
.filter-panel.collapsed .filter-body, .filter-panel.collapsed .filter-footer .filter-status { display: none; }
.filter-panel.collapsed .filter-header .filter-title::after { content: ' (' attr(data-count) ')'; font-size: 11px; color: #6c757d; font-weight: 400; }
```

- [ ] **Step 2: Commit**

```bash
git add src/template.html
git commit -m "style: add filter panel CSS classes"
```

---

### Task 2: 筛选面板 — State 初始化与持久化

**Files:**
- Modify: `src/template.html` — JS `<script>` 区块

- [ ] **Step 1: 添加 filters state 字段和常量**

在 `const MAX_COMPARE = 8;` 之后添加：

```js
// Filter state
const FILTER_KEYS = [
  { key: 'n_years', label: 'Yrs ≥', op: 'gte', type: 'number' },
  { key: 'cagr', label: 'CAGR% ≥', op: 'gte', type: 'number' },
  { key: 'eps_cagr', label: 'EPS CAGR% ≥', op: 'gte', type: 'number' },
  { key: 'roic_median', label: 'ROICmed ≥', op: 'gte', type: 'number' },
  { key: 'roic_recent5', label: 'Recent5 ≥', op: 'gte', type: 'number' },
  { key: 'roic_min', label: 'MinROIC ≥', op: 'gte', type: 'number' },
  { key: 'lt10_years', label: '<10y ≤', op: 'lte', type: 'number' },
  { key: 'net_cash_pct', label: 'NetC% ≥', op: 'gte', type: 'number' },
  { key: 'screen_total', label: '芒格筛选', op: 'enum', type: 'select', options: ['全部', '≥3/5', '=5/5'] },
];
const FILTERS_KEY = 'stock-screener-filters';
```

- [ ] **Step 2: 在 state 对象中添加 filters 和 filterCollapsed 字段**

修改 state 初始化，在 `stars: [],` 后面添加两个字段：

```js
  filters: {},
  filterCollapsed: false,
```

- [ ] **Step 3: 添加 filters 持久化函数**

在 `saveStars()` 函数之后添加：

```js
function loadFilters() {
  try {
    const stored = localStorage.getItem(FILTERS_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      // Validate keys against FILTER_KEYS
      for (const fk of FILTER_KEYS) {
        if (parsed[fk.key] !== undefined) {
          state.filters[fk.key] = parsed[fk.key];
        }
      }
    }
  } catch (e) {}
}

function saveFilters() {
  try {
    localStorage.setItem(FILTERS_KEY, JSON.stringify(state.filters));
  } catch (e) {}
}

function resetFilters() {
  state.filters = {};
  saveFilters();
}
```

- [ ] **Step 4: 在 init() 中调用 loadFilters()**

在 `init()` 函数的 `loadStars();` 之后添加：

```js
  loadFilters();
```

- [ ] **Step 5: Commit**

```bash
git add src/template.html
git commit -m "feat: add filter state, constants, and localStorage persistence"
```

---

### Task 3: 筛选面板 — HTML 渲染与交互绑定

**Files:**
- Modify: `src/template.html` — JS `renderSummary()` 函数

- [ ] **Step 1: 添加筛选逻辑函数**

在 `renderSummary()` 函数之前添加：

```js
function applyFilters(rows) {
  return rows.filter(r => {
    for (const fk of FILTER_KEYS) {
      const fv = state.filters[fk.key];
      if (fv === undefined || fv === '' || fv === null) continue;
      const rv = r[fk.key];
      if (rv == null) return false; // null values don't pass any filter
      if (fk.op === 'gte' && rv < Number(fv)) return false;
      if (fk.op === 'lte' && rv > Number(fv)) return false;
      if (fk.op === 'enum') {
        if (fv === '≥3/5' && rv < 3) return false;
        if (fv === '=5/5' && rv !== 5) return false;
      }
    }
    return true;
  });
}

function hasActiveFilters() {
  return Object.values(state.filters).some(v => v !== undefined && v !== '' && v !== null && v !== '全部');
}
```

- [ ] **Step 2: 修改 renderSummary() — 插入筛选面板 HTML**

在 `renderSummary(area)` 函数内部，把现有的 `let rows = [...DATA.summary];` 改为先输出筛选面板再过滤。将函数体替换为：

找到 `let html = '<table>` 这一行，在它之前插入筛选面板渲染代码。具体修改：

将：
```js
function renderSummary(area) {
  let rows = [...DATA.summary];
  const col = state.sortColumn;
  rows.sort((a, b) => {
```

改为：
```js
function renderSummary(area) {
  let allRows = [...DATA.summary];
  const col = state.sortColumn;
  allRows.sort((a, b) => {
```

然后，在 `const arrow = ...` 之前插入：

```js
  // Apply filters
  let rows = applyFilters(allRows);
  const filterPassCount = rows.length;
  const filterTotalCount = allRows.length;

  // Render filter panel
  let filterHtml = '<div class="filter-panel' + (state.filterCollapsed ? ' collapsed' : '') + '">';
  filterHtml += '<div class="filter-header">';
  filterHtml += '<span class="filter-title" data-count="' + filterPassCount + '/' + filterTotalCount + '">🔧' + (hasActiveFilters() ? '<span class="badge active"></span>' : '<span class="badge"></span>') + ' 自定义筛选</span>';
  filterHtml += '<span class="filter-reset" id="filterReset">重置</span>';
  filterHtml += '</div>';
  filterHtml += '<div class="filter-body">';
  for (const fk of FILTER_KEYS) {
    if (fk.type === 'number') {
      const fv = state.filters[fk.key];
      const isActive = fv !== undefined && fv !== '' && fv !== null;
      filterHtml += '<div class="filter-item">';
      filterHtml += '<span class="filter-label">' + fk.label + '</span>';
      filterHtml += '<input type="number" class="filter-input' + (isActive ? ' filter-active' : '') + '" data-key="' + fk.key + '" value="' + (isActive ? fv : '') + '" placeholder="—" />';
      filterHtml += '</div>';
    } else if (fk.type === 'select') {
      const fv = state.filters[fk.key] || '全部';
      filterHtml += '<div class="filter-item">';
      filterHtml += '<span class="filter-label">' + fk.label + '</span>';
      filterHtml += '<select class="filter-input" data-key="' + fk.key + '">';
      for (const opt of fk.options) {
        filterHtml += '<option' + (fv === opt ? ' selected' : '') + '>' + opt + '</option>';
      }
      filterHtml += '</select>';
      filterHtml += '</div>';
    }
  }
  filterHtml += '</div>';
  filterHtml += '<div class="filter-footer">';
  filterHtml += '<span class="filter-status">✅ ' + filterPassCount + '/' + filterTotalCount + ' 通过筛选</span>';
  filterHtml += '<span class="filter-toggle" id="filterToggle">' + (state.filterCollapsed ? '展开 ▼' : '收起 ▲') + '</span>';
  filterHtml += '</div>';
  filterHtml += '</div>';
```

然后将 `let html = '<table>` 改为 `let html = filterHtml + '<table>`。

- [ ] **Step 3: 在 renderSummary() 末尾绑定筛选交互事件**

在现有的 `// Bind sort` 代码块之后（函数末尾 `}` 之前）添加：

```js
  // Bind filter inputs
  let filterTimer = null;
  area.querySelectorAll('.filter-input').forEach(input => {
    const handler = () => {
      const key = input.dataset.key;
      const val = input.value.trim();
      if (val === '' || val === '全部') {
        delete state.filters[key];
      } else {
        state.filters[key] = val;
      }
      saveFilters();
      // Update active class
      input.classList.toggle('filter-active', val !== '' && val !== '全部');
      // Debounce re-render
      clearTimeout(filterTimer);
      filterTimer = setTimeout(() => renderSummary(area), 300);
    };
    input.addEventListener('input', handler);
    input.addEventListener('change', handler);
  });

  // Bind reset
  const resetBtn = document.getElementById('filterReset');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      resetFilters();
      renderSummary(area);
    });
  }

  // Bind toggle collapse
  const toggleBtn = document.getElementById('filterToggle');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      state.filterCollapsed = !state.filterCollapsed;
      renderSummary(area);
    });
  }
```

- [ ] **Step 4: 重新构建仪表盘验证**

```bash
python src/build.py
```

打开 `munger-dashboard.html`，切换到汇总排名 tab，验证：
- 筛选面板出现在表格上方
- 输入数值后表格行实时过滤（300ms debounce）
- 点击「收起 ▲」面板折叠，点击「展开 ▼」恢复
- 点击「重置」清空所有筛选
- 有活跃筛选时标题旁显示蓝色圆点
- 刷新页面后筛选条件从 localStorage 恢复
- 芒格筛选下拉正常工作

- [ ] **Step 5: Commit**

```bash
git add src/template.html munger-dashboard.html
git commit -m "feat: add filter panel to summary tab with 9 criteria"
```

---

### Task 4: 资产负债结构图 — HTML 占位与模式切换 UI

**Files:**
- Modify: `src/template.html` — JS `renderDetail()` 函数

- [ ] **Step 1: 在 renderDetail() 中插入资产负债图 HTML**

在 `renderDetail(area)` 函数中，找到四联图表结束的位置：

```js
  html += '</div>';

  // Munger screen
```

在 `// Munger screen` 之前插入：

```js
  // Capital structure chart
  html += '<div class="chart-box" style="margin-bottom:12px;">';
  html += '<div style="display:flex;justify-content:space-between;align-items:center;">';
  html += '<span class="chart-title">📊 资本结构</span>';
  html += '<div class="stmt-tabs" style="margin-bottom:0;">';
  html += '<div class="stmt-tab' + (state.balanceMode !== 'normalized' ? ' active' : '') + '" data-mode="absolute">绝对值</div>';
  html += '<div class="stmt-tab' + (state.balanceMode === 'normalized' ? ' active' : '') + '" data-mode="normalized">归一化</div>';
  html += '</div>';
  html += '</div>';
  html += '<div id="chartDetailBalance" style="height:250px;"></div>';
  html += '</div>';
```

- [ ] **Step 2: 添加 balanceMode state 字段**

在 state 对象中 `filterCollapsed: false,` 之后添加：

```js
  balanceMode: 'absolute',
```

- [ ] **Step 3: 在 renderDetail() 中绑定模式切换事件**

在 `renderDetail()` 函数中，找到现有的 `// Bind statement tabs` 代码块之前，添加：

```js
  // Bind balance mode tabs
  document.querySelectorAll('[data-mode]').forEach(tab => {
    tab.addEventListener('click', () => {
      state.balanceMode = tab.dataset.mode;
      document.querySelectorAll('[data-mode]').forEach(t2 => t2.classList.toggle('active', t2.dataset.mode === state.balanceMode));
      const t = DATA.tickers.find(x => x.ticker === state.activeTicker);
      if (t) renderDetailBalanceChart(t);
    });
  });
```

- [ ] **Step 4: 在 renderDetail() 的 setTimeout 中添加图表渲染调用**

在 `renderDetail()` 函数末尾的 `setTimeout` 块中，在 `renderDetailEpsYoyChart(t);` 之后添加：

```js
    renderDetailBalanceChart(t);
```

- [ ] **Step 5: Commit**

```bash
git add src/template.html
git commit -m "feat: add capital structure chart placeholder and mode toggle UI"
```

---

### Task 5: 资产负债结构图 — ECharts 渲染逻辑

**Files:**
- Modify: `src/template.html` — JS 区块

- [ ] **Step 1: 实现 renderDetailBalanceChart() 函数**

在 `renderDetailEpsYoyChart()` 函数之后添加：

```js
function renderDetailBalanceChart(t) {
  const dom = document.getElementById('chartDetailBalance');
  if (!dom || typeof echarts === 'undefined') return;

  // Dispose previous instance if exists
  const existingIdx = chartInstances.findIndex(c => c.getDom() === dom);
  if (existingIdx >= 0) {
    chartInstances[existingIdx].dispose();
    chartInstances.splice(existingIdx, 1);
  }

  const chart = echarts.init(dom);
  chartInstances.push(chart);

  const balance = t.raw_data && t.raw_data.balance;
  if (!balance) return;

  // Extract 4 series from balance data
  const equityData = balance['Total Equity'] || {};
  const ltDebtData = balance['+ LT Debt'] || {};
  const stDebtData = balance['+ ST Debt'] || {};
  const cashData = balance['+ Cash & Cash Equivalents'] || {};

  // Collect all years
  const yearsSet = new Set();
  for (const item of [equityData, ltDebtData, stDebtData, cashData]) {
    for (const y of Object.keys(item)) yearsSet.add(parseInt(y));
  }
  const years = Array.from(yearsSet).sort((a, b) => a - b);
  if (years.length === 0) return;

  const isNormalized = state.balanceMode === 'normalized';

  // Build series data arrays
  const equityArr = [];
  const ltDebtArr = [];
  const stDebtArr = [];
  const cashArr = [];

  for (const y of years) {
    const eq = equityData[y] ?? equityData[String(y)] ?? 0;
    const ltd = ltDebtData[y] ?? ltDebtData[String(y)] ?? 0;
    const std = stDebtData[y] ?? stDebtData[String(y)] ?? 0;
    const csh = cashData[y] ?? cashData[String(y)] ?? 0;
    const total = eq + ltd + std + csh;
    if (isNormalized && total > 0) {
      equityArr.push([y, (eq / total * 100).toFixed(2) * 1]);
      ltDebtArr.push([y, (ltd / total * 100).toFixed(2) * 1]);
      stDebtArr.push([y, (std / total * 100).toFixed(2) * 1]);
      cashArr.push([y, (csh / total * 100).toFixed(2) * 1]);
    } else if (!isNormalized) {
      equityArr.push([y, eq]);
      ltDebtArr.push([y, ltd]);
      stDebtArr.push([y, std]);
      cashArr.push([y, csh]);
    }
  }

  const series = [
    { name: '权益', type: 'bar', stack: 'capital', data: equityArr, itemStyle: { color: '#1a73e8' } },
    { name: '长期债', type: 'bar', stack: 'capital', data: ltDebtArr, itemStyle: { color: '#fbbc04' } },
    { name: '短期债', type: 'bar', stack: 'capital', data: stDebtArr, itemStyle: { color: '#ea4335' } },
    { name: '现金', type: 'bar', stack: 'capital', data: cashArr, itemStyle: { color: '#34a853' } },
  ];

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: function(params) {
        if (!params || !params.length) return '';
        const year = params[0].axisValue;
        let tip = '<strong>' + year + '</strong><br/>';
        for (const p of params) {
          if (isNormalized) {
            tip += p.marker + p.seriesName + ': ' + (p.value != null ? p.value.toFixed(1) + '%' : '—') + '<br/>';
          } else {
            tip += p.marker + p.seriesName + ': ' + (p.value != null ? '$' + p.value.toFixed(0) + 'M' : '—') + '<br/>';
          }
        }
        return tip;
      }
    },
    legend: { bottom: 0, textStyle: { fontSize: 10 } },
    grid: { top: 10, right: 15, bottom: 40, left: isNormalized ? 45 : 60 },
    xAxis: { type: 'category', data: years.map(String), axisLabel: { fontSize: 10, rotate: years.length > 20 ? 45 : 0 } },
    yAxis: {
      type: 'value',
      name: isNormalized ? '%' : '$M',
      nameLocation: 'end',
      max: isNormalized ? 100 : undefined,
      min: 0,
      axisLabel: { fontSize: 10, formatter: isNormalized ? v => v + '%' : undefined },
      axisLine: { lineStyle: { color: '#dee2e6' } },
      splitLine: { lineStyle: { color: '#f0f0f0' } }
    },
    series: series,
  });
  if (!_resizeBound) { window.addEventListener('resize', handleResize); _resizeBound = true; }
}
```

- [ ] **Step 2: 重新构建仪表盘验证**

```bash
python src/build.py
```

打开 `munger-dashboard.html`，点击任一 ticker 进入深度详情，验证：
- 资本结构堆叠柱状图出现在四联图表下方
- 4 层颜色正确：蓝（权益）、黄（长期债）、红（短期债）、绿（现金）
- 点击「归一化」切换到百分比模式，Y 轴变为 0-100%
- 点击「绝对值」切回，Y 轴显示 $M
- tooltip 悬停显示具体数值
- 图表正确 resize

- [ ] **Step 3: Commit**

```bash
git add src/template.html munger-dashboard.html
git commit -m "feat: add capital structure stacked bar chart with absolute/normalized toggle"
```

---

### Task 6: 集成验证与最终构建

**Files:**
- Modify: `src/template.html` (如需微调)
- Regenerate: `munger-dashboard.html`

- [ ] **Step 1: 完整功能验证清单**

打开 `munger-dashboard.html`，逐项验证：

**筛选面板：**
- [ ] 面板在汇总排名 tab 表格上方显示
- [ ] 9 个筛选项全部可见且可交互
- [ ] 输入数值后 300ms 内表格行更新
- [ ] 不满足的行被隐藏（非灰显）
- [ ] 底部显示 `✅ N/25 通过筛选`
- [ ] 点击「收起 ▲」面板折叠，折叠后标题显示 `(N/25)`
- [ ] 点击「展开 ▼」恢复
- [ ] 有活跃筛选时标题旁显示蓝色圆点
- [ ] 点击「重置」清空所有筛选
- [ ] 刷新页面后筛选条件恢复
- [ ] 有活跃输入框时边框变蓝色高亮
- [ ] 筛选不影响左侧 ticker 列表和图表对比 tab

**资产负债结构图：**
- [ ] 图表在深度详情四联图下方
- [ ] 4 层堆叠柱状图颜色正确
- [ ] 绝对值模式 Y 轴显示 $M
- [ ] 归一化模式 Y 轴 0-100%
- [ ] 切换按钮样式与 stmt-tab 一致
- [ ] tooltip 显示正确
- [ ] 图表正确 resize

- [ ] **Step 2: 修复发现的问题（如有）**

- [ ] **Step 3: 最终构建与提交**

```bash
python src/build.py
git add src/template.html munger-dashboard.html
git commit -m "feat: filter panel + capital structure chart — final integration"
```
