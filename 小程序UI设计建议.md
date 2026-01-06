# 小程序 UI/交互设计建议（参考稿）

> 目标：在不大改现有功能结构的前提下，让整体视觉更统一、更“iOS 18 极简/玻璃感”、信息层级更清晰、交互更顺手。

## 1. 设计方向（统一的“审美基线”）

### 1.1 关键词
- **黑白灰为主**：尽量不用高饱和色，靠层级/留白/对比度来表达重点。
- **轻玻璃拟态**：半透明白卡片 + 轻描边 + 轻阴影；能 blur 就 blur，不能 blur 也要优雅降级。
- **内容优先**：题目/选项/进度是主角，装饰性元素减少。
- **克制的动效**：`scale(0.98)` + `opacity` 就足够，避免花哨过渡。

### 1.2 你现在已有的好基因（建议扩展到全站）
从 `miniprogram-1/miniprogram/pages/index/index.less`、`miniprogram-1/miniprogram/pages/subjects/subjects.less` 能看出你已经在用：
- `page` 固定高度 + `scroll-view` 内部滚动（避免全页滚动）
- 卡片圆角 22rpx、轻边框、轻阴影、透明白背景、`backdrop-filter`

建议把这些“首页/科目页”的风格，作为全局基线，逐步把其它页面（练习/考试/绑定等）对齐。

---

## 2. 设计 Token（颜色/圆角/阴影/间距/字号）

> 建议把以下值视为“默认值”，页面只在必要时覆盖。这样能快速统一观感。

### 2.1 颜色（建议）
- 页面背景：`#F2F2F7`
- 卡片底：`rgba(255,255,255,0.86)`（需要玻璃感时：`0.72`~`0.86`）
- 细边框：`rgba(0,0,0,0.06)`（或系统灰：`rgba(60,60,67,0.12)`）
- 主文字：`#111111`
- 次文字：`rgba(60,60,67,0.6)`
- 禁用/弱化：`rgba(60,60,67,0.35)`

> 关于强调色：能用黑白灰表达就不用蓝色；如果必须区分“正确/错误”，也建议用**低饱和**的绿/红（少用、面积小、只在结果态出现）。

### 2.2 圆角（建议）
- 大卡片：`22rpx`
- 按钮/输入：`18rpx`
- 胶囊（tag/chip）：`999rpx`

### 2.3 阴影（建议）
- 卡片默认：`0 10rpx 26rpx rgba(0,0,0,0.05)`
- Hero/强调卡：`0 12rpx 34rpx rgba(0,0,0,0.06)`

### 2.4 间距（建议）
- 页面左右内边距：`24rpx`
- 卡片内边距：`18~20rpx`
- 栅格间距：`12rpx`
- 组件垂直间距：`16rpx`

### 2.5 字号/字重（建议）
- 大标题：`36rpx` / `700`
- 小标题：`30~32rpx` / `700~800`
- 正文：`28rpx` / `400~600`
- 辅助：`24~26rpx` / `400~600`

---

## 3. 页面布局规范（强烈建议统一）

### 3.1 结构规则
固定顶部导航 +（如有）固定底部操作区；**只有内容区滚动**。

推荐结构（WXML）：

```xml
<view class="page-root">
  <navigation-bar title="标题" back="{{true}}" color="black" background="#FFF"></navigation-bar>
  <view class="page-container">
    <scroll-view class="content-area" scroll-y type="list" bounces="{{false}}">
      <view class="container">
        <!-- 内容 -->
      </view>
    </scroll-view>
    <!-- 如果需要固定底部操作区：放在 scroll-view 外 -->
    <!-- <view class="bottom-actions">...</view> -->
  </view>
</view>
```

对应样式（LESS/WXSS）建议固定为一套（几乎所有页可复用）：

```less
page { height: 100vh; overflow: hidden; }
.page-root { height: 100vh; display: flex; flex-direction: column; overflow: hidden; background: #F2F2F7; }
.page-container { flex: 1; min-height: 0; overflow: hidden; display: flex; flex-direction: column; }
.content-area { flex: 1; min-height: 0; height: 0; }
.container { padding: 24rpx; padding-bottom: calc(40rpx + env(safe-area-inset-bottom)); box-sizing: border-box; width: 100%; }
.bottom-actions { flex: none; padding: 16rpx 24rpx calc(16rpx + env(safe-area-inset-bottom)); background: rgba(255,255,255,0.86); border-top: 1rpx solid rgba(0,0,0,0.06); }
```

### 3.2 响应式关键点（避免卡片“挤爆/溢出”）
- 列表/卡片容器统一加：`box-sizing: border-box; width: 100%;`
- Flex 子项避免文字撑破：在需要省略的容器上加 `min-width: 0;`
- 需要滚动的 flex 子项：加 `min-height: 0;`（你现在的首页已经做对了）

---

## 4. 组件级建议（做“统一感”的最快路径）

### 4.1 卡片 Card
统一卡片基类（建议在后续抽公共样式时复用）：
- 背景：`rgba(255,255,255,0.86)`
- 边框：`1rpx solid rgba(0,0,0,0.06)`
- 圆角：`22rpx`
- 阴影：`0 10rpx 26rpx rgba(0,0,0,0.05)`

### 4.2 按钮 Button
- 主按钮：黑底白字（`#111` / `#fff`），高度 `72~88rpx`，`font-weight: 700`
- 次按钮：浅灰底/描边（`rgba(60,60,67,0.08)` + 细边框）
- 危险操作：尽量“低调红”（小面积、仅关键节点出现），避免大红底块铺满

### 4.3 Tag/Chip（筛选/科目/章节）
- 默认灰底灰字（不要蓝色高亮铺底）
- 选中态建议：**描边更深 + 字重更高**，必要时再加轻微底色变化

### 4.4 输入框 Input
- 高度建议 `72~76rpx`，圆角 `18rpx`
- 背景用 `rgba(60,60,67,0.08)`，别用纯白（会显“硬”）

### 4.5 空/错/加载三态（很多页面质感差就差在这）
- **空状态**：一段简短说明 + 一个明确动作（去选择科目/去搜索/去开始练习）
- **错误状态**：同样提供“重试”按钮；避免只吐一个 toast
- **加载状态**：优先骨架屏（灰块）而不是转圈；如果用转圈，颜色用灰，不用亮蓝

---

## 5. 页面级落地建议（按优先级）

### 5.1 练习/考试相关页（最值得统一）
你现在部分页面还在用 `#007AFF`、动效涟漪、较强的色彩提示，建议逐步改为：
- “选择态/可点击态”主要靠：**描边/阴影/字重/轻微缩放**
- 正确/错误只在“结果态”出现，且用低饱和色，面积尽量小（例如：选项左侧细条/小角标）
- 底部操作区（上一题/提交/下一题）固定在页面底部，按钮样式与首页主按钮一致

### 5.2 我的/登录/绑定页（最容易“看起来简陋”）
- 用一张“Hero Card”（头像 + 昵称 + 状态）做顶部信息锚点（你首页的 hero-card 风格可以复用）
- 绑定/登录的主流程：尽量一屏内完成，减少杂项说明文本
- 表单项统一输入框样式，按钮统一主/次按钮样式

### 5.3 题目列表/错题本/收藏
- 列表项建议卡片化或“半卡片化”（白底 + 细分割线），让信息层级更清晰
- 筛选条用 chip，选中态不要大面积蓝色底
- 支持长标题/多行时：使用 `-webkit-line-clamp`，避免布局抖动

---

## 6. 推进方式（不大动结构也能快速变好看）

### 6.1 一次性先做“统一外壳”
优先把所有页面对齐到同一套：
- 页面背景色
- 统一的 `page-root/page-container/content-area/container` 布局
- 统一卡片样式（圆角/阴影/边框/透明度）

### 6.2 再逐步统一组件
先从出现频率最高的三类开始：
- 卡片（列表、模块、信息区）
- 主按钮/次按钮
- tag/chip（筛选、分类）

---

## 7. 自查清单（每做完一个页面过一遍）
- 是否只有内容区滚动（`scroll-view`），没有全页滚动？
- 是否统一背景色、统一容器 padding（24rpx）？
- 卡片是否全宽、无溢出、`box-sizing: border-box`、必要处 `min-width: 0`？
- 颜色是否克制（黑白灰为主），强调色是否“少量且必要”？
- 空/错/加载三态是否都有（并且有明确动作）？
- 主要点击区域高度是否 ≥ `72rpx`（更推荐 `88rpx`）？

