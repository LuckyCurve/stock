# 投资原则标语设计文档

**日期**: 2026-05-02  
**状态**: 已批准

---

## 需求

在仪表盘顶部 top-bar 区域，将三条个人投资原则以竖排平行列表的形式嵌入页面，作为装饰性精神标注。

三条原则：
1. 安全边际
2. 保持谦逊
3. 读懂生意

---

## 设计

### 视觉结构

top-bar 标题区域从上到下依次为：

```
📊 股票筛选器
悟已往之不谏，知来者之可追。实迷途其未远，觉今是而昨非。

投资原则：
· 安全边际
· 保持谦逊
· 读懂生意
```

- 古文 tagline 保留，位置不变
- 古文与"投资原则："之间留 4px 间距
- 三条原则竖排，平行并列关系，不分主次

### 样式规格

| 元素 | 样式 |
|------|------|
| `投资原则：` 标题 | `font-size: 11px`, `color: #6c757d`, `letter-spacing: 0.5px`, `margin-top: 4px`, 正体 |
| 每条原则 | `font-size: 11px`, `color: #868e96`, `line-height: 1.6`, 正体，前缀 `·` |
| 整体容器 | 无边框、无背景，融入现有 top-bar 布局 |

### HTML 结构变更

在 `src/template.html` 的 `.tagline` div 下方新增：

```html
<div class="tagline">悟已往之不谏，知来者之可追。实迷途其未远，觉今是而昨非。</div>
<div class="principles">
  <div class="principles-label">投资原则：</div>
  <div class="principles-list">
    <div>· 安全边际</div>
    <div>· 保持谦逊</div>
    <div>· 读懂生意</div>
  </div>
</div>
```

### CSS 新增

```css
.principles { margin-top: 4px; }
.principles-label { font-size: 11px; color: #6c757d; letter-spacing: 0.5px; }
.principles-list { font-size: 11px; color: #868e96; line-height: 1.6; }
```

---

## 范围

- **只改** `src/template.html`（HTML 结构 + CSS）
- **不改** `compute.py`、`parse.py`、`build.py`
- 改完后运行 `python src/build.py` 重新生成 `munger-dashboard.html`

---

## 验证标准

- [ ] top-bar 显示古文 tagline + 投资原则两个区块
- [ ] 三条原则竖排，视觉上平行
- [ ] 样式克制，不抢夺标题焦点
- [ ] 左侧面板折叠/展开不影响 top-bar 显示
- [ ] 页面在常规宽度下不出现换行错位
