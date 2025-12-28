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

#### 题型处理说明
- **选择题**（单选）：选择后自动调用 `autoCheck()` 显示结果
- **多选题**：**不自动检查**，用户需要先选择选项，然后点击"查看结果"按钮才能看到答案
  - 多选题的 checkbox 没有 `onchange="autoCheck()"` 事件
  - 必须在 `_inline_js.html` 中确保 `autoCheck()` 函数不处理多选题
- **判断题**：选择后自动调用 `autoCheck()` 显示结果
- **填空题**：需要手动点击"查看结果"按钮
- **问答题**：需要手动点击"查看结果"按钮

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

## 重要约定：关键 JS 变量声明

### `questions` 和 `listItems` 必须使用 `let` 而非 `const`

在 `_inline_js.html` 开头声明的两个关键变量：

```javascript
let questions = document.querySelectorAll('.question-box');
let listItems = document.querySelectorAll('.q-item');
```

**必须使用 `let`，不能使用 `const`！**

原因：
- `reshuffle()`（重排功能）需要在 DOM 重排后重新获取元素引用
- 如果使用 `const`，`reshuffle()` 中的 `questions = ...` 会失败
- 使用 `window.questions = ...` 只是创建了一个全局属性，而不是更新模块作用域中的变量
- 这会导致其他函数（如 `showQuestion()`）仍然使用旧的 NodeList，造成侧边栏与题目显示不同步

**Bug 历史**（2025-12-27 修复）：
- 问题表现：选择乱序进入答题界面后，点击"重排"按钮，侧边栏列表顺序变了，但主内容区题目顺序没变
- 根本原因：`const questions` 和 `const listItems` 无法被重新赋值，`reshuffle()` 中的 `window.questions = ...` 实际上没有更新原变量
- 修复方案：将 `const` 改为 `let`，并在 `reshuffle()` 中直接使用 `questions = ...` 赋值

### `reshuffle()` 必须同步新顺序到云端

`reshuffle()` 函数在重排题目后，必须完成以下步骤：

1. **收集新顺序**：从 DOM 中获取每个题目的 `data-id`
   ```javascript
   const newOrder = Array.from(questions).map(q => parseInt(q.getAttribute('data-id')));
   ```

2. **更新 `cachedOrder`**：
   ```javascript
   cachedOrder = newOrder;
   ```

3. **调用 `saveState(true)` 同步到服务器**：
   - `saveState()` 会把 `cachedOrder` 放入 `payload.order`
   - 通过 `/api/progress` 保存到 `user_progress` 表
   - 后端 `quiz.py` 会读取 `saved_order` 并按此顺序渲染题目

**Bug 历史**（2025-12-27 修复）：
- 问题表现：重排后刷新页面，题目又恢复到之前的顺序
- 根本原因：`reshuffle()` 只在前端打乱了 DOM，没有更新 `cachedOrder` 和同步到服务器
- 修复方案：在 DOM 重排后，收集新顺序、更新 `cachedOrder`、调用 `saveState(true)`

### `progressKey()` 必须与后端 `quiz.py` 保持一致

前端 `progressKey()` 生成的 key 必须与后端 `quiz.py` 中的 key 格式完全一致：

```
quiz_progress_{uid}_{mode}_{subject}_{type}_{dataScope}_q{0/1}_o{0/1}
```

**关键字段**：
- `dataScope`：根据 `source` 参数计算，值为 `'favorites'`/`'mistakes'`/`'all'`

**Bug 历史**（2025-12-27 修复）：
- 问题表现：进度保存只保存了题号索引，刷新后题目顺序丢失
- 根本原因：前端 `progressKey()` 少了 `dataScope` 字段，导致 key 与后端不匹配，无法获取后端保存的 `order`
- 修复方案：
  1. 在 `progressKey()` 中添加 `dataScope` 字段
  2. 在 `init()` 中添加兜底逻辑：如果 `cachedOrder` 为空且是乱序模式，从 DOM 收集题目顺序

### 选项打乱必须使用确定性随机

**重要**：后端 `quiz.py` 中的选项打乱必须使用**确定性随机**（固定种子），而不是纯随机。

```python
# 种子 = 用户ID * 1000000 + 题目ID
shuffle_seed = (uid if uid != -1 else 0) * 1000000 + q['id']
rng = random.Random(shuffle_seed)
rng.shuffle(q['options'])
```

**原因**：
- 纯随机打乱会导致每次请求选项顺序不同
- 同一用户在不同浏览器/设备看到的选项顺序不一致
- 答案字母也会不一致（因为答案是根据打乱后的顺序重新计算的）

**Bug 历史**（2025-12-28 修复）：
- 问题表现：A/B 两个浏览器同时登录同一账号，启用"打乱选项"做同一道题，选项顺序不一致
- 根本原因：`random.shuffle()` 是纯随机，每次请求都会产生不同顺序
- 修复方案：使用 `random.Random(seed)` 创建确定性随机生成器，种子为 `用户ID * 1000000 + 题目ID`

### 悬浮球禁用时必须同时禁用所有相关功能

当用户在题库设置中关闭悬浮球时，悬浮球的所有功能都应该被禁用，包括：
- 答对自动切题（`isFabAutoNextEnabled()`）
- AI 解析
- 收藏
- 清除本题
- 专注模式

**实现方式**：在 `isFabAutoNextEnabled()` 等功能函数中，首先检查 `isFabEnabled()`：

```javascript
function isFabAutoNextEnabled(){
    // 如果悬浮球被禁用，所有悬浮球相关功能也应该禁用
    if (!isFabEnabled()) return false;
    return localStorage.getItem(FAB_AUTO_NEXT_KEY) === '1';
}
```

**Bug 历史**（2025-12-28 修复）：
- 问题表现：用户在题库设置中关闭悬浮球后，"答对自动切题"功能仍然生效
- 根本原因：`isFabAutoNextEnabled()` 只检查了自己的开关，没有检查悬浮球总开关
- 修复方案：在 `isFabAutoNextEnabled()` 中添加 `if (!isFabEnabled()) return false;`

### 多选题特殊处理规则

**重要约定**：多选题与选择题（单选）的区别：

1. **答题行为**：
   - 选择题（单选）：选择选项后**自动显示结果**（通过 `autoCheck()`）
   - 多选题：选择选项后**不自动显示结果**，必须点击"查看结果"按钮

2. **答案格式**：
   - 选择题：答案格式为单个字母，如 `"A"`
   - 多选题：答案格式为多个字母，如 `"AB"` 或 `"ABC"`（至少两个）

3. **验证逻辑**：
   - 在 `admin.py` 中添加题目时，会验证多选题答案至少包含两个选项
   - 验证答案中的所有字母是否在选项范围内

4. **JS 函数处理**：
   - `autoCheck()`：只处理选择题和判断题，**不处理多选题**
   - `judgeQuestion()`：支持选择题、判断题、多选题（答案比较逻辑相同：排序后比较字符串）
   - `hasAnswered()`：支持选择题、判断题、多选题（检查是否有选中的选项）
   - `styleFeedback()`：支持选择题、判断题、多选题（高亮正确/错误选项）

5. **选项打乱**：
   - 多选题支持选项顺序打乱（与选择题一致）
   - 使用确定性随机，确保同一用户同一题目的选项顺序一致
   - 答案会根据打乱后的选项顺序重新计算

6. **模板渲染**：
   - 在 `_question.html` 中，多选题有独立的模板分支
   - 多选题的 checkbox 不包含 `onchange="autoCheck()"` 事件

**Bug 历史**（2025-01-XX 添加）：
- 多选题功能是新增模块，与选择题完全独立
- 多选题不改变选择题的任何功能和行为

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

### 4）多选题不显示结果
- 检查 `autoCheck()` 函数是否误处理了多选题
- 确认多选题的 checkbox 是否包含了 `onchange="autoCheck()"` 事件（不应该有）
- 确认 `_question.html` 中多选题模板分支是否正确
- 检查 `judgeQuestion()` 和 `styleFeedback()` 是否支持多选题类型

### 5）多选题答案验证失败
- 确认答案格式：必须是至少两个字母，如 "AB"、"ABC"
- 检查答案中的所有字母是否都在选项范围内
- 查看后端 `admin.py` 中的验证逻辑是否正确执行

---

## 后续演进（可选）

当你确认页面稳定后，建议第二阶段做：
- 把 `_inline_css.html` 迁移到 `static/quiz.css`
- 把 `_inline_js.html` 迁移到 `static/quiz.js`
- 模板中用 `<link rel="stylesheet">` 和 `<script src>` 引入

这样可以进一步提升缓存效率与可维护性。
>export pdf