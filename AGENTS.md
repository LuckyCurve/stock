# 股票筛选器

芒格式长期投资分析可视化工具。基于 `roic_cache/` 中的 roic.ai 财报 YAML 数据，计算 ROIC、净现金、CAGR 等核心指标，生成自包含的 HTML 仪表盘，支持横向对比与深度验证。

## 快速开始

```bash
# 1. 抓取财报数据（双击 scripts/fetch.bat 或终端运行）
python src/fetch.py
# 交互式输入 ticker，如: AAPL MSFT GOOGL

# 2. 构建仪表盘（双击 scripts/build.bat 或终端运行）
python src/build.py

# 3. 打开生成的文件
# munger-dashboard.html
```

## ⚠️ 修改须知

- **修改页面样式或交互** → 改 `src/template.html`，然后重新 `python src/build.py`
- **修改指标计算逻辑** → 改 `src/compute.py`
- **修改数据解析** → 改 `src/parse.py`
- **不要直接编辑 `munger-dashboard.html`**，它是构建产物，下次构建会被覆盖

## 项目结构

```
stock/
├── scripts/
│   ├── fetch.bat          # Windows 双击抓取入口
│   └── build.bat          # Windows 双击构建入口
├── src/
│   ├── fetch.py           # 交互式抓取脚本（opencli roic financials）
│   ├── build.py           # 构建脚本：解析 YAML → 计算指标 → 嵌入 HTML
│   ├── parse.py           # 手写 YAML 解析器（零依赖，仅支持 roic.ai 格式）
│   ├── compute.py         # 指标计算：ROIC、CAGR、净现金、芒格筛选、关键比率
│   └── template.html      # HTML 模板（布局 + CSS + JS + ECharts）
├── munger-dashboard.html  # 构建产物（自包含，可直接打开）
├── roic_cache/            # 财报数据缓存（YAML，由 opencli roic financials 抓取）
├── .cache/                # ECharts 缓存（构建时自动下载）
├── .gitignore             # Git 忽略规则（缓存、构建产物等）
└── docs/
    └── superpowers/
        ├── specs/         # 设计文档
        └── plans/         # 实施计划
```

## 数据源

- **工具**: `opencli roic financials <TICKER>`
- **来源**: roic.ai，免费 tier，DOM 抓取
- **格式**: long-format YAML，每条记录 `{ticker, statement, fiscalYear, item, value}`
- **单位**: 百万美元，`null` 表示数据缺失
- **覆盖**: 三大报表（Income / Balance / Cashflow），年度数据
- **缓存**: 已抓取的 ticker 自动跳过，存放在 `roic_cache/<TICKER>.yaml`

## 核心指标

| 指标 | 公式 |
|------|------|
| ROIC | EBIT × (1 - 25%) / (Total Equity + LT Debt + ST Debt - Cash) |
| 净现金 | Cash - LT Debt - ST Debt |
| NetC% | 净现金 / Total Assets × 100 |
| CAGR | (末年 Revenue / 首年 Revenue)^(1/年数) - 1 |
| EPS CAGR | (首年正EPS / 末年正EPS)^(1/年数) - 1，口径 fallback: Diluted Cont Ops → Diluted GAAP → Basic Cont Ops → Basic GAAP |

## 芒格筛选（5 项）

1. MinROIC ≥ 10%（穿越周期底线）
2. ROIC < 10% 的年数 ≤ 3（稳定性）
3. ROIC 中位数 ≥ 20%（长期质量）
4. NetC% > 0（净现金）
5. CAGR > 5%（持续增长）

- 5/5 → ✅ 候选 | 3-4/5 → ⚠️ 边缘 | 0-2/5 → ❌ 淘汰

## 仪表盘功能

- **左侧面板**: ticker 列表（勾选对比 / 点击详情）、搜索过滤、⭐ 星标（localStorage + URL hash 持久化）、芒格筛选结论（默认折叠，点击展开）
- **📊 汇总排名**: 全 ticker 汇总表，可排序，勾选行高亮，Ticker 名可点击跳转深度详情
- **📈 图表对比**: ROIC 折线图、营收/EBIT 增长曲线（半对数）、柱状图、雷达图、EPS YoY% 增长率对比折线图、关键比率对比表
- **🔍 深度详情**: Ticker 大标题、收入/净现金/ROIC/EPS YoY% 四联图表、ROIC 计算明细（逐年验证）、芒格筛选卡、EPS CAGR 统计芯片、统计摘要、三大报表原始数据
- **💡 悬停提示**: 英文指标标签悬停显示中文释义
- **⚠️ 短历史标注**: 数据不足 20 年的 ticker 全局标注提醒

## 技术栈

- Python 3（stdlib only，零外部依赖）
- ECharts 5（构建时自动下载并内联嵌入）
- 纯 HTML/CSS/JS，单文件自包含
