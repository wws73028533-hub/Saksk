# 答题页键盘快捷键（可自定义）

本项目的答题页（`/quiz`）支持键盘快捷键，并在「设置 → 快捷键」中支持自定义，且支持组合键（如 `Ctrl+Shift+KeyN`）。

## 1. 默认快捷键

> 快捷键以 `KeyboardEvent.code` 为主（例如 `KeyF`、`Digit1`、`ArrowLeft`），组合键以 `Ctrl/Alt/Shift/Meta + code` 表示。

| 功能 | 默认值 | 说明 |
|---|---|---|
| 上一题 | `ArrowLeft` | 切到上一题 |
| 下一题 | `ArrowRight` | 切到下一题 |
| 收藏/取消收藏 | `KeyF` | 切换当前题目收藏状态 |
| 选项 1 | `Digit1` | 选择题/判断题：选择第 1 个选项（A/对） |
| 选项 2 | `Digit2` | 选择题：选择第 2 个选项（B/错） |
| 选项 3 | `Digit3` | 选择题：选择第 3 个选项（C） |
| 选项 4 | `Digit4` | 选择题：选择第 4 个选项（D） |
| 填空：上一个挖空 | `ArrowUp` | **当填空输入框聚焦时**切换到上一个空 |
| 填空：下一个挖空 | `ArrowDown` | **当填空输入框聚焦时**切换到下一个空 |
| 提交/查看结果/下一题 | `Enter` | 保持与原逻辑一致：优先“下一题”，其次“查看结果” |

## 2. 自定义录入规则

- 在设置页中点击某一项的输入框，然后直接按下想要的组合键。
- 支持组合键：`Ctrl` / `Alt` / `Shift` / `Meta(Win/⌘)` + 任意键。
- 按 `Backspace` 或 `Delete` 可清空该项。
- 注意：
  - 与浏览器/系统已占用的组合键（例如 `Ctrl+W`、`Cmd+Q` 等）可能无法被网页捕获，属于正常现象。
  - 为保证跨键盘布局一致性，使用 `KeyboardEvent.code`，因此字母键通常显示为 `KeyX`（代表键位），而不是输入字符。

## 3. 存储位置

- 本地：`localStorage['quiz_hotkeys_v1']`
- 同步：设置页会随其它偏好一起通过 `/api/progress` 进行跨设备同步（登录状态下）。

## 4. 相关代码位置

- 设置页：`app/modules/main/templates/main/settings/hotkeys.html`
- 快捷键逻辑：`app/modules/quiz/templates/quiz/partials/quiz/_inline_js.html`

