# 编程题模块需求与功能分析文档

## 1. 模块概述

### 1.1 设计原则

- **独立性**：编程题模块是完全独立的功能模块，不与其他模块（quiz、exam、chat）混合
- **模块化**：采用模块化设计，每个功能子模块都有独立的文件夹
- **可扩展性**：支持多种编程语言（初期支持Python，后续可扩展Java、C++等）
- **安全性**：代码执行采用沙箱环境，防止恶意代码执行

### 1.2 模块定位

编程题模块是一个独立的在线编程练习平台，提供：
- 编程题目浏览与筛选
- 在线代码编辑与执行
- 自动判题与测试用例验证
- 提交历史与统计
- 题目收藏与错题记录

### 1.3 技术栈

- **后端**：Flask + Flask-RESTful
- **前端**：原生HTML/CSS/JavaScript + Monaco Editor（代码编辑器）
- **代码执行**：Python subprocess（开发环境）/ Docker（生产环境）
- **数据库**：SQLite（通过 `utils.database.get_db()` 访问）
- **UI风格**：iOS 18风格，毛玻璃效果，简约设计

---

## 2. 模块结构设计

### 2.1 目录结构

```
app/
├── modules/                          # 新建：模块化功能目录
│   └── coding/                      # 编程题模块（完全独立）
│       ├── __init__.py              # 模块初始化
│       ├── routes/                  # 路由层
│       │   ├── __init__.py
│       │   ├── pages.py             # 页面路由（列表页、详情页等）
│       │   ├── api.py               # API路由（题目、提交、执行等）
│       │   └── admin.py             # 管理端路由（题目管理）
│       ├── services/                # 服务层
│       │   ├── __init__.py
│       │   ├── question_service.py # 题目服务（CRUD、查询）
│       │   ├── submission_service.py # 提交服务（提交记录、统计）
│       │   ├── judge_service.py    # 判题服务（测试用例验证）
│       │   └── code_executor.py    # 代码执行服务（从app/services迁移）
│       ├── models/                  # 数据模型层
│       │   ├── __init__.py
│       │   ├── coding_question.py   # 编程题模型
│       │   └── code_submission.py   # 代码提交模型
│       ├── schemas/                 # 数据验证层（Pydantic）
│       │   ├── __init__.py
│       │   ├── question_schemas.py  # 题目相关Schema
│       │   └── submission_schemas.py # 提交相关Schema
│       ├── utils/                   # 工具函数
│       │   ├── __init__.py
│       │   ├── validators.py       # 代码验证器（从app/utils迁移）
│       │   └── formatters.py       # 输出格式化
│       └── templates/               # 模板文件
│           ├── coding/
│           │   ├── base.html       # 基础模板
│           │   ├── index.html      # 题目列表页
│           │   ├── detail.html     # 题目详情页（编辑+执行）
│           │   ├── submissions.html # 提交历史页
│           │   └── statistics.html  # 统计页面
│           └── admin/
│               └── coding/
│                   ├── questions.html    # 题目管理页
│                   └── question_form.html # 题目编辑表单
```

### 2.2 模块注册

在 `app/__init__.py` 中注册模块：

```python
from app.modules.coding import init_coding_module

def create_app(config_name='development'):
    app = Flask(__name__)
    # ... 其他初始化 ...
    
    # 注册编程题模块
    init_coding_module(app)
    
    return app
```

---

## 3. 功能需求分析

### 3.1 用户端功能

#### 3.1.1 题目列表页 (`/coding`)

**功能描述**：
- 显示所有编程题列表
- 支持按科目、难度、状态筛选
- 显示题目基本信息（标题、难度、通过率、提交次数）
- 支持搜索功能

**页面元素**：
- 筛选器（科目下拉、难度选择、状态筛选）
- 搜索框
- 题目卡片列表
- 分页器

**数据字段**：
- 题目ID
- 题目标题
- 科目名称
- 难度等级（简单/中等/困难）
- 通过率（已通过人数/总提交人数）
- 提交次数
- 收藏状态
- 完成状态（未开始/进行中/已通过）

#### 3.1.2 题目详情页 (`/coding/<question_id>`)

**功能描述**：
- 显示题目完整信息（描述、示例、约束条件）
- 在线代码编辑器（Monaco Editor）
- 代码执行功能（运行测试用例）
- 提交代码功能（自动判题）
- 查看提交历史

**页面布局**：
- 左侧：题目描述区域
  - 题目标题
  - 题目描述（Markdown渲染）
  - 输入输出示例
  - 约束条件
  - 提示信息
- 右侧：代码编辑区域
  - 代码编辑器（Monaco Editor）
  - 工具栏（运行、提交、重置、格式化）
  - 输出面板（执行结果、测试用例结果）
  - 提交历史（最近提交记录）

**交互功能**：
- 代码自动保存（LocalStorage）
- 代码模板加载
- 运行代码（不判题，仅执行）
- 提交代码（自动判题，记录提交）
- 查看历史提交记录
- 收藏/取消收藏题目

#### 3.1.3 提交历史页 (`/coding/submissions`)

**功能描述**：
- 显示用户的所有提交记录
- 支持按题目、状态、时间筛选
- 显示提交详情（代码、结果、执行时间）

**数据字段**：
- 提交ID
- 题目标题
- 提交时间
- 执行状态（通过/失败/错误/超时）
- 通过测试用例数/总测试用例数
- 执行时间
- 代码语言

**操作**：
- 查看提交详情
- 重新提交（加载历史代码）
- 删除提交记录

#### 3.1.4 统计页面 (`/coding/statistics`)

**功能描述**：
- 显示用户编程题练习统计
- 题目完成情况
- 提交成功率
- 各难度题目分布

**统计指标**：
- 总提交次数
- 通过题目数
- 总题目数
- 提交成功率
- 各难度题目完成情况

### 3.2 管理端功能

#### 3.2.1 题目管理页 (`/admin/coding/questions`)

**功能描述**：
- 编程题列表（表格展示）
- 创建、编辑、删除题目
- 批量操作（删除、导出）
- 题目状态管理（启用/禁用）

**管理功能**：
- 创建题目（表单）
- 编辑题目（表单）
- 删除题目（确认对话框）
- 批量删除
- 导入/导出题目（JSON格式）
- 预览题目（查看题目详情）

#### 3.2.2 题目编辑表单

**表单字段**：
- 题目标题（必填）
- 科目选择（下拉）
- 难度等级（简单/中等/困难）
- 题目描述（Markdown编辑器）
- 输入输出示例（JSON格式）
- 代码模板（代码编辑器）
- 编程语言（Python/Java/C++等，初期仅Python）
- 时间限制（秒，默认5秒）
- 内存限制（MB，默认128MB）
- 测试用例（JSON格式，包含输入输出）
- 提示信息（可选）
- 是否启用（开关）

**测试用例格式**：
```json
{
  "test_cases": [
    {
      "input": "1\n2",
      "output": "3",
      "description": "示例1"
    },
    {
      "input": "10\n20",
      "output": "30",
      "description": "示例2"
    }
  ],
  "hidden_cases": [
    {
      "input": "100\n200",
      "output": "300"
    }
  ]
}
```

---

## 4. 数据库设计

### 4.1 数据表

#### 4.1.1 `questions` 表（复用现有表，添加编程题字段）

**编程题相关字段**：
- `code_template` (TEXT): 代码模板
- `programming_language` (TEXT): 编程语言（python/java/cpp等）
- `time_limit` (INTEGER): 时间限制（秒）
- `memory_limit` (INTEGER): 内存限制（MB）
- `test_cases_json` (TEXT): 测试用例（JSON格式）
- `difficulty` (TEXT): 难度等级（easy/medium/hard）
- `is_enabled` (INTEGER): 是否启用（0/1）

**注意**：这些字段已存在于 `questions` 表中，通过 `q_type='编程题'` 区分。

#### 4.1.2 `code_submissions` 表（已存在）

**字段说明**：
- `id` (INTEGER PRIMARY KEY): 提交ID
- `user_id` (INTEGER): 用户ID
- `question_id` (INTEGER): 题目ID
- `code` (TEXT): 提交的代码
- `language` (TEXT): 编程语言
- `status` (TEXT): 提交状态（accepted/wrong_answer/time_limit_exceeded/runtime_error/compilation_error）
- `passed_cases` (INTEGER): 通过的测试用例数
- `total_cases` (INTEGER): 总测试用例数
- `execution_time` (REAL): 执行时间（秒）
- `error_message` (TEXT): 错误信息
- `submitted_at` (DATETIME): 提交时间

#### 4.1.3 新增表：`coding_statistics`（可选）

**字段说明**：
- `id` (INTEGER PRIMARY KEY): 统计ID
- `user_id` (INTEGER): 用户ID
- `question_id` (INTEGER): 题目ID
- `total_submissions` (INTEGER): 总提交次数
- `accepted_submissions` (INTEGER): 通过次数
- `best_time` (REAL): 最佳执行时间
- `first_accepted_at` (DATETIME): 首次通过时间
- `last_submitted_at` (DATETIME): 最后提交时间
- `updated_at` (DATETIME): 更新时间

**用途**：用于快速查询用户统计信息，避免每次计算。

---

## 5. API设计

### 5.1 用户端API

#### 5.1.1 题目相关API

**获取题目列表**
```
GET /coding/api/questions
Query Parameters:
  - subject: 科目名称（可选）
  - difficulty: 难度（easy/medium/hard，可选）
  - status: 状态（all/unsolved/solved，可选）
  - keyword: 搜索关键词（可选）
  - page: 页码（默认1）
  - per_page: 每页数量（默认20）

Response:
{
  "status": "success",
  "data": {
    "questions": [
      {
        "id": 1,
        "title": "两数之和",
        "subject": "算法",
        "difficulty": "easy",
        "acceptance_rate": 0.75,
        "total_submissions": 100,
        "is_favorite": false,
        "status": "unsolved"  // unsolved/solving/solved
      }
    ],
    "total": 50,
    "page": 1,
    "per_page": 20
  }
}
```

**获取题目详情**
```
GET /coding/api/questions/<question_id>

Response:
{
  "status": "success",
  "data": {
    "id": 1,
    "title": "两数之和",
    "description": "给定一个整数数组...",
    "examples": [
      {
        "input": "nums = [2,7,11,15], target = 9",
        "output": "[0,1]",
        "explanation": "因为 nums[0] + nums[1] == 9"
      }
    ],
    "constraints": ["2 <= nums.length <= 10^4"],
    "code_template": "def twoSum(nums, target):\n    pass",
    "programming_language": "python",
    "time_limit": 5,
    "memory_limit": 128,
    "difficulty": "easy",
    "hints": ["可以使用哈希表"]
  }
}
```

#### 5.1.2 代码执行API

**运行代码（不判题）**
```
POST /coding/api/execute
Request Body:
{
  "code": "print('Hello')",
  "language": "python",
  "input": "1\n2",  // 可选
  "time_limit": 5,  // 可选
  "memory_limit": 128  // 可选
}

Response:
{
  "status": "success",
  "data": {
    "output": "Hello\n",
    "error": null,
    "execution_time": 0.05,
    "status_code": "success"
  }
}
```

**提交代码（自动判题）**
```
POST /coding/api/submit
Request Body:
{
  "question_id": 1,
  "code": "def twoSum(nums, target):\n    ...",
  "language": "python"
}

Response:
{
  "status": "success",
  "data": {
    "submission_id": 123,
    "status": "accepted",  // accepted/wrong_answer/time_limit_exceeded/runtime_error
    "passed_cases": 5,
    "total_cases": 5,
    "execution_time": 0.12,
    "test_results": [
      {
        "case_id": 1,
        "status": "passed",
        "input": "1\n2",
        "expected_output": "3",
        "actual_output": "3",
        "execution_time": 0.01
      }
    ],
    "error_message": null
  }
}
```

#### 5.1.3 提交历史API

**获取提交历史**
```
GET /coding/api/submissions
Query Parameters:
  - question_id: 题目ID（可选）
  - status: 状态筛选（可选）
  - page: 页码（默认1）
  - per_page: 每页数量（默认20）

Response:
{
  "status": "success",
  "data": {
    "submissions": [
      {
        "id": 123,
        "question_id": 1,
        "question_title": "两数之和",
        "code": "def twoSum(nums, target):...",
        "language": "python",
        "status": "accepted",
        "passed_cases": 5,
        "total_cases": 5,
        "execution_time": 0.12,
        "submitted_at": "2025-01-29 10:30:00"
      }
    ],
    "total": 50,
    "page": 1,
    "per_page": 20
  }
}
```

**获取提交详情**
```
GET /coding/api/submissions/<submission_id>

Response:
{
  "status": "success",
  "data": {
    "id": 123,
    "question_id": 1,
    "question_title": "两数之和",
    "code": "def twoSum(nums, target):...",
    "language": "python",
    "status": "accepted",
    "passed_cases": 5,
    "total_cases": 5,
    "execution_time": 0.12,
    "test_results": [...],
    "error_message": null,
    "submitted_at": "2025-01-29 10:30:00"
  }
}
```

#### 5.1.4 统计API

**获取用户统计**
```
GET /coding/api/statistics

Response:
{
  "status": "success",
  "data": {
    "total_submissions": 150,
    "accepted_submissions": 120,
    "total_questions": 50,
    "solved_questions": 30,
    "acceptance_rate": 0.80,
    "difficulty_stats": {
      "easy": {"solved": 15, "total": 20},
      "medium": {"solved": 10, "total": 20},
      "hard": {"solved": 5, "total": 10}
    }
  }
}
```

### 5.2 管理端API

#### 5.2.1 题目管理API

**获取题目列表**
```
GET /admin/coding/api/questions
Query Parameters:
  - subject_id: 科目ID（可选）
  - difficulty: 难度（可选）
  - is_enabled: 是否启用（可选）
  - keyword: 搜索关键词（可选）
  - page: 页码
  - per_page: 每页数量

Response:
{
  "status": "success",
  "data": {
    "questions": [...],
    "total": 50,
    "page": 1,
    "per_page": 20
  }
}
```

**创建题目**
```
POST /admin/coding/api/questions
Request Body:
{
  "title": "两数之和",
  "subject_id": 1,
  "difficulty": "easy",
  "description": "给定一个整数数组...",
  "examples": [...],
  "constraints": [...],
  "code_template": "def twoSum(nums, target):\n    pass",
  "programming_language": "python",
  "time_limit": 5,
  "memory_limit": 128,
  "test_cases_json": {...},
  "hints": [...],
  "is_enabled": true
}

Response:
{
  "status": "success",
  "message": "题目创建成功",
  "data": {
    "id": 1,
    ...
  }
}
```

**更新题目**
```
PUT /admin/coding/api/questions/<question_id>
Request Body: (同创建题目)

Response:
{
  "status": "success",
  "message": "题目更新成功"
}
```

**删除题目**
```
DELETE /admin/coding/api/questions/<question_id>

Response:
{
  "status": "success",
  "message": "题目删除成功"
}
```

**批量删除**
```
POST /admin/coding/api/questions/batch_delete
Request Body:
{
  "ids": [1, 2, 3]
}

Response:
{
  "status": "success",
  "message": "成功删除 3 道题目"
}
```

---

## 6. 核心功能实现

### 6.1 代码执行服务

**位置**：`app/modules/coding/services/code_executor.py`

**功能**：
- 安全执行用户代码
- 时间限制控制
- 内存限制控制（生产环境）
- 输出截断（防止过长输出）

**实现要点**：
- 开发环境：使用 `subprocess` 执行
- 生产环境：使用 Docker 容器隔离执行
- 超时处理：使用 `subprocess.communicate(timeout=...)`
- 输出限制：限制输出长度（如10000字符）

### 6.2 判题服务

**位置**：`app/modules/coding/services/judge_service.py`

**功能**：
- 解析测试用例（JSON格式）
- 执行代码并验证输出
- 比较实际输出与期望输出
- 生成判题结果

**判题流程**：
1. 解析题目测试用例（公开测试用例 + 隐藏测试用例）
2. 对每个测试用例：
   - 执行代码（输入测试用例的input）
   - 获取实际输出
   - 与期望输出比较（去除首尾空白、换行符）
   - 记录结果
3. 统计通过用例数
4. 生成提交记录

**输出比较规则**：
- 去除首尾空白字符
- 去除末尾换行符
- 逐行比较（可选：严格模式）

### 6.3 题目服务

**位置**：`app/modules/coding/services/question_service.py`

**功能**：
- 题目CRUD操作
- 题目查询与筛选
- 题目统计信息计算
- 收藏/取消收藏

### 6.4 提交服务

**位置**：`app/modules/coding/services/submission_service.py`

**功能**：
- 提交记录CRUD
- 提交历史查询
- 提交统计计算
- 最佳提交记录查询

---

## 7. 前端实现

### 7.1 代码编辑器

**技术选型**：Monaco Editor（VS Code编辑器核心）

**功能**：
- 语法高亮
- 代码补全
- 代码格式化
- 多光标编辑
- 快捷键支持
- 主题切换（浅色/深色）

**集成方式**：
```html
<script src="https://cdn.jsdelivr.net/npm/monaco-editor@latest/min/vs/loader.js"></script>
<script>
  require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@latest/min/vs' } });
  require(['vs/editor/editor.main'], function () {
    const editor = monaco.editor.create(document.getElementById('editor'), {
      value: codeTemplate,
      language: 'python',
      theme: 'vs-dark',
      fontSize: 14,
      minimap: { enabled: false },
      scrollBeyondLastLine: false
    });
  });
</script>
```

### 7.2 UI组件

**遵循iOS 18风格**：
- 毛玻璃效果卡片
- 圆角按钮
- 柔和的阴影
- 流畅的动画过渡
- 响应式布局

**组件库**：
- 按钮组件（主要/次要/危险）
- 卡片组件
- 表格组件
- 模态框组件
- 下拉菜单组件

### 7.3 状态管理

**使用LocalStorage**：
- 保存代码草稿（按题目ID）
- 保存编辑器设置（主题、字体大小）
- 保存用户偏好

**使用SessionStorage**：
- 临时数据（如搜索结果）

---

## 8. 安全考虑

### 8.1 代码执行安全

**开发环境**：
- 使用 `subprocess` 执行，设置超时
- 限制执行时间（默认5秒）
- 限制输出长度

**生产环境**：
- 使用 Docker 容器隔离执行
- 限制容器资源（CPU、内存）
- 网络隔离（禁止网络访问）
- 文件系统只读（除临时目录）

### 8.2 输入验证

- 代码长度限制（如10000字符）
- 禁止危险函数（如 `eval`, `exec`, `__import__`）
- 禁止文件操作（如 `open`, `file`）
- 禁止系统调用（如 `os.system`, `subprocess`）

### 8.3 权限控制

- 题目查看：所有登录用户
- 代码提交：所有登录用户
- 题目管理：管理员/科目管理员
- 提交历史：仅查看自己的提交

---

## 9. 开发计划

### 9.1 第一阶段：基础功能（MVP）

**目标**：实现基本的编程题功能

**任务清单**：
1. ✅ 创建模块目录结构
2. ✅ 设计数据库表结构（复用现有表）
3. ⬜ 实现代码执行服务（迁移并优化）
4. ⬜ 实现判题服务
5. ⬜ 实现题目服务（CRUD）
6. ⬜ 实现提交服务
7. ⬜ 实现用户端API
8. ⬜ 实现用户端页面（列表页、详情页）
9. ⬜ 集成Monaco Editor
10. ⬜ 实现管理端API
11. ⬜ 实现管理端页面

### 9.2 第二阶段：功能增强

**目标**：完善功能，提升用户体验

**任务清单**：
1. ⬜ 实现提交历史页
2. ⬜ 实现统计页面
3. ⬜ 实现收藏功能
4. ⬜ 实现代码自动保存
5. ⬜ 优化判题性能
6. ⬜ 添加更多编程语言支持（Java、C++）

### 9.3 第三阶段：高级功能

**目标**：添加高级特性

**任务清单**：
1. ⬜ 实现代码对比功能（与历史提交对比）
2. ⬜ 实现讨论区（题目评论）
3. ⬜ 实现排行榜
4. ⬜ 实现题目推荐算法
5. ⬜ 实现Docker容器执行（生产环境）

---

## 10. 注意事项

### 10.1 模块独立性

- **不要**在quiz、exam、chat模块中引用编程题模块的代码
- **不要**在编程题模块中引用其他模块的代码（除公共工具类）
- **不要**在 `app/routes/coding.py` 中继续开发，应迁移到新模块

### 10.2 代码迁移

- 将 `app/services/code_executor.py` 迁移到 `app/modules/coding/services/`
- 将 `app/utils/code_validator.py` 迁移到 `app/modules/coding/utils/`
- 将 `app/templates/coding/index.html` 迁移到 `app/modules/coding/templates/coding/`
- 清理 `app/routes/coding.py`，仅保留模块注册代码

### 10.3 数据库兼容性

- 复用现有的 `questions` 表和 `code_submissions` 表
- 通过 `q_type='编程题'` 区分编程题
- 确保字段迁移逻辑在 `app/utils/database.py` 中正确执行

### 10.4 权限控制

- 使用 `@login_required` 装饰器保护用户端API
- 使用 `@admin_required` 或 `@subject_admin_required` 保护管理端API
- 在路由注册时添加权限检查

---

## 11. 参考资源

- Monaco Editor文档：https://microsoft.github.io/monaco-editor/
- Flask-RESTful文档：https://flask-restful.readthedocs.io/
- Pydantic文档：https://docs.pydantic.dev/
- iOS设计指南：https://developer.apple.com/design/human-interface-guidelines/

---

**文档版本**：v1.0  
**创建日期**：2025-01-29  
**最后更新**：2025-01-29  
**维护者**：开发团队

