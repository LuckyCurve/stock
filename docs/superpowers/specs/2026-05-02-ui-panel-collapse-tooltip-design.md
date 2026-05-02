# UI 优化设计：左侧面板折叠 + Tippy.js Tooltip

**日期**: 2026-05-02  
**状态**: 已批准

---

## 1. 左侧面板折叠

### 目标
允许用户收起左侧 ticker 面板，让右侧内容区获得更多空间。

### 交互设计
- 面板头部右侧加一个折叠按钮（`◀`），点击后面板收缩至 32px 宽
- 收起状态下只显示居中的展开按钮（`▶`），隐藏所有内容（搜索框、ticker 列表、芒格结论）
- 右侧内容区自动扩展占满剩余宽度
- 再次点击按钮展开面板，恢复 220px 宽
- 折叠状态存入 `localStorage`（key: `panelCollapsed`），刷新后保持

### 实现方式
- `state` 对象增加 `panelCollapsed: bool` 字段，初始值从 `localStorage` 读取
- `.left-panel` 增加 `.collapsed` CSS 类：`width: 32px; overflow: hidden`
- 面板头部 `.panel-header` 改为 flex 布局，右侧加 `<button class="panel-toggle">` 
- 收起时 `.panel-header` 文字隐藏，按钮图标切换为 `▶`
- JS 中 `togglePanel()` 函数切换 class 并同步 `localStorage`

---

## 2. Tippy.js Tooltip

### 目标
用 Tippy.js 替换浏览器原生 `title` tooltip，提供美观的气泡卡片样式。

### 依赖
- **Popper.js** (`@popperjs/core`): Tippy.js 的定位引擎，CDN: `https://cdn.jsdelivr.net/npm/@popperjs/core@2/dist/umd/popper.min.js`
- **Tippy.js** (`tippy.js`): tooltip 库，CDN: `https://cdn.jsdelivr.net/npm/tippy.js@6/dist/tippy-bundle.umd.min.js`
- **Tippy CSS**: `https://cdn.jsdelivr.net/npm/tippy.js@6/dist/tippy.css`

两个 JS 文件在构建时下载并内联（与 ECharts 相同机制），CSS 同样内联。

### 使用方式
- 所有 `title="中文"` 改为 `data-tippy-content="中文"`（共 4 处）
- 页面初始化时调用 `tippy('[data-tippy-content]')`
- 移除现有 CSS：`[title] { text-decoration: underline dotted... }`
- 保留下划线提示：改为 `[data-tippy-content] { text-decoration: underline dotted #adb5bd; ... }`

### build.py 修改
在 `build.py` 中增加下载并内联 Popper.js、Tippy.js、Tippy CSS 的逻辑，缓存至 `.cache/` 目录：
- `.cache/popper.min.js`
- `.cache/tippy-bundle.umd.min.js`  
- `.cache/tippy.css`

模板中新增占位符 `{{{TIPPY_SCRIPTS}}}` 和 `{{{TIPPY_CSS}}}`，构建时替换。

---

## 3. 受影响文件

| 文件 | 改动 |
|------|------|
| `src/template.html` | 面板折叠 HTML/CSS/JS；`title` → `data-tippy-content`；移除旧 tooltip CSS；新增 Tippy 初始化 |
| `src/build.py` | 下载并内联 Popper.js + Tippy.js + Tippy CSS |

---

## 4. 不在范围内

- 面板收起时不显示 ticker 图标/缩略信息（纯收起，无图标模式）
- 不修改 ECharts 内置 tooltip 样式
- 不修改芒格筛选卡片内的 criterion 气泡（已有 `title`，统一替换即可）
