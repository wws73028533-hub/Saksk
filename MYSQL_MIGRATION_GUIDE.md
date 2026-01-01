# SQLite 到 MySQL 迁移指南

本指南详细说明如何将系统从 SQLite 数据库迁移到 MySQL 数据库。

## 目录

1. [准备工作](#准备工作)
2. [安装 MySQL 和驱动](#安装-mysql-和驱动)
3. [配置修改](#配置修改)
4. [代码修改](#代码修改)
5. [SQL 语法转换](#sql-语法转换)
6. [数据迁移](#数据迁移)
7. [测试验证](#测试验证)
8. [常见问题](#常见问题)

---

## 准备工作

### 1. 备份现有 SQLite 数据库

在迁移之前，**务必备份**当前的 SQLite 数据库：

```bash
# Windows
copy instance\submissions.db instance\submissions.db.backup

# Linux/Mac
cp instance/submissions.db instance/submissions.db.backup
```

### 2. 检查系统要求

- Python 3.8+
- MySQL 5.7+ 或 MySQL 8.0+（推荐 8.0+）
- 足够的磁盘空间用于数据迁移

---

## 安装 MySQL 和驱动

### 1. 安装 MySQL 服务器

#### Windows
1. 下载 MySQL Installer：https://dev.mysql.com/downloads/installer/
2. 运行安装程序，选择 "MySQL Server"
3. 设置 root 密码（请妥善保存）
4. 完成安装后，启动 MySQL 服务

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install mysql-server
sudo mysql_secure_installation
```

#### Linux (CentOS/RHEL)
```bash
sudo yum install mysql-server
sudo systemctl start mysqld
sudo mysql_secure_installation
```

#### macOS
```bash
brew install mysql
brew services start mysql
mysql_secure_installation
```

### 2. 创建数据库和用户

登录 MySQL：

```bash
mysql -u root -p
```

执行以下 SQL：

```sql
-- 创建数据库（使用 utf8mb4 字符集支持 emoji 和特殊字符）
CREATE DATABASE saksk_ti CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建专用用户（推荐，不要直接使用 root）
CREATE USER 'saksk_user'@'localhost' IDENTIFIED BY 'your_strong_password_here';

-- 授予权限
GRANT ALL PRIVILEGES ON saksk_ti.* TO 'saksk_user'@'localhost';

-- 刷新权限
FLUSH PRIVILEGES;

-- 验证用户权限
SHOW GRANTS FOR 'saksk_user'@'localhost';
```

### 3. 安装 Python MySQL 驱动

推荐使用 `PyMySQL`（纯 Python 实现，易于安装）：

```bash
pip install PyMySQL
```

或者使用 `mysqlclient`（性能更好，但需要编译）：

```bash
# Windows（需要 Visual C++ 编译器）
pip install mysqlclient

# Linux（需要先安装开发库）
sudo apt-get install python3-dev default-libmysqlclient-dev build-essential
pip install mysqlclient

# macOS
brew install mysql-client
pip install mysqlclient
```

---

## 配置修改

### 1. 更新 requirements.txt

在 `requirements.txt` 中添加 MySQL 驱动：

```
# ============================================================================
# MySQL 数据库驱动
# ============================================================================
PyMySQL==1.1.0  # 推荐：纯 Python 实现，易于安装
# 或使用 mysqlclient==2.2.0  # 性能更好，但需要编译
```

### 2. 修改配置文件 (app/core/config.py)

在 `Config` 类中添加 MySQL 配置：

```python
# 数据库配置
DB_TYPE = os.environ.get('DB_TYPE', 'sqlite')  # 'sqlite' 或 'mysql'

if DB_TYPE == 'mysql':
    # MySQL 配置
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'saksk_user')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'saksk_ti')
    MYSQL_CHARSET = os.environ.get('MYSQL_CHARSET', 'utf8mb4')
else:
    # SQLite 配置（保留兼容性）
    DATABASE_PATH = os.path.join(BASE_DIR, 'instance', 'submissions.db')
```

### 3. 创建环境变量文件 (.env)

在项目根目录创建 `.env` 文件：

```env
# 数据库类型：sqlite 或 mysql
DB_TYPE=mysql

# MySQL 配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=saksk_user
MYSQL_PASSWORD=your_strong_password_here
MYSQL_DATABASE=saksk_ti
MYSQL_CHARSET=utf8mb4

# 其他配置...
SECRET_KEY=your_secret_key_here
```

**重要：** 将 `.env` 添加到 `.gitignore` 中，不要提交密码到版本控制！

---

## 代码修改

### 1. 修改数据库工具 (app/core/utils/database.py)

主要修改点：

1. **替换 sqlite3 导入**
2. **修改 get_db() 函数** - 根据配置选择数据库类型
3. **修改 SQL 语法** - 转换为 MySQL 兼容语法
4. **移除 PRAGMA 语句** - MySQL 不需要
5. **修改数据类型** - INTEGER → INT, TEXT → VARCHAR/TEXT, AUTOINCREMENT → AUTO_INCREMENT

### 2. 修改 __init__.py 中的 PRAGMA 语句

在 `app/__init__.py` 中，移除或替换 SQLite 特定的 `PRAGMA table_info` 查询。

---

## SQL 语法转换

### 主要差异对比

| SQLite | MySQL | 说明 |
|--------|-------|------|
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `INT PRIMARY KEY AUTO_INCREMENT` | 自增主键 |
| `TEXT` | `VARCHAR(255)` 或 `TEXT` | 文本类型 |
| `DATETIME DEFAULT CURRENT_TIMESTAMP` | `DATETIME DEFAULT CURRENT_TIMESTAMP` | 时间戳（MySQL 5.6.5+） |
| `INTEGER DEFAULT 0` | `INT DEFAULT 0` 或 `TINYINT(1) DEFAULT 0` | 布尔值（MySQL 使用 TINYINT(1)） |
| `PRAGMA table_info(table)` | `DESCRIBE table` 或 `SHOW COLUMNS FROM table` | 查看表结构 |
| `sqlite_master` | `information_schema.TABLES` | 系统表 |
| `CREATE INDEX IF NOT EXISTS` | `CREATE INDEX IF NOT EXISTS` (MySQL 8.0+) | 索引创建 |
| `UNIQUE INDEX ... WHERE` | `CREATE UNIQUE INDEX ...` (不支持 WHERE) | 条件唯一索引 |

### 数据类型映射建议

| SQLite | MySQL | 说明 |
|--------|-------|------|
| `INTEGER` | `INT` 或 `INTEGER` | 整数 |
| `TEXT` | `VARCHAR(255)` (短文本) 或 `TEXT` (长文本) | 文本 |
| `REAL` | `DOUBLE` 或 `DECIMAL` | 浮点数 |
| `BLOB` | `BLOB` 或 `LONGBLOB` | 二进制数据 |
| `DATETIME` | `DATETIME` 或 `TIMESTAMP` | 日期时间 |

---

## 数据迁移

### 方法 1：使用 SQL 导出/导入（推荐用于小型数据库）

#### 步骤 1：导出 SQLite 数据

使用 Python 脚本导出数据：

```python
# scripts/export_sqlite.py
import sqlite3
import json
from datetime import datetime

def export_data(db_path, output_file):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    tables = []
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    
    for table_name in cursor.fetchall():
        table_name = table_name[0]
        if table_name == 'sqlite_sequence':
            continue
        
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        tables.append({
            'name': table_name,
            'data': [dict(row) for row in rows]
        })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(tables, f, ensure_ascii=False, indent=2, default=str)
    
    conn.close()
    print(f"数据已导出到 {output_file}")

if __name__ == '__main__':
    export_data('instance/submissions.db', 'instance/data_export.json')
```

#### 步骤 2：导入到 MySQL

```python
# scripts/import_mysql.py
import json
import pymysql
from app.core.config import Config

def import_data(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        tables = json.load(f)
    
    # 连接 MySQL（先确保表已创建）
    conn = pymysql.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE,
        charset=Config.MYSQL_CHARSET
    )
    
    cursor = conn.cursor()
    
    for table_info in tables:
        table_name = table_info['name']
        data = table_info['data']
        
        if not data:
            continue
        
        # 获取列名
        columns = list(data[0].keys())
        placeholders = ', '.join(['%s'] * len(columns))
        columns_str = ', '.join([f"`{col}`" for col in columns])
        
        sql = f"INSERT INTO `{table_name}` ({columns_str}) VALUES ({placeholders})"
        
        for row in data:
            values = [row.get(col) for col in columns]
            try:
                cursor.execute(sql, values)
            except Exception as e:
                print(f"插入 {table_name} 数据时出错: {e}")
                print(f"SQL: {sql}")
                print(f"Values: {values}")
        
        conn.commit()
        print(f"已导入 {len(data)} 条记录到 {table_name}")
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    import_data('instance/data_export.json')
```

### 方法 2：使用专业工具（推荐用于大型数据库）

#### 使用 DBeaver 或 MySQL Workbench

1. **DBeaver（免费，跨平台）**
   - 下载：https://dbeaver.io/
   - 连接到 SQLite 数据库
   - 导出数据为 SQL 脚本
   - 连接到 MySQL 数据库
   - 执行 SQL 脚本

2. **MySQL Workbench（官方工具）**
   - 下载：https://dev.mysql.com/downloads/workbench/
   - 使用 "Database Migration Wizard"

---

## 测试验证

### 1. 功能测试清单

- [ ] 用户登录/注册
- [ ] 题目浏览和搜索
- [ ] 答题功能
- [ ] 收藏和错题本
- [ ] 考试功能
- [ ] 编程题提交
- [ ] 聊天功能
- [ ] 通知功能
- [ ] 管理员功能

### 2. 性能测试

```bash
# 测试数据库连接
python -c "from app import create_app; app = create_app(); from app.core.utils.database import get_db; db = get_db(); print('连接成功')"

# 测试查询性能
python scripts/test_mysql_performance.py
```

### 3. 数据完整性检查

```sql
-- 在 MySQL 中检查数据
USE saksk_ti;

-- 检查表数量
SELECT COUNT(*) as table_count FROM information_schema.tables 
WHERE table_schema = 'saksk_ti';

-- 检查各表记录数
SELECT 
    table_name,
    table_rows
FROM information_schema.tables
WHERE table_schema = 'saksk_ti'
ORDER BY table_rows DESC;

-- 检查外键约束
SELECT 
    TABLE_NAME,
    CONSTRAINT_NAME,
    REFERENCED_TABLE_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'saksk_ti'
AND REFERENCED_TABLE_NAME IS NOT NULL;
```

---

## 常见问题

### 1. 字符编码问题

**问题：** 中文显示乱码

**解决：**
- 确保数据库字符集为 `utf8mb4`
- 确保连接字符集为 `utf8mb4`
- 确保表和列的字符集为 `utf8mb4`

```sql
-- 检查数据库字符集
SHOW CREATE DATABASE saksk_ti;

-- 修改表字符集
ALTER TABLE users CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 时间戳问题

**问题：** `CURRENT_TIMESTAMP` 默认值不工作

**解决：** MySQL 5.6.5 之前版本需要显式指定 `ON UPDATE CURRENT_TIMESTAMP`：

```sql
created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
```

### 3. 布尔值问题

**问题：** SQLite 使用 `INTEGER`，MySQL 使用 `TINYINT(1)`

**解决：** 在代码中统一处理，MySQL 中 `TINYINT(1)` 的 0/1 与 Python 的 True/False 会自动转换。

### 4. 外键约束问题

**问题：** 外键约束不生效

**解决：** 确保使用 InnoDB 引擎（MySQL 5.5+ 默认），并启用外键检查：

```sql
SET FOREIGN_KEY_CHECKS = 1;
```

### 5. 连接池问题

**问题：** 连接数过多

**解决：** 使用连接池（如 SQLAlchemy），或配置 MySQL 连接池参数。

### 6. 性能问题

**优化建议：**
- 添加适当的索引
- 使用 `EXPLAIN` 分析慢查询
- 配置 MySQL 缓冲池大小
- 定期优化表：`OPTIMIZE TABLE table_name`

---

## 回滚方案

如果迁移后出现问题，可以快速回滚到 SQLite：

1. **修改 .env 文件：**
   ```env
   DB_TYPE=sqlite
   ```

2. **恢复备份的数据库文件：**
   ```bash
   copy instance\submissions.db.backup instance\submissions.db
   ```

3. **重启应用**

---

## 生产环境部署建议

1. **使用连接池：** 推荐使用 SQLAlchemy 或 PyMySQL 的连接池
2. **启用 SSL：** 生产环境建议启用 MySQL SSL 连接
3. **定期备份：** 配置 MySQL 自动备份
4. **监控：** 使用 MySQL Enterprise Monitor 或开源工具如 Prometheus + mysqld_exporter
5. **主从复制：** 大型应用考虑配置 MySQL 主从复制

---

## 下一步

完成迁移后，建议：

1. 更新部署文档
2. 更新开发环境配置说明
3. 设置数据库备份策略
4. 配置数据库监控
5. 性能优化和索引调优

---

## 支持

如遇到问题，请检查：
- MySQL 错误日志：`/var/log/mysql/error.log` (Linux) 或 MySQL 安装目录下的日志
- 应用日志：`logs/app.log`
- MySQL 状态：`SHOW STATUS;`

