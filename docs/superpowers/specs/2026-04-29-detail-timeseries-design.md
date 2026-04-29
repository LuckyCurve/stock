# 深度详情时序图设计

## 概述

在深度详情页顶部（芒格筛选卡上方、短历史警告下方）新增三个等宽横向时序折线图，展示当前 ticker 的收入、净现金/总资产、ROIC 逐年趋势。

## 布局

```
┌─────────────────────────────────────────────────┐
│  ⚠️ 短历史警告（如有）                            │
├─────────────┬─────────────┬─────────────────────┤
│  Revenue    │   NetC%     │      ROIC           │
│  折线图     │   折线图    │      折线图          │
│  200px高    │   200px高   │      200px高        │
├─────────────┴─────────────┴─────────────────────┤
│  芒格筛选卡                                      │
│  ...                                             │
```

一行三列等宽，使用 CSS grid `grid-template-columns: 1fr 1fr 1fr`。

## 三个图表

### 1. 收入 (Revenue)
- **数据源**: `raw_data.income['Sales/Revenue/Turnover']`
- **X轴**: 财年，范围 = 数据实际年份跨度（不外扩）
- **Y轴**: 线性，单位 $M
- **参考线**: 无

### 2. 净现金/总资产 (NetC%)
- **数据源**: 新增 `net_cash_pct_series`，逐年计算
- **公式**: `(Cash - LT Debt - ST Debt) / Total Assets × 100`
- **X轴**: 财年，范围 = 数据实际年份跨度
- **Y轴**: 线性，单位 %
- **参考线**: 0% 红色虚线（线上方 = 净现金企业，线下方 = 净负债）

### 3. ROIC
- **数据源**: 已有 `roic_series`
- **X轴**: 财年，范围 = 数据实际年份跨度
- **Y轴**: 线性，单位 %
- **参考线**: 10% 黄色虚线 + 20% 绿色虚线

## 计算变动

### compute.py — 新增 `compute_net_cash_pct_series`

```python
def compute_net_cash_pct_series(data):
    """逐年计算 NetC%。返回 {year: net_cash_pct or None}"""
    # 遍历 balance sheet 中有 Total Assets 的年份
    # 对每年: net_cash_pct = (cash - lt_debt - st_debt) / total_assets * 100
    # 缺值年份返回 None
```

### compute.py — `compute_all` 新增字段

- `net_cash_pct_series`: 上述函数返回值

## 模板变动

### template.html — `renderDetail` 函数

在芒格筛选卡 HTML 之前，插入三图容器：

```html
<div class="charts-grid" style="grid-template-columns:1fr 1fr 1fr;margin-bottom:12px;">
  <div class="chart-box"><div class="chart-title">收入趋势</div><div id="chartDetailRevenue" style="height:200px;"></div></div>
  <div class="chart-box"><div class="chart-title">净现金/总资产</div><div id="chartDetailNetCash" style="height:200px;"></div></div>
  <div class="chart-box"><div class="chart-title">ROIC 趋势</div><div id="chartDetailRoic" style="height:200px;"></div></div>
</div>
```

新增三个 ECharts 渲染函数：
- `renderDetailRevenueChart(t)` — 收入折线，X轴范围 = 数据年份
- `renderDetailNetCashChart(t)` — NetC% 折线 + 0% 参考线
- `renderDetailRoicChart(t)` — ROIC 折线 + 10%/20% 参考线

图表实例加入 `chartInstances` 以便切换时正确 dispose。

## X轴范围规则

三个图统一：X轴 min/max = 该图数据的实际年份最小值/最大值，不外扩到固定范围。这样短历史 ticker 不会有大段空白。

## 不涉及的部分

- 汇总排名、图表对比页不变
- 芒格筛选逻辑不变
- fetch / parse 不变
