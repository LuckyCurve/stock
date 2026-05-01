# 星标全选按钮 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在左侧面板添加一键勾选/取消所有星标股票的 toggle 按钮

**Architecture:** 纯前端改动，修改 `src/template.html` 中的 CSS 和 JS。添加按钮样式、按钮渲染逻辑、toggle 行为函数。按钮在 `renderTickerList()` 中动态生成，确保状态同步。

**Tech Stack:** HTML/CSS/JS（现有技术栈）

---

### Task 1: 添加按钮 CSS 样式

**Files:**
- Modify: `src/template.html`（CSS 部分，`.ticker-filter` 样式之后）

- [ ] **Step 1: 在 CSS 中添加 `.star-select-all` 样式**

在 `.ticker-divider` 样式之后添加：

```css
.star-select-all { display: block; width: calc(100% - 20px); margin: 4px 10px; padding: 5px 8px; border: 1px solid #fbbc04; border-radius: 4px; background: #fef7e0; color: #e37400; font-size: 11px; font-weight: 600; cursor: pointer; text-align: center; transition: background 0.15s, color 0.15s; user-select: none; }
.star-select-all:hover { background: #fbbc04; color: #fff; }
```

- [ ] **Step 2: 重新构建并验证样式生效**

Run: `python src/build.py`
Expected: 构建成功，打开 munger-dashboard.html 可在浏览器 DevTools 中看到新样式类

- [ ] **Step 3: 提交**

```bash
git add src/template.html
git commit -m "feat: add star-select-all button CSS"
```

---

### Task 2: 添加 toggleAllStars 函数与按钮渲染逻辑

**Files:**
- Modify: `src/template.html`（JS 部分）

- [ ] **Step 1: 在 `toggleStar` 函数之后添加 `toggleAllStars` 函数**

```javascript
function toggleAllStars() {
  if (state.stars.length === 0) return;
  const allStarredChecked = state.stars.every(t => state.checkedTickers.has(t));
  if (allStarredChecked) {
    // 取消全部星标 ticker 的勾选，不影响非星标
    for (const t of state.stars) {
      state.checkedTickers.delete(t);
    }
  } else {
    // 超限检查
    if (state.stars.length > MAX_COMPARE) {
      alert('最多同时对比 ' + MAX_COMPARE + ' 支股票');
      return;
    }
    // 先清除所有勾选，再勾选星标
    state.checkedTickers.clear();
    for (const t of state.stars) {
      state.checkedTickers.add(t);
    }
  }
  renderTickerList();
  if (state.activeTab === 'compare' || state.activeTab === 'summary') renderContent();
}
```

- [ ] **Step 2: 在 `renderTickerList` 函数中，列表渲染前插入按钮**

在 `function renderItem(t) {` 定义之前（即 `for (const t of starred) renderItem(t);` 之前），插入按钮渲染逻辑：

```javascript
  // Star select-all button
  if (state.stars.length > 0) {
    const filter = state.filterText.toLowerCase();
    const visibleStars = state.stars.filter(s => !filter || s.toLowerCase().includes(filter));
    if (visibleStars.length > 0) {
      const allStarredChecked = visibleStars.every(t => state.checkedTickers.has(t));
      const btn = document.createElement('div');
      btn.className = 'star-select-all';
      btn.textContent = allStarredChecked
        ? '⭐ 取消全部星标 (' + visibleStars.length + ')'
        : '⭐ 勾选全部星标 (' + visibleStars.length + ')';
      btn.addEventListener('click', (e) => { e.stopPropagation(); toggleAllStars(); });
      list.appendChild(btn);
    }
  }
```

注意：这里用 `visibleStars`（受搜索过滤影响的星标子集）来判断文案，但 `toggleAllStars()` 操作的是全部 `state.stars`，与过滤无关——这是合理的，因为按钮操作的是星标集合本身。

- [ ] **Step 3: 重新构建并手动测试**

Run: `python src/build.py`
Expected: 构建成功

手动测试场景：
1. 无星标 → 按钮不显示
2. 有星标 → 显示"⭐ 勾选全部星标 (N)"
3. 点击 → 所有星标被勾选，按钮变为"⭐ 取消全部星标 (N)"
4. 再点击 → 取消星标的勾选
5. 超过 8 个星标点击 → 弹 alert，不做变更
6. 搜索过滤时，按钮显示过滤后可见的星标数

- [ ] **Step 4: 提交**

```bash
git add src/template.html
git commit -m "feat: add star-select-all toggle button in left panel"
```
