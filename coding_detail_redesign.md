# 编程题答题页面重新设计方案

## 设计理念

基于 iOS 18 风格，采用**极简主义**和**毛玻璃效果（Glassmorphism）**，使用**抽屉式弹窗（Drawer）**替代传统侧边栏，打造沉浸式编程体验。

---

## 整体布局

### 主界面结构

```
┌─────────────────────────────────────────────────────────┐
│  左侧：功能栏（固定，极宽，毛玻璃效果）                  │
│  ┌─────────────────────────────────────┐               │
│  │  [题目选择]                          │               │
│  │  [提交历史]                          │               │
│  │  [排名]                              │               │
│  │  [设置]                              │               │
│  └─────────────────────────────────────┘               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  左侧：题目描述区域（可拖拽调整宽度）                    │
│  ┌─────────────────────────────────────┐               │
│  │  题目标题 + 元信息                    │               │
│  ├─────────────────────────────────────┤               │
│  │  题目描述（Markdown渲染）             │               │
│  │  示例、约束、提示等                   │               │
│  └─────────────────────────────────────┘               │
│  ║ ← 可拖拽分割线                                       │
│  右侧：代码编辑器区域（可拖拽调整宽度）                  │
│  ┌─────────────────────────────────────┐               │
│  │  编辑器工具栏（语言选择、上一题/下一题）│            │
│  │                      [🐛 Debug]      │ ← Debug按钮  │
│  ├─────────────────────────────────────┤               │
│  │  Monaco Editor（代码编辑区）          │               │
│  ├─────────────────────────────────────┤               │
│  │  操作按钮（测试用例、提交、重置）      │               │
│  ├─────────────────────────────────────┤               │
│  │  输出面板（执行结果、判题结果）        │               │
│  ├─────────────────────────────────────┤               │
│  │  Debug窗口（展开时显示）              │               │
│  │  ┌───────────────────────────────┐ │               │
│  │  │ [测试用例] [编译器输出]          │ │ ← 标签页     │
│  │  ├───────────────────────────────┤ │               │
│  │  │  测试用例输入区域               │ │               │
│  │  │  1 | 50800                     │ │               │
│  │  │                                │ │               │
│  │  │  [重置测试用例] [运行测试 ▶]    │ │               │
│  │  └───────────────────────────────┘ │               │
│  └─────────────────────────────────────┘               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**布局说明**：
- **左侧功能栏**：固定宽度（约 `50px`），垂直排列功能按钮
- **题目描述区域**：
  - 默认宽度 `50%`，可通过拖拽分割线调整
  - 支持自由上下滑动查看完整题目内容
  - 内容超出可视区域时显示滚动条
- **代码编辑器区域**：默认宽度 `50%`，可通过拖拽分割线调整
- **可拖拽分割线**：位于两个区域之间，鼠标悬停时显示拖拽提示，支持水平拖拽调整宽度比例

---

## 抽屉式弹窗设计

### 1. 题目选择抽屉（Question Drawer）

**触发方式**：点击左侧功能栏的"题目选择"按钮

**位置**：从**右侧滑入**

**尺寸**：
- 宽度：`420px`（移动端：`85vw`，最大`420px`）
- 高度：`100vh`
- 距离顶部：`0`
- 距离右侧：`0`

**设计特点**：
- 毛玻璃背景：`rgba(255, 255, 255, 0.72)` + `backdrop-filter: blur(40px)`
- 圆角：仅左侧上角和下角为 `18px`
- 阴影：`0 -8px 40px rgba(0, 0, 0, 0.12)`
- 边框：左侧 `0.5px solid rgba(0, 0, 0, 0.06)`

**内容结构**：
```
┌─────────────────────────────────────┐
│  [×] 题目选择                        │ ← 标题栏（固定）
├─────────────────────────────────────┤
│                                     │
│  题目列表（滚动区域，按题型分类）     │
│                                     │
│  📚 函数题 (fn)                     │
│  ┌───────────────────────────────┐ │
│  │ 📝 题目 #1: 两数之和           │ │
│  │    [红色框✓] 答案正确           │ │
│  └───────────────────────────────┘ │
│  ┌───────────────────────────────┐ │
│  │ 📝 题目 #2: 三数之和           │ │
│  │    [浅绿框✕] 答案错误           │ │
│  └───────────────────────────────┘ │
│  ┌───────────────────────────────┐ │
│  │ 📝 题目 #3: 四数之和           │ │
│  │    [蓝色框-] 待评测             │ │
│  └───────────────────────────────┘ │
│  ┌───────────────────────────────┐ │
│  │ 📝 题目 #4: 五数之和           │ │
│  │    [灰色虚线框] 未作答          │ │
│  └───────────────────────────────┘ │
│                                     │
│  💻 编程题 (</>)                    │
│  ┌───────────────────────────────┐ │
│  │ 📝 题目 #1: 字符串处理         │ │
│  │    [红色框✓] 答案正确           │ │
│  └───────────────────────────────┘ │
│  ┌───────────────────────────────┐ │
│  │ 📝 题目 #2: 数组操作           │ │
│  │    [浅绿框✕] 答案错误           │ │
│  └───────────────────────────────┘ │
│  ┌───────────────────────────────┐ │
│  │ 📝 题目 #3: 算法实现           │ │
│  │    [灰色虚线框] 未作答          │ │
│  └───────────────────────────────┘ │
│                                     │
└─────────────────────────────────────┘
```

**题目状态说明**：
- **⭕ 未作答**：尚未提交过代码（灰色虚线框）
- **⏳ 待评测**：代码已提交，等待评测中（蓝色实心框带横线）
- **✅ 答案正确**：所有测试用例通过（红色实心框带对勾）
- **❌ 答案错误**：部分或全部测试用例未通过（浅绿色实心框带X）

**题型分类**：
- **📚 函数题 (fn)**：函数编程题，需要实现特定函数
- **💻 编程题 (</>)**：完整编程题，需要实现完整程序

**题目列表显示**：
- 按题型分组显示
- 每个题型下显示该类型的所有题目
- 题目卡片仅显示题目标题和状态
- 点击题目卡片跳转到对应题目

**交互行为**：
- 点击题目卡片 → 关闭抽屉，跳转到对应题目
- 点击遮罩层（drawer-backdrop）→ 关闭抽屉
- 按 `ESC` 键 → 关闭抽屉
- 滑动关闭（移动端）：从右侧向左滑动超过 `30%` → 关闭

**动画效果**：
- 打开：从右侧滑入，`transform: translateX(0)`，`transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)`
- 关闭：滑出到右侧，`transform: translateX(100%)`
- 遮罩层：`opacity: 0 → 1`，`transition: opacity 0.3s ease`

---

### 2. 提交历史抽屉（Submissions Drawer）

**触发方式**：点击左侧功能栏的"提交历史"按钮

**位置**：从**右侧滑入**（同题目选择抽屉）

**尺寸**：与题目选择抽屉相同

**内容结构**：
```
┌─────────────────────────────────────┐
│  [×] 提交历史                        │ ← 标题栏
├─────────────────────────────────────┤
│                                     │
│  当前题目提交记录列表（滚动区域）     │
│  ┌───────────────────────────────┐ │
│  │    ✅ 通过 | 5/5 测试用例      │ │
│  │    ⏱️ 0.12s | 📅 2025-01-29   │ │
│  │    [查看代码] [重新提交]        │ │
│  └───────────────────────────────┘ │
│  ┌───────────────────────────────┐ │
│  │    ❌ 答案错误 | 3/5 测试用例   │ │
│  │    ⏱️ 0.08s | 📅 2025-01-28   │ │
│  │    [查看代码] [重新提交]        │ │
│  └───────────────────────────────┘ │
│  ┌───────────────────────────────┐ │
│  │    ⏱️ 超时 | 0/5 测试用例      │ │
│  │    ⏱️ 5.01s | 📅 2025-01-27   │ │
│  │    [查看代码] [重新提交]        │ │
│  └───────────────────────────────┘ │
│                                     │
│  [加载更多]                          │ ← 分页
└─────────────────────────────────────┘
```

**说明**：
- 仅显示当前正在查看的题目的提交历史
- 按时间倒序排列（最新的在前）

**交互行为**：
- 点击"查看代码" → 在抽屉内展开代码预览（可复制）
- 点击"重新提交" → 关闭抽屉，加载该提交的代码到编辑器
- 点击提交记录 → 展开详情（代码、测试用例结果等）

---

### 3. 排名抽屉（Ranking Drawer）

**触发方式**：点击左侧功能栏的"排名"按钮

**位置**：从**右侧滑入**（同其他抽屉）

**尺寸**：与题目选择抽屉相同

**内容结构**：
```
┌─────────────────────────────────────┐
│  [×] 排名                           │ ← 标题栏
├─────────────────────────────────────┤
│                                     │
│  当前题目排名列表（滚动区域）         │
│  ┌───────────────────────────────┐ │
│  │ 🥇 #1 张三                     │ │
│  │    ⏱️ 0.12s | 📅 2025-01-29   │ │
│  │    ✅ 首次通过                 │ │
│  └───────────────────────────────┘ │
│  ┌───────────────────────────────┐ │
│  │ 🥈 #2 李四                     │ │
│  │    ⏱️ 0.15s | 📅 2025-01-29   │ │
│  │    ✅ 首次通过                 │ │
│  └───────────────────────────────┘ │
│  ┌───────────────────────────────┐ │
│  │ 🥉 #3 王五                     │ │
│  │    ⏱️ 0.18s | 📅 2025-01-28   │ │
│  │    ✅ 首次通过                 │ │
│  └───────────────────────────────┘ │
│  ┌───────────────────────────────┐ │
│  │ 👤 #10 当前用户（高亮）         │ │
│  │    ⏱️ 0.25s | 📅 2025-01-27   │ │
│  │    ✅ 首次通过                 │ │
│  └───────────────────────────────┘ │
│                                     │
└─────────────────────────────────────┘
```

**说明**：
- 仅显示当前正在查看的题目的排名
- 按首次通过时间排序（最快通过的在前）
- 显示每个用户在该题目的最佳执行时间和首次通过时间

**交互行为**：
- 点击用户 → 查看该用户的详细统计（可选功能）
- 当前用户始终高亮显示

---

## 视觉设计规范

### 颜色系统（单色配色方案）

```css
:root {
    /* 背景色 */
    --bg-primary: #f5f5f7;           /* 主背景（浅灰） */
    --bg-secondary: rgba(255, 255, 255, 0.72);  /* 卡片背景（毛玻璃） */
    --bg-tertiary: rgba(255, 255, 255, 0.92);   /* 实体背景 */
    
    /* 文字颜色 */
    --text-primary: #1d1d1f;         /* 主文字（深灰） */
    --text-secondary: #6e6e73;       /* 次要文字（中灰） */
    --text-tertiary: #a1a1a6;        /* 辅助文字（浅灰） */
    
    /* 边框颜色 */
    --border-primary: rgba(0, 0, 0, 0.06);      /* 主边框 */
    --border-secondary: rgba(0, 0, 0, 0.12);    /* 次要边框 */
    
    /* 状态颜色（极简，仅用于状态指示） */
    --status-success: rgba(52, 199, 89, 0.15);  /* 成功（浅绿背景） */
    --status-error: rgba(255, 59, 48, 0.15);     /* 错误（浅红背景） */
    --status-warning: rgba(255, 149, 0, 0.15);  /* 警告（浅橙背景） */
    
    /* 阴影 */
    --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.04);
    --shadow-md: 0 8px 30px rgba(0, 0, 0, 0.06);
    --shadow-lg: 0 -8px 40px rgba(0, 0, 0, 0.12);
    
    /* 圆角 */
    --radius-sm: 12px;
    --radius-md: 18px;
    --radius-lg: 24px;
    
    /* 毛玻璃效果 */
    --blur: blur(40px) saturate(180%);
}
```

### 暗色模式（Dark Mode）

```css
body.dark-mode {
    --bg-primary: #000000;
    --bg-secondary: rgba(28, 28, 30, 0.6);
    --bg-tertiary: rgba(28, 28, 30, 0.95);
    --text-primary: #f5f5f7;
    --text-secondary: #a1a1a6;
    --text-tertiary: #6e6e73;
    --border-primary: rgba(255, 255, 255, 0.12);
    --border-secondary: rgba(255, 255, 255, 0.2);
    --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
    --shadow-md: 0 8px 30px rgba(0, 0, 0, 0.5);
    --shadow-lg: 0 -8px 40px rgba(0, 0, 0, 0.6);
}
```

### 字体系统（San Francisco）

```css
font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 
             'Helvetica Neue', Arial, sans-serif;

/* 字号 */
--font-size-xs: 11px;    /* 辅助文字 */
--font-size-sm: 13px;    /* 次要文字 */
--font-size-base: 15px;  /* 正文 */
--font-size-lg: 17px;    /* 强调文字 */
--font-size-xl: 20px;    /* 小标题 */
--font-size-2xl: 28px;   /* 大标题 */
--font-size-3xl: 34px;   /* 超大标题 */

/* 字重 */
--font-weight-regular: 400;
--font-weight-medium: 500;
--font-weight-semibold: 600;
--font-weight-bold: 700;
```

---

## 组件设计

### 1. 左侧功能栏（Sidebar Navigation）

**样式**：
- 固定定位：`position: fixed; top: 0; left: 0; bottom: 0;`
- 宽度：`280px`（极宽）
- 背景：毛玻璃效果 `rgba(255, 255, 255, 0.72)` + `backdrop-filter: blur(40px)`
- 边框：右侧 `0.5px solid var(--border-primary)`
- 阴影：`var(--shadow-md)`
- 内边距：`24px 0`
- 布局：`display: flex; flex-direction: column; gap: 8px;`

**内容**：
- 垂直排列的功能按钮
  - [题目选择] 按钮
  - [提交历史] 按钮
  - [排名] 按钮
  - [设置] 按钮（主题切换、字体大小等）

**按钮样式**：
- 宽度：`100%`
- 圆角：`var(--radius-sm)`
- 内边距：`16px 24px`
- 字体：`var(--font-size-base)`
- 字体粗细：`var(--font-weight-medium)`
- 背景：透明，悬停时 `var(--bg-tertiary)`
- 对齐：左对齐文本
- 过渡：`transition: all 0.2s ease`

**激活状态**：
- 当前激活的功能按钮高亮显示
- 背景：`var(--bg-tertiary)`
- 边框：左侧 `2px solid var(--text-primary)`

---

### 2. 抽屉组件（Drawer Component）

**HTML结构**：
```html
<!-- 遮罩层 -->
<div class="drawer-backdrop" id="drawer-backdrop"></div>

<!-- 抽屉容器 -->
<div class="drawer" id="drawer">
    <div class="drawer-header">
        <h2 class="drawer-title">标题</h2>
        <button class="drawer-close" id="drawer-close">
            <svg>...</svg>
        </button>
    </div>
    <div class="drawer-content">
        <!-- 内容区域 -->
    </div>
</div>
```

**CSS样式**：
```css
.drawer-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.3);
    backdrop-filter: blur(4px);
    z-index: 1000;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.3s ease;
}

.drawer-backdrop.active {
    opacity: 1;
    pointer-events: auto;
}

.drawer {
    position: fixed;
    top: 0;
    right: 0;
    width: 420px;
    height: 100vh;
    background: var(--bg-secondary);
    backdrop-filter: var(--blur);
    -webkit-backdrop-filter: var(--blur);
    border-left: 0.5px solid var(--border-primary);
    border-radius: var(--radius-md) 0 0 var(--radius-md);
    box-shadow: var(--shadow-lg);
    z-index: 1001;
    transform: translateX(100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.drawer.active {
    transform: translateX(0);
}

.drawer-header {
    padding: 20px 24px;
    border-bottom: 0.5px solid var(--border-primary);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-shrink: 0;
}

.drawer-title {
    font-size: var(--font-size-xl);
    font-weight: var(--font-weight-semibold);
    color: var(--text-primary);
    margin: 0;
}

.drawer-close {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: transparent;
    border: 0.5px solid var(--border-primary);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s ease;
    color: var(--text-secondary);
}

.drawer-close:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
}

.drawer-content {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
}
```

**JavaScript控制**：
```javascript
// 打开抽屉
function openDrawer(drawerId) {
    const drawer = document.getElementById(drawerId);
    const backdrop = document.getElementById('drawer-backdrop');
    drawer.classList.add('active');
    backdrop.classList.add('active');
    document.body.style.overflow = 'hidden'; // 禁止背景滚动
}

// 关闭抽屉
function closeDrawer() {
    const drawers = document.querySelectorAll('.drawer');
    const backdrop = document.getElementById('drawer-backdrop');
    drawers.forEach(d => d.classList.remove('active'));
    backdrop.classList.remove('active');
    document.body.style.overflow = ''; // 恢复滚动
}

// ESC键关闭
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeDrawer();
    }
});
```

---

### 3. 题目卡片（Question Card）

**样式**：
```css
.question-card {
    padding: 16px;
    background: var(--bg-tertiary);
    border: 0.5px solid var(--border-primary);
    border-radius: var(--radius-sm);
    margin-bottom: 12px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.question-card:hover {
    background: var(--bg-secondary);
    border-color: var(--border-secondary);
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
}

.question-card.active {
    border-color: var(--text-primary);
    background: var(--bg-secondary);
}

.question-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 8px;
}

.question-card-title {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--text-primary);
    margin: 0;
}

.question-card-meta {
    display: flex;
    gap: 12px;
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
    margin-top: 8px;
}

.question-card-status {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 4px;
    font-size: var(--font-size-xs);
    flex-shrink: 0;
}

/* 未作答：灰色虚线框 */
.question-card-status.unsolved {
    border: 2px dashed var(--text-tertiary);
    background: transparent;
    color: var(--text-tertiary);
}

/* 待评测：蓝色实心框带横线 */
.question-card-status.pending {
    background: rgba(10, 132, 255, 0.9);
    border: none;
    color: white;
    position: relative;
}

.question-card-status.pending::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 12px;
    height: 2px;
    background: white;
    border-radius: 1px;
}

/* 答案正确：红色实心框带对勾 */
.question-card-status.accepted {
    background: rgba(255, 59, 48, 0.9);
    border: none;
    color: white;
    position: relative;
}

.question-card-status.accepted::after {
    content: '✓';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 14px;
    font-weight: bold;
    color: white;
}

/* 答案错误：浅绿色实心框带X */
.question-card-status.wrong-answer {
    background: rgba(52, 199, 89, 0.8);
    border: none;
    color: white;
    position: relative;
}

.question-card-status.wrong-answer::after {
    content: '✕';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 14px;
    font-weight: bold;
    color: white;
}
```

---

### 4. 提交记录卡片（Submission Card）

**样式**：
```css
.submission-card {
    padding: 16px;
    background: var(--bg-tertiary);
    border: 0.5px solid var(--border-primary);
    border-radius: var(--radius-sm);
    margin-bottom: 12px;
    transition: all 0.2s ease;
}

.submission-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.submission-card-title {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--text-primary);
    margin: 0;
}

.submission-card-status {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    border-radius: var(--radius-sm);
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-medium);
}

.submission-card-status.accepted {
    background: var(--status-success);
    color: var(--text-primary);
}

.submission-card-status.failed {
    background: var(--status-error);
    color: var(--text-primary);
}

.submission-card-meta {
    display: flex;
    gap: 16px;
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
    margin-top: 8px;
}

.submission-card-actions {
    display: flex;
    gap: 8px;
    margin-top: 12px;
}

.submission-card-btn {
    padding: 6px 12px;
    border: 0.5px solid var(--border-primary);
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--text-primary);
    font-size: var(--font-size-sm);
    cursor: pointer;
    transition: all 0.2s ease;
}

.submission-card-btn:hover {
    background: var(--bg-secondary);
    border-color: var(--border-secondary);
}
```

---

### 5. 排名卡片（Ranking Card）

**样式**：
```css
.ranking-card {
    padding: 16px;
    background: var(--bg-tertiary);
    border: 0.5px solid var(--border-primary);
    border-radius: var(--radius-sm);
    margin-bottom: 12px;
    transition: all 0.2s ease;
}

.ranking-card.current-user {
    border-color: var(--text-primary);
    background: var(--bg-secondary);
    box-shadow: var(--shadow-sm);
}

.ranking-card-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
}

.ranking-medal {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: var(--font-size-xl);
}

.ranking-number {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--text-primary);
}

.ranking-username {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--text-primary);
    flex: 1;
}

.ranking-stats {
    display: flex;
    gap: 16px;
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
    margin-top: 8px;
}
```

---

### 6. 提交结果弹窗（Submission Result Modal）

**触发方式**：代码提交后自动弹出

**HTML结构**：
```html
<!-- 遮罩层 -->
<div class="modal-backdrop" id="submission-modal-backdrop"></div>

<!-- 提交结果弹窗 -->
<div class="submission-modal" id="submission-modal">
    <!-- 标题栏 -->
    <div class="modal-header">
        <h2 class="modal-title">提交结果</h2>
        <button class="modal-close" id="submission-modal-close">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M12 4L4 12M4 4l8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
        </button>
    </div>
    
    <!-- 提交详情网格 -->
    <div class="submission-details-grid">
        <div class="detail-item">
            <span class="detail-label">题目</span>
            <span class="detail-value" id="submission-problem">R7-2</span>
        </div>
        <div class="detail-item">
            <span class="detail-label">用户</span>
            <span class="detail-value" id="submission-user">23999183 王为硕</span>
        </div>
        <div class="detail-item">
            <span class="detail-label">编译器</span>
            <span class="detail-value" id="submission-compiler">C (gcc)</span>
        </div>
        <div class="detail-item">
            <span class="detail-label">状态</span>
            <span class="detail-value status-badge" id="submission-status">编译错误</span>
        </div>
        <div class="detail-item">
            <span class="detail-label">分数</span>
            <span class="detail-value" id="submission-score">0/10</span>
        </div>
        <div class="detail-item">
            <span class="detail-label">提交时间</span>
            <span class="detail-value" id="submission-time">2025/12/29 20:43:04</span>
        </div>
        <div class="detail-item">
            <span class="detail-label">内存</span>
            <span class="detail-value" id="submission-memory">0 / 65536 KB</span>
        </div>
        <div class="detail-item">
            <span class="detail-label">用时</span>
            <span class="detail-value" id="submission-duration">0 / 400 ms</span>
        </div>
        <div class="detail-item">
            <span class="detail-label">评测时间</span>
            <span class="detail-value" id="submission-eval-time">2025/12/29 20:43:04</span>
        </div>
    </div>
    
    <!-- 提交代码区域 -->
    <div class="submission-section">
        <div class="section-header">
            <h3 class="section-title">提交代码</h3>
            <button class="copy-btn" id="copy-code-btn">
                <span>📋</span> 复制内容
            </button>
        </div>
        <div class="code-display">
            <div class="line-numbers" id="code-line-numbers"></div>
            <pre class="code-content" id="submission-code">1 asasd</pre>
        </div>
    </div>
    
    <!-- 编译器输出区域 -->
    <div class="submission-section">
        <div class="section-header">
            <h3 class="section-title">编译器输出</h3>
        </div>
        <div class="compiler-output-display">
            <pre class="compiler-error" id="compiler-output">a.c:1:1: error: expected '=', ',', ';', 'asm' or '__attribute__' at end of input
1 | asasd
  | ^~~~~</pre>
        </div>
    </div>
    
    <!-- 确认按钮 -->
    <div class="modal-footer">
        <button class="modal-confirm-btn" id="submission-modal-confirm">确认</button>
    </div>
</div>
```

**CSS样式**：
```css
/* 遮罩层 */
.modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(8px);
    z-index: 2000;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.3s ease;
}

.modal-backdrop.active {
    opacity: 1;
    pointer-events: auto;
}

/* 提交结果弹窗 */
.submission-modal {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%) scale(0.95);
    width: 90%;
    max-width: 800px;
    max-height: 90vh;
    background: var(--bg-tertiary);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-lg);
    z-index: 2001;
    display: flex;
    flex-direction: column;
    opacity: 0;
    pointer-events: none;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    overflow: hidden;
}

.submission-modal.active {
    opacity: 1;
    pointer-events: auto;
    transform: translate(-50%, -50%) scale(1);
}

/* 标题栏 */
.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 24px;
    border-bottom: 0.5px solid var(--border-primary);
    flex-shrink: 0;
}

.modal-title {
    font-size: var(--font-size-xl);
    font-weight: var(--font-weight-semibold);
    color: var(--text-primary);
    margin: 0;
}

.modal-close {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: transparent;
    border: 0.5px solid var(--border-primary);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s ease;
    color: var(--text-secondary);
}

.modal-close:hover {
    background: var(--bg-secondary);
    color: var(--text-primary);
    border-color: var(--border-secondary);
}

/* 提交详情网格 */
.submission-details-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    padding: 24px;
    border-bottom: 0.5px solid var(--border-primary);
    background: var(--bg-primary);
}

.detail-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.detail-label {
    font-size: var(--font-size-xs);
    color: var(--text-tertiary);
    font-weight: var(--font-weight-medium);
}

.detail-value {
    font-size: var(--font-size-sm);
    color: var(--text-primary);
}

.status-badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 8px;
    border-radius: var(--radius-sm);
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-medium);
}

.status-badge.compilation-error {
    background: var(--status-error);
    color: var(--text-primary);
}

.status-badge.accepted {
    background: var(--status-success);
    color: var(--text-primary);
}

.status-badge.wrong-answer {
    background: rgba(255, 149, 0, 0.15);
    color: var(--text-primary);
}

/* 提交代码区域 */
.submission-section {
    padding: 24px;
    border-bottom: 0.5px solid var(--border-primary);
    flex-shrink: 0;
}

.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}

.section-title {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--text-primary);
    margin: 0;
}

.copy-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 6px 12px;
    border: 0.5px solid var(--border-primary);
    border-radius: var(--radius-sm);
    background: var(--bg-secondary);
    color: var(--text-primary);
    font-size: var(--font-size-xs);
    cursor: pointer;
    transition: all 0.2s ease;
}

.copy-btn:hover {
    background: var(--bg-tertiary);
    border-color: var(--border-secondary);
}

/* 代码显示区域 */
.code-display {
    display: flex;
    background: var(--bg-primary);
    border: 0.5px solid var(--border-primary);
    border-radius: var(--radius-sm);
    overflow: hidden;
    max-height: 200px;
    overflow-y: auto;
}

.code-display .line-numbers {
    width: 40px;
    padding: 12px 8px;
    background: var(--bg-secondary);
    border-right: 0.5px solid var(--border-primary);
    color: var(--text-tertiary);
    font-size: var(--font-size-sm);
    font-family: 'Monaco', 'Courier New', monospace;
    text-align: right;
    user-select: none;
    flex-shrink: 0;
}

.code-content {
    flex: 1;
    padding: 12px 16px;
    margin: 0;
    color: var(--text-primary);
    font-size: var(--font-size-sm);
    font-family: 'Monaco', 'Courier New', monospace;
    line-height: 1.6;
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-x: auto;
}

/* 编译器输出区域 */
.compiler-output-display {
    background: #1e1e1e;
    border: 0.5px solid var(--border-primary);
    border-radius: var(--radius-sm);
    padding: 16px;
    max-height: 300px;
    overflow-y: auto;
}

.compiler-error {
    margin: 0;
    color: #d4d4d4;
    font-size: var(--font-size-sm);
    font-family: 'Monaco', 'Courier New', monospace;
    line-height: 1.6;
    white-space: pre-wrap;
    word-wrap: break-word;
}

.compiler-error .error-line {
    color: #f48771;
}

.compiler-error .error-marker {
    color: #f48771;
}

/* 弹窗底部 */
.modal-footer {
    padding: 24px;
    display: flex;
    justify-content: flex-end;
    flex-shrink: 0;
}

.modal-confirm-btn {
    padding: 10px 24px;
    border: none;
    border-radius: var(--radius-sm);
    background: var(--status-success);
    color: white;
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-medium);
    cursor: pointer;
    transition: all 0.2s ease;
}

.modal-confirm-btn:hover {
    opacity: 0.9;
    transform: translateY(-1px);
}

.modal-confirm-btn:active {
    transform: translateY(0);
}
```

**JavaScript实现**：
```javascript
// 显示提交结果弹窗
function showSubmissionModal(submissionData) {
    const modal = document.getElementById('submission-modal');
    const backdrop = document.getElementById('submission-modal-backdrop');
    
    // 填充数据
    document.getElementById('submission-problem').textContent = submissionData.problem || 'N/A';
    document.getElementById('submission-user').textContent = submissionData.user || 'N/A';
    document.getElementById('submission-compiler').textContent = submissionData.compiler || 'N/A';
    document.getElementById('submission-status').textContent = getStatusText(submissionData.status);
    document.getElementById('submission-status').className = `detail-value status-badge ${getStatusClass(submissionData.status)}`;
    document.getElementById('submission-score').textContent = `${submissionData.score || 0}/${submissionData.total_score || 10}`;
    document.getElementById('submission-time').textContent = formatDateTime(submissionData.submitted_at);
    document.getElementById('submission-memory').textContent = `${submissionData.memory_used || 0} / ${submissionData.memory_limit || 65536} KB`;
    document.getElementById('submission-duration').textContent = `${submissionData.execution_time || 0} / ${submissionData.time_limit || 400} ms`;
    document.getElementById('submission-eval-time').textContent = formatDateTime(submissionData.evaluated_at || submissionData.submitted_at);
    
    // 显示提交代码
    const code = submissionData.code || '';
    const codeLines = code.split('\n');
    const lineNumbersHtml = codeLines.map((_, i) => `<span>${i + 1}</span>`).join('\n');
    document.getElementById('code-line-numbers').innerHTML = lineNumbersHtml;
    document.getElementById('submission-code').textContent = code;
    
    // 显示编译器输出
    const compilerOutput = submissionData.compiler_output || submissionData.error_message || '';
    document.getElementById('compiler-output').textContent = compilerOutput;
    
    // 显示弹窗
    modal.classList.add('active');
    backdrop.classList.add('active');
    document.body.style.overflow = 'hidden';
}

// 关闭提交结果弹窗
function closeSubmissionModal() {
    const modal = document.getElementById('submission-modal');
    const backdrop = document.getElementById('submission-modal-backdrop');
    modal.classList.remove('active');
    backdrop.classList.remove('active');
    document.body.style.overflow = '';
}

// 状态文本映射
function getStatusText(status) {
    const statusMap = {
        'accepted': '答案正确',
        'wrong_answer': '答案错误',
        'compilation_error': '编译错误',
        'runtime_error': '运行时错误',
        'time_limit_exceeded': '超时',
        'memory_limit_exceeded': '内存超限',
        'pending': '待评测'
    };
    return statusMap[status] || status;
}

// 状态样式类映射
function getStatusClass(status) {
    const classMap = {
        'accepted': 'accepted',
        'wrong_answer': 'wrong-answer',
        'compilation_error': 'compilation-error',
        'runtime_error': 'compilation-error',
        'time_limit_exceeded': 'wrong-answer',
        'memory_limit_exceeded': 'wrong-answer',
        'pending': 'wrong-answer'
    };
    return classMap[status] || 'wrong-answer';
}

// 格式化日期时间
function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    return `${year}/${month}/${day} ${hours}:${minutes}:${seconds}`;
}

// 复制代码
document.getElementById('copy-code-btn')?.addEventListener('click', () => {
    const code = document.getElementById('submission-code').textContent;
    navigator.clipboard.writeText(code).then(() => {
        const btn = document.getElementById('copy-code-btn');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<span>✓</span> 已复制';
        setTimeout(() => {
            btn.innerHTML = originalText;
        }, 2000);
    });
});

// 关闭按钮事件
document.getElementById('submission-modal-close')?.addEventListener('click', closeSubmissionModal);
document.getElementById('submission-modal-confirm')?.addEventListener('click', closeSubmissionModal);
document.getElementById('submission-modal-backdrop')?.addEventListener('click', closeSubmissionModal);

// ESC键关闭
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const modal = document.getElementById('submission-modal');
        if (modal.classList.contains('active')) {
            closeSubmissionModal();
        }
    }
});
```

**交互行为**：
- 代码提交后自动弹出提交结果弹窗
- 点击"复制内容"按钮 → 复制提交的代码到剪贴板
- 点击"确认"按钮或关闭按钮 → 关闭弹窗
- 点击遮罩层 → 关闭弹窗
- 按 `ESC` 键 → 关闭弹窗
- 弹窗内容可滚动查看

---

### 7. Debug窗口（Debug Panel）

**位置**：代码编辑器区域下方，点击Debug按钮后展开

**HTML结构**：
```html
<div class="editor-panel">
    <!-- 编辑器工具栏 -->
    <div class="editor-toolbar">
        <div class="toolbar-left">
            <!-- 语言选择、上一题/下一题 -->
        </div>
        <button class="debug-toggle-btn" id="debug-toggle">
            <span>🐛</span> Debug
        </button>
    </div>
    
    <!-- Monaco Editor -->
    <div id="monaco-editor"></div>
    
    <!-- 操作按钮区域 -->
    <div class="editor-actions">
        <!-- 测试用例、提交、重置按钮 -->
    </div>
    
    <!-- 输出面板 -->
    <div class="output-panel">
        <!-- 执行结果、判题结果 -->
    </div>
    
    <!-- Debug窗口（可折叠） -->
    <div class="debug-panel" id="debug-panel">
        <div class="debug-tabs">
            <button class="debug-tab active" data-tab="testcase">测试用例</button>
            <button class="debug-tab" data-tab="compiler">编译器输出</button>
            <button class="debug-copy-btn">
                <span>📋</span> 复制内容
            </button>
        </div>
        
        <!-- 测试用例标签页 -->
        <div class="debug-content" id="debug-testcase">
            <div class="testcase-input">
                <div class="line-numbers">
                    <span>1</span>
                </div>
                <textarea 
                    class="testcase-textarea" 
                    id="testcase-input"
                    placeholder="输入测试用例..."
                >50800</textarea>
            </div>
            <div class="debug-actions">
                <button class="debug-reset-btn">重置测试用例</button>
                <button class="debug-run-btn">
                    <span>▶</span> 运行测试
                </button>
            </div>
            <div class="debug-status">
                <span class="status-text">上一次测试于 5 秒前 非零返回</span>
                <button class="view-last-case-btn">查看上次用例</button>
            </div>
        </div>
        
        <!-- 编译器输出标签页 -->
        <div class="debug-content" id="debug-compiler" style="display: none;">
            <div class="compiler-output">
                <div class="line-numbers">
                    <span>1</span>
                    <span>2</span>
                    <span>3</span>
                    <span>4</span>
                    <span>5</span>
                </div>
                <pre class="compiler-text">
Traceback (most recent call last):
  File "/tmp/a.py", line 6, in &lt;module&gt;
    print("{:.2f}".format(salary(sales)))
NameError: name 'salary' is not defined
                </pre>
            </div>
        </div>
    </div>
</div>
```

**CSS样式**：
```css
/* Debug按钮 */
.debug-toggle-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border: 0.5px solid var(--border-primary);
    border-radius: var(--radius-sm);
    background: var(--bg-tertiary);
    color: var(--text-primary);
    font-size: var(--font-size-sm);
    cursor: pointer;
    transition: all 0.2s ease;
}

.debug-toggle-btn:hover {
    background: var(--bg-secondary);
    border-color: var(--border-secondary);
}

.debug-toggle-btn.active {
    background: var(--status-warning);
    border-color: var(--status-warning);
}

/* Debug窗口 */
.debug-panel {
    display: none;
    border-top: 0.5px solid var(--border-primary);
    background: var(--bg-primary);
    max-height: 400px;
    overflow: hidden;
    flex-direction: column;
}

.debug-panel.active {
    display: flex;
}

/* Debug标签页 */
.debug-tabs {
    display: flex;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 0.5px solid var(--border-primary);
    background: var(--bg-tertiary);
    gap: 8px;
}

.debug-tab {
    padding: 8px 16px;
    border: none;
    border-bottom: 2px solid transparent;
    background: transparent;
    color: var(--text-secondary);
    font-size: var(--font-size-sm);
    cursor: pointer;
    transition: all 0.2s ease;
}

.debug-tab:hover {
    color: var(--text-primary);
}

.debug-tab.active {
    color: var(--text-primary);
    border-bottom-color: var(--text-primary);
}

.debug-copy-btn {
    margin-left: auto;
    padding: 6px 12px;
    border: 0.5px solid var(--border-primary);
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--text-secondary);
    font-size: var(--font-size-xs);
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 4px;
}

.debug-copy-btn:hover {
    background: var(--bg-secondary);
    color: var(--text-primary);
}

/* Debug内容区域 */
.debug-content {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
}

.debug-content.active {
    display: flex;
}

/* 测试用例输入区域 */
.testcase-input {
    display: flex;
    flex: 1;
    background: var(--bg-tertiary);
    border-bottom: 0.5px solid var(--border-primary);
}

.line-numbers {
    width: 40px;
    padding: 12px 8px;
    background: var(--bg-primary);
    border-right: 0.5px solid var(--border-primary);
    color: var(--text-tertiary);
    font-size: var(--font-size-sm);
    font-family: 'Monaco', 'Courier New', monospace;
    text-align: right;
    user-select: none;
    display: flex;
    flex-direction: column;
    gap: 0;
}

.testcase-textarea {
    flex: 1;
    padding: 12px 16px;
    border: none;
    background: transparent;
    color: var(--text-primary);
    font-size: var(--font-size-sm);
    font-family: 'Monaco', 'Courier New', monospace;
    resize: none;
    outline: none;
    line-height: 1.6;
}

.testcase-textarea::placeholder {
    color: var(--text-tertiary);
}

/* Debug操作按钮 */
.debug-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: var(--bg-tertiary);
    border-bottom: 0.5px solid var(--border-primary);
    gap: 12px;
}

.debug-reset-btn {
    padding: 8px 16px;
    border: 0.5px solid var(--border-primary);
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--text-secondary);
    font-size: var(--font-size-sm);
    cursor: pointer;
    transition: all 0.2s ease;
}

.debug-reset-btn:hover {
    background: var(--bg-secondary);
    color: var(--text-primary);
}

.debug-run-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 20px;
    border: none;
    border-radius: var(--radius-sm);
    background: var(--status-success);
    color: white;
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    cursor: pointer;
    transition: all 0.2s ease;
}

.debug-run-btn:hover {
    opacity: 0.9;
    transform: translateY(-1px);
}

.debug-run-btn:active {
    transform: translateY(0);
}

/* Debug状态栏 */
.debug-status {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 16px;
    background: var(--bg-primary);
    border-top: 0.5px solid var(--border-primary);
    font-size: var(--font-size-xs);
    color: var(--text-secondary);
}

.status-text {
    flex: 1;
}

.view-last-case-btn {
    padding: 4px 12px;
    border: 0.5px solid var(--border-primary);
    border-radius: var(--radius-sm);
    background: var(--bg-tertiary);
    color: var(--text-primary);
    font-size: var(--font-size-xs);
    cursor: pointer;
    transition: all 0.2s ease;
}

.view-last-case-btn:hover {
    background: var(--bg-secondary);
}

/* 编译器输出 */
.compiler-output {
    display: flex;
    flex: 1;
    background: var(--bg-tertiary);
}

.compiler-text {
    flex: 1;
    padding: 12px 16px;
    margin: 0;
    color: var(--text-primary);
    font-size: var(--font-size-sm);
    font-family: 'Monaco', 'Courier New', monospace;
    line-height: 1.6;
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-x: auto;
}
```

**JavaScript实现**：
```javascript
// Debug窗口切换
const debugToggleBtn = document.getElementById('debug-toggle');
const debugPanel = document.getElementById('debug-panel');
const debugTabs = document.querySelectorAll('.debug-tab');
const debugContents = document.querySelectorAll('.debug-content');

debugToggleBtn.addEventListener('click', () => {
    debugPanel.classList.toggle('active');
    debugToggleBtn.classList.toggle('active');
    
    // 调整编辑器高度
    if (debugPanel.classList.contains('active')) {
        editor.layout({ height: window.innerHeight - 400 });
    } else {
        editor.layout({ height: window.innerHeight - 200 });
    }
});

// 标签页切换
debugTabs.forEach(tab => {
    tab.addEventListener('click', () => {
        const targetTab = tab.dataset.tab;
        
        // 更新标签页状态
        debugTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        
        // 更新内容显示
        debugContents.forEach(content => {
            content.style.display = 'none';
        });
        
        const targetContent = document.getElementById(`debug-${targetTab}`);
        if (targetContent) {
            targetContent.style.display = 'flex';
        }
    });
});

// 运行测试
const debugRunBtn = document.querySelector('.debug-run-btn');
const testcaseInput = document.getElementById('testcase-input');

debugRunBtn.addEventListener('click', async () => {
    const code = editor.getValue();
    const input = testcaseInput.value;
    
    // 调用API执行代码
    const response = await fetch('/coding/api/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, input, language: 'python' })
    });
    
    const result = await response.json();
    
    // 切换到编译器输出标签页
    document.querySelector('[data-tab="compiler"]').click();
    
    // 显示输出结果
    const compilerText = document.querySelector('.compiler-text');
    if (result.data.error) {
        compilerText.textContent = result.data.error;
        compilerText.style.color = 'var(--status-error)';
    } else {
        compilerText.textContent = result.data.output;
        compilerText.style.color = 'var(--text-primary)';
    }
    
    // 更新状态栏
    const statusText = document.querySelector('.status-text');
    const now = new Date();
    statusText.textContent = `上一次测试于 ${now.toLocaleTimeString()} ${result.data.status_code === 'success' ? '成功' : '非零返回'}`;
});

// 重置测试用例
const debugResetBtn = document.querySelector('.debug-reset-btn');
debugResetBtn.addEventListener('click', () => {
    testcaseInput.value = '';
    testcaseInput.focus();
});
```

**交互行为**：
- 点击Debug按钮 → 展开/收起Debug窗口
- 点击"测试用例"标签 → 显示测试用例输入区域
- 点击"编译器输出"标签 → 显示代码执行输出
- 输入测试用例 → 支持多行输入
- 点击"运行测试" → 执行代码并显示结果
- 点击"重置测试用例" → 清空输入框
- 点击"查看上次用例" → 恢复上次输入的测试用例

---

## 响应式设计

### 移动端适配

**断点**：`max-width: 768px`

**调整**：
1. **左侧功能栏**：
   - 默认隐藏，通过汉堡菜单按钮触发显示
   - 显示时覆盖在主内容上方（全屏宽度）
   - 或改为底部导航栏（移动端常见模式）

2. **主布局**：
   - 移除左侧功能栏的固定宽度（`margin-left: 0`）
   - 垂直堆叠（题目描述在上，代码编辑器在下）
   - 可拖拽分割线改为垂直方向（调整上下区域高度）

3. **抽屉宽度**：`85vw`（最大`420px`）

4. **字体大小**：适当缩小

5. **内边距**：减少到 `16px`

6. **可拖拽分割线**：
   - 移动端改为垂直方向（调整上下区域高度）
   - 或禁用拖拽功能，使用固定比例布局

---

## 动画效果

### 1. 抽屉打开/关闭动画

```css
.drawer {
    transform: translateX(100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.drawer.active {
    transform: translateX(0);
}
```

### 2. 卡片悬停动画

```css
.question-card {
    transition: all 0.2s ease;
}

.question-card:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
}
```

### 3. 按钮点击反馈

```css
.btn {
    transition: all 0.15s ease;
}

.btn:active {
    transform: scale(0.98);
}
```

---

## 交互细节

### 1. 键盘快捷键

- `ESC`：关闭当前打开的抽屉
- `Ctrl/Cmd + K`：打开题目选择抽屉（可选）
- `Ctrl/Cmd + H`：打开提交历史抽屉（可选）
- `Ctrl/Cmd + R`：打开排名抽屉（可选）

### 2. 触摸手势（移动端）

- 从右侧向左滑动：打开抽屉
- 从左侧向右滑动：关闭抽屉
- 滑动距离超过 `30%`：触发关闭

### 3. 焦点管理

- 打开抽屉时，焦点自动移动到抽屉内的第一个可交互元素
- 关闭抽屉时，焦点返回到触发按钮

---

## 技术实现要点

### 1. 状态管理

使用简单的 JavaScript 对象管理抽屉状态：

```javascript
const drawerState = {
    questionDrawer: false,
    submissionDrawer: false,
    rankingDrawer: false
};
```

### 2. API 调用

- 题目列表：`GET /coding/api/questions`（返回题目状态：全对/未全对/未作）
- 当前题目提交历史：`GET /coding/api/submissions?question_id={current_question_id}`
- 当前题目排名：`GET /coding/api/rankings?question_id={current_question_id}`

### 3. 可拖拽分割线实现

**HTML结构**：
```html
<div class="main-content">
    <div class="question-panel" id="question-panel">
        <!-- 题目描述内容 -->
    </div>
    <div class="resizer" id="resizer"></div>
    <div class="editor-panel" id="editor-panel">
        <!-- 代码编辑器内容 -->
    </div>
</div>
```

**CSS样式**：
```css
.main-content {
    display: flex;
    height: calc(100vh - 60px);
    margin-left: 280px; /* 左侧功能栏宽度 */
}

.question-panel {
    flex: 1;
    min-width: 300px;
    max-width: calc(100% - 300px);
    overflow-y: auto;
}

.editor-panel {
    flex: 1;
    min-width: 300px;
    max-width: calc(100% - 300px);
    overflow-y: auto;
}

.resizer {
    width: 4px;
    background: var(--border-primary);
    cursor: col-resize;
    transition: background 0.2s ease;
    flex-shrink: 0;
}

.resizer:hover {
    background: var(--border-secondary);
}
```

**JavaScript实现**：
```javascript
let isResizing = false;
let startX = 0;
let startWidth = 0;

const resizer = document.getElementById('resizer');
const questionPanel = document.getElementById('question-panel');
const editorPanel = document.getElementById('editor-panel');

resizer.addEventListener('mousedown', (e) => {
    isResizing = true;
    startX = e.clientX;
    startWidth = questionPanel.offsetWidth;
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    resizer.style.background = 'var(--border-secondary)';
});

function handleMouseMove(e) {
    if (!isResizing) return;
    const diff = e.clientX - startX;
    const newWidth = startWidth + diff;
    const containerWidth = questionPanel.parentElement.offsetWidth;
    const minWidth = 300;
    const maxWidth = containerWidth - 300;
    
    if (newWidth >= minWidth && newWidth <= maxWidth) {
        questionPanel.style.width = `${newWidth}px`;
        questionPanel.style.flex = 'none';
        editorPanel.style.flex = '1';
    }
}

function handleMouseUp() {
    isResizing = false;
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
    resizer.style.background = 'var(--border-primary)';
    
    // 保存宽度到 localStorage
    localStorage.setItem('questionPanelWidth', questionPanel.style.width);
}

// 页面加载时恢复保存的宽度
window.addEventListener('load', () => {
    const savedWidth = localStorage.getItem('questionPanelWidth');
    if (savedWidth) {
        questionPanel.style.width = savedWidth;
        questionPanel.style.flex = 'none';
    }
});
```

### 4. 性能优化

- 抽屉内容懒加载（打开时才加载）
- 虚拟滚动（题目列表超过100条时）
- 分割线宽度保存到 localStorage，页面刷新后恢复

---

## 实施步骤

1. **第一阶段**：重构主布局，添加左侧功能栏（极宽侧边栏）
2. **第二阶段**：实现可拖拽分割线，支持题目描述区域和代码编辑器区域宽度调整
3. **第三阶段**：实现抽屉组件基础框架
4. **第四阶段**：实现题目选择抽屉（简化版，仅显示题目列表和状态）
5. **第五阶段**：实现提交历史抽屉（仅显示当前题目提交历史）
6. **第六阶段**：实现排名抽屉（仅显示当前题目排名）
7. **第七阶段**：优化动画和交互细节
8. **第八阶段**：响应式适配和测试

---

## 设计亮点

1. **极简主义**：去除冗余元素，聚焦核心功能
2. **毛玻璃效果**：现代化的视觉体验
3. **抽屉式交互**：不占用主界面空间，按需展示
4. **单色配色**：符合 iOS 18 设计规范
5. **流畅动画**：提升用户体验
6. **响应式设计**：适配各种设备

---

**设计完成日期**：2025-01-29  
**设计版本**：v1.0

