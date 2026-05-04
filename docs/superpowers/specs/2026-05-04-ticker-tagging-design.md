# 股票三态标注设计

日期：2026-05-04

## 背景

随着列表中股票数量增多，仅有 ⭐ 星标已不够用。用户需要标注"看过并排除"的股票，使其不占主要视线但仍可找回。

## 核心概念

每只股票有三种互斥状态：

| 状态 | 含义 | 图标 | 颜色 |
|------|------|------|------|
| 无标记 | 还没看过/未分类 | ☆ | #999 |
| 星标 | 关注/候选 | ⭐ | #fbbc04 |
| 排除 | 看过，不想要 | 🚫 | #ea4335 |

## 数据模型

### 现状

```js
state.stars = ['AAPL', 'MSFT'];  // string[]
```

### 改为

```js
state.tags = { AAPL: 'star', IBM: 'exclude' };  // { [ticker]: 'star' | 'exclude' }
```

- 不在 `tags` 中的 ticker → 无标记
- 值只可能为 `'star'` 或 `'exclude'`，天然互斥

### 持久化

- localStorage key: `stock-screener-tags`，值为 `{"AAPL":"star","IBM":"exclude"}`
- URL hash: `#stars=AAPL,MSFT&excluded=IBM,TSLA`（向后兼容旧 `#stars=A,B` 格式）
- 加载优先级：URL hash > localStorage

### 迁移

首次加载时检测旧 `stock-screener-stars` key，自动转换为 `tags`（全部映射为 `'star'`），然后删除旧 key。

## 左侧面板交互与视觉

### 三态循环切换

点击星标图标位置：`☆(无标记) → ⭐(星标) → 🚫(排除) → ☆(无标记)`

### 列表分组排序

1. ⭐ 星标组
2. 无标记组
3. 🚫 排除组

组间用分割线隔开（复用 `.ticker-divider`）。

### 排除组视觉半隐藏

- 整行 opacity: 0.45
- hover 时 opacity 恢复到 0.8
- ROIC mini 值保留颜色但随 opacity 降低
- 仍可勾选对比、仍可点击进详情（功能不限制）

### "勾选全部星标"按钮

保持不变，仅作用于星标组，不涉及排除组。

## 切换函数与 URL 同步

### toggleTag

```js
function toggleTag(ticker) {
  const current = state.tags[ticker];
  if (!current) {
    state.tags[ticker] = 'star';        // ☆ → ⭐
  } else if (current === 'star') {
    state.tags[ticker] = 'exclude';      // ⭐ → 🚫
  } else {
    delete state.tags[ticker];           // 🚫 → ☆
  }
  saveTags();
  renderTickerList();
}
```

### saveTags / loadTags

- `saveTags()`: 写入 `localStorage('stock-screener-tags', JSON.stringify(state.tags))`，调用 `syncTagsHash()`
- `syncTagsHash()`: 从 tags 提取 stars 和 excluded 两组，拼接 `#stars=A,B&excluded=C,D`。两组都为空则清除 hash
- `loadTags()`: 优先读 URL hash，其次读 localStorage。首次检测旧 `stock-screener-stars` key 时自动迁移

### URL hash 解析

```
#stars=AAPL,MSFT&excluded=IBM,TSLA
```

兼容旧格式 `#stars=AAPL,MSFT`（无 excluded 段，全部视为 star）。

## 受影响的函数

| 旧函数 | 变化 |
|--------|------|
| `toggleStar(ticker)` | → `toggleTag(ticker)`，循环逻辑替换 |
| `toggleAllStars()` | 读 `Object.entries(tags).filter(→'star')` 提取星标列表 |
| `loadStars()` | → `loadTags()`，加迁移逻辑 |
| `saveStars()` | → `saveTags()` |
| `syncStarsHash()` | → `syncTagsHash()`，双段输出 |
| `renderTickerList()` | 三组渲染，排除组加 opacity |

## 不受影响的部分

- 汇总排名表
- 图表对比
- 深度详情
- 自定义筛选器
- 芒格筛选结论

这些模块不引用 tags/stars 数据。

## 改动范围

仅修改 `src/template.html` 中的 `<script>` 和 `<style>` 部分，然后 `python src/build.py` 重新构建。
