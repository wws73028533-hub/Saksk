# quiz 页面 partials 维护指南

本目录用于承载 `app/templates/quiz.html` 的组件化拆分结果。

目标：
- **降低单文件体积**：把 HTML/CSS/JS 按“职责”拆成模块；
- **保证功能不变**：所有 JS 依赖的 `id/class/data-*` **必须保持一致**；
- **便于扩展**：新增功能时只改对应 partial，避免在一个超长文件里查找位置。

> 当前阶段为了降低回归风险：CSS/JS 仍以内联形式存在，但被拆分到 `_inline_css.html` / `_inline_js.html` 中，通过 `quiz.html -> _head_meta.html/_scripts_main.html` 引入。

---

## 入口文件与装配关系

- **入口**：`app/templates/quiz.html`
  - 只负责：设置少量 Jinja 变量、然后 include 各 partial。

装配链路（简化）：

- `quiz.html`
  - `partials/quiz/_head_meta.html`
    - `partials/quiz/_inline_css.html`
  - `partials/quiz/_sidebar.html`
  - `partials/quiz/_main_layout.html`
    - `partials/quiz/_header.html`
    - `partials/quiz/_progress.html`
    - `partials/quiz/_question.html`
    - `partials/quiz/_footer.html`
    - `partials/quiz/_dock.html`
  - `partials/quiz/_modals_forward.html`
  - `partials/quiz/_modals_score.html`
  - `partials/quiz/_scripts_main.html`
    - `partials/quiz/_inline_js.html`

---

## 文件职责说明（逐个）

### `_head_meta.html`
- 放置：`<meta>`、`<title>` 逻辑、`icon`、`theme-color`。
- 通过 `{% include 'partials/quiz/_inline_css.html' %}` 注入整段 CSS。
- **注意**：不要在别处再插入 `<style>`，否则会出现“样式覆盖顺序不透明”的问题。

### `_inline_css.html`
- quiz 页所有样式的唯一来源（当前阶段）。
- 重点关注：
  - `@media(min-width:1024px)`（桌面布局）
  - `.main-area / #mainCard / #answerExplainDock`（布局核心）
- **改样式建议**：尽量追加到文件末尾，并写清注释，避免被后面的同名选择器覆盖。

#### 近期约定：问答题/计算题右侧 dock（桌面端）
为满足“长答案/长解析”的阅读体验，桌面端对**问答题/计算题**启用右侧栏布局。

- **触发方式（JS）**：`showQuestion()` 会根据当前题 `data-type`，对 `.main-area` 动态切换类名：
  - `type === '问答题' || type === '计算题'` → `.main-area.with-right-dock`
  - 其它题型 → 移除该类，恢复默认（dock 在主卡下方）

- **布局目标（CSS）**：
  - `#mainCard` 左侧固定宽度 `var(--main-card-max-width)`（当前为 766px）
  - `#answerExplainDock` 右侧固定宽度（当前为 **420px**，可按设计调整）
  - dock 采用 `position: sticky; top: 20px;`，随滚动保持可见
  - `#answerCard` / `#explainCard` 在右侧栏内 **等高对齐**（flex 等分 + min-height 兜底）

> **原则**：不改 JS 依赖的 `id/class`，只做布局层适配。

#### 近期约定：填空题答案结构化展示（dock）
为避免填空题答案在 `#answerCard` 中以 `1;一;;2;二...` 这种串展示，前端将其结构化。

- **数据格式兼容（历史约定）**：
  - 多空：用 `;;` 分隔每一空
  - 一空多答案：同一空内用 `;` 分隔备选
  - 示例：`1;一;;2;二;;3;三` → 3 空，每空备选 2 个

- **渲染效果**：
  - 单空：
    - 单答案：显示为“答案”
    - 多答案：显示为“可接受答案”，使用 pill 标签展示
  - 多空：逐行展示“空 1/空 2...”，每空内多答案用 pill 标签展示

- **相关样式类**：`.blank-ans` / `.blank-ans-row` / `.pill`
  - pill 字体目前为 `14px`（更易读）

### `_sidebar.html`
- 左侧题号列表与工具按钮（清除进度/重排）。
- 关键 DOM：
  - `#sidebar`、`#overlay`、`#question-list`
  - 列表项：`.q-item`，并且必须有 `id="list-item-{{ loop.index0 }}"`

### `_main_layout.html`
- 主内容区（header/progress/question/footer）+ dock + 悬浮球（Fab）。
- 关键 DOM：
  - `#quizFab`（悬浮球本体）
  - `#quizFabMenu`（圆环菜单容器）
  - `.quiz-fab-item[data-action]`（菜单项）
    - `clearCurrent`：清除本题进度（新增）
- 约定：考试模式悬浮球策略（在 `_inline_js.html -> init()` 内处理）：
  - 考试进行中（`mode === 'exam' && !EXAM_SUBMITTED`）：禁用/隐藏
  - 回顾模式（`mode === 'exam' && EXAM_SUBMITTED`）：允许显示（但部分菜单项禁用：`autoNext`/`clearCurrent`）

### `_header.html`
- 顶部栏：菜单/转发/计时器/模式徽章/主题切换/退出。
- 关键 DOM：
  - `#forward-question-btn`
  - `#timer`（考试模式）

### `_progress.html`
- 进度条。
- 关键 DOM：
  - `#progress-fill`
  - `#progress-label`

### `_question.html`
- **最关键**：题目 DOM 结构必须保持原样。
- 关键 DOM：
  - 题容器：`.question-box` 且必须带 `id="q-{{ loop.index0 }}"`
  - 必要数据：`data-type / data-answer / data-id / data-score / data-index`
  - 图片：`.question-image-gallery` + `data-images`
  - 内部答案解析：`.quiz-card.card-answer / .quiz-card.card-explain`

### `_footer.html`
- 上一题/下一题/查看结果/交卷按钮。
- 关键 DOM：
  - `#btn-prev`
  - `#btn-next`（刷题/背题）
  - `#btn-check`（刷题查看结果）
  - `#btn-next-exam` / `#btn-submit-exam`（考试）

### `_dock.html`
- 答案/解析“外置展示区”。
- 关键 DOM：
  - `#answerExplainDock`
  - `#answerCard` / `#explainCard`

### `_modals_forward.html`
- 转发弹层 UI。
- 关键 DOM：
  - `#forwardOverlay`
  - `#forwardUserSearch` / `#forwardUserList`

### `_modals_score.html`
- 成绩弹层 UI。
- 关键 DOM：
  - `#scoreOverlay`
  - `#finalScore` / `#scoreGrid`

### `_scripts_main.html`
- 只负责：包裹 `<script>` 并 include `_inline_js.html`。
- 以及快捷键提示 `.shortcut-hint`。

### `_inline_js.html`
- quiz 页所有 JS（当前阶段）。
- **重要原则**：
  - 尽量不要在 JS 中硬编码新的选择器；
  - 如果必须新增 DOM，请优先在对应 partial 中加，并写注释说明依赖关系。

---

## 常见坑 / 排查思路

### 1）桌面端（>1024px）布局异常
- 优先检查 `_inline_css.html` 里的 `@media(min-width:1024px)`
- 在浏览器 DevTools 里看：
  - `.main-area` 的 `display / width / gap`
  - `#mainCard` 是否被拉伸
  - `#answerExplainDock` 的宽度/是否 sticky 生效

### 2）修改 CSS 后页面没变化
- 强制刷新：`Ctrl+F5`
- 确认页面确实在使用 `quiz.html`（而不是旧模板或其它环境）

### 3）JS 报错（找不到元素）
- 先确认对应的 `id/class` 是否被改名或移动。
- 题目 DOM 结构变动时最容易引发连锁问题：优先检查 `_question.html`。

---

## 后续演进（可选）

当你确认页面稳定后，建议第二阶段做：
- 把 `_inline_css.html` 迁移到 `static/quiz.css`
- 把 `_inline_js.html` 迁移到 `static/quiz.js`
- 模板中用 `<link rel="stylesheet">` 和 `<script src>` 引入

这样可以进一步提升缓存效率与可维护性。
>export pdf