# AGENTS.md — 商机智能跟踪与预警系统

> 本文档供 AI Coding Agent 阅读，旨在帮助快速理解项目架构、约定和开发流程。

---

## 1. 项目概述

**商机智能跟踪与预警系统** 是一个面向 ICT/运营商行业的管理后台，用于取代人工 Excel 追踪商机。系统围绕"三角色"（项目经理、客户经理、责任支局长）协作展开，提供商机管理、进度协作、AI 风险分析、邮件预警和数据看板等功能。

核心业务指标：漏单率、平均转化周期、未推进超期率、AI 预警命中率。

---

## 2. 技术栈

| 层级 | 选型 | 说明 |
|------|------|------|
| 后端框架 | Python FastAPI 0.111 | 异步 RESTful API |
| ORM | SQLAlchemy 2.0 (async) | 异步引擎 + async_sessionmaker |
| 数据库迁移 | Alembic 1.13 | 异步迁移配置 |
| 数据库 | PostgreSQL 14 | 主数据库，使用 asyncpg 驱动 |
| 缓存/消息 | Redis 7 | 缓存、消息队列（预留） |
| 前端框架 | Vue 3 (Composition API) + Vite 8 | SPA |
| UI 组件库 | Element Plus 2.14 | Jira 风格主题覆盖 |
| 可视化 | ECharts 6 | 看板图表 |
| HTTP 客户端 | Axios | 前端请求封装 |
| AI 服务 | DeepSeek API (OpenAI 兼容) | 进度文本语义分析、风险识别 |
| 任务调度 | APScheduler 3.10 (AsyncIOScheduler) | 定时邮件提醒、AI 定时扫描 |
| 邮件发送 | aiosmtplib + Jinja2 | 异步 SMTP + HTML 模板渲染 |
| 密码/认证 | passlib(bcrypt) + python-jose(JWT) | 密码哈希 + HS256 JWT |
| Excel 处理 | openpyxl | 商机数据导入导出 |
| 容器化 | Docker + Docker Compose | 生产部署 |

依赖管理：
- **后端**: `backend/requirements.txt`（无 pyproject.toml，纯 pip）
- **前端**: `frontend/package.json`（npm）

---

## 3. 项目结构

```
sjxt/
├── backend/                          # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py                   # FastAPI 应用入口，注册路由和 CORS
│   │   ├── seed.py                   # 种子数据脚本（管理员 + 系统配置）
│   │   ├── api/                      # 路由层（APIRouter）
│   │   │   ├── __init__.py           # 空
│   │   │   ├── auth.py               # POST /api/auth/login
│   │   │   ├── users.py              # CRUD /api/users
│   │   │   ├── opportunities.py      # CRUD + 导入导出 /api/opportunities
│   │   │   ├── progress.py           # 进度协作 /api/opportunities/{id}/progress
│   │   │   ├── ai.py                 # AI 引擎路由（分析/文本分析/历史）
│   │   │   ├── ai_analysis.py        # AI 分析路由（独立 prefix）
│   │   │   ├── dashboard.py          # 数据看板 /api/dashboard/*
│   │   │   ├── email_logs.py         # 邮件日志 /api/email-logs
│   │   │   ├── priority_engine.py    # 优先级引擎 /api/priority/*
│   │   │   ├── scheduler.py          # 调度管理 /api/scheduler/*
│   │   │   ├── configs.py            # 系统配置 /api/configs
│   │   │   └── operation_logs.py     # 操作日志 /api/logs
│   │   ├── core/                     # 核心基础设施
│   │   │   ├── __init__.py           # 导出 settings, Base, engine, get_db, security utils
│   │   │   ├── config.py             # Pydantic Settings（环境变量）
│   │   │   ├── database.py           # 异步引擎 + SessionLocal + get_db 依赖
│   │   │   └── security.py           # bcrypt 密码 + JWT token
│   │   ├── models/                   # SQLAlchemy ORM 模型
│   │   │   ├── __init__.py           # 统一导出所有模型供 Alembic 使用
│   │   │   ├── user.py               # User
│   │   │   ├── opportunity.py        # Opportunity（商机主表）
│   │   │   ├── opportunity_progress.py  # 进度更新历史
│   │   │   ├── ai_analysis_result.py    # AI 分析结果
│   │   │   ├── email_log.py          # 邮件发送日志
│   │   │   ├── priority_change_log.py   # 优先级变更历史
│   │   │   ├── operation_log.py      # 操作日志
│   │   │   └── system_config.py      # 系统配置键值对
│   │   ├── schemas/                  # Pydantic 请求/响应模型
│   │   │   ├── __init__.py           # 空
│   │   │   ├── user.py, opportunity.py, progress.py, ai.py, ai_analysis.py,
│   │   │   │   email.py, dashboard.py, priority_engine.py
│   │   ├── services/                 # 业务逻辑层
│   │   │   ├── __init__.py           # 空
│   │   │   ├── ai_engine.py          # 核心 AI 引擎：DeepSeek 调用 + 进度/全面分析
│   │   │   ├── ai_service.py         # 另一套 AI 分析服务（与 ai_engine 重叠，待统一）
│   │   │   ├── email_service.py      # SMTP 发送 + Jinja2 模板渲染
│   │   │   ├── priority_engine.py    # 多维度优先级评分 + 自动/手动调整
│   │   │   ├── scheduler_service.py  # APScheduler 定时任务管理
│   │   │   └── log_service.py        # 操作日志记录与查询
│   │   └── utils/
│   │       └── excel.py              # Excel 导入导出（openpyxl + 用户匹配）
│   ├── alembic/                      # 数据库迁移
│   │   ├── env.py                    # 异步 Alembic 配置
│   │   ├── script.py.mako            # 迁移模板
│   │   └── versions/                 # 迁移版本文件
│   ├── alembic.ini                   # Alembic 配置
│   ├── Dockerfile                    # Python 3.11-slim + uvicorn
│   └── requirements.txt              # Python 依赖
├── frontend/                         # Vue 3 前端
│   ├── src/
│   │   ├── main.js                   # Vue 应用入口（注册 Element Plus / ECharts / Router）
│   │   ├── App.vue                   # 根组件（仅 <router-view />）
│   │   ├── router/index.js           # Vue Router 配置 + 登录守卫
│   │   ├── api/
│   │   │   ├── http.js               # Axios 实例（拦截器 + JWT 注入）
│   │   │   └── index.js              # 各 API 方法封装（authApi, userApi, opportunityApi）
│   │   ├── layouts/
│   │   │   └── MainLayout.vue        # Jira 风格主布局（侧边栏 + 顶栏 + 内容区）
│   │   ├── views/
│   │   │   ├── Login.vue             # 登录页
│   │   │   ├── OpportunityList.vue   # 商机列表（筛选 + 表格 + 导入/导出）
│   │   │   ├── OpportunityDetail.vue # 商机详情（基本信息 + 进度时间线 + AI 分析 + 三角色）
│   │   │   ├── OpportunityForm.vue   # 新建/编辑商机表单
│   │   │   ├── Dashboard.vue         # 数据看板（ECharts 图表 + 紧急概览）
│   │   │   ├── Settings.vue          # 系统设置（用户管理 + 系统配置 + Scheduler 状态）
│   │   │   └── OperationLogs.vue     # 操作日志查看
│   │   └── styles/
│   │       └── jira-theme.css        # Jira Design System CSS 变量覆盖
│   ├── index.html
│   ├── vite.config.js                # Vite 配置（dev proxy /api → localhost:8080）
│   ├── nginx.conf                    # Nginx 生产配置（reverse proxy /api → backend:8000）
│   └── Dockerfile                    # Multi-stage: node:20-alpine build + nginx:alpine
├── docker-compose.yml                # postgres + redis + backend + frontend
├── .env.example                      # 环境变量模板
├── .dockerignore
└── README.md
```

---

## 4. 数据模型

所有 ORM 模型定义在 `backend/app/models/`，继承自 `app.core.database.Base`。共 8 张表：

| 表名 | 模型类 | 说明 |
|------|--------|------|
| `users` | User | 用户（三角色 + 管理员），含 hashed_password |
| `opportunities` | Opportunity | 商机主表，含 AI 扩展字段和关联外键 |
| `opportunity_progress` | OpportunityProgress | 进度更新历史，每次填写一条记录 |
| `ai_analysis_results` | AiAnalysisResult | AI 分析结果，JSONB 存储风险信号 |
| `email_logs` | EmailLog | 邮件发送日志 |
| `priority_change_logs` | PriorityChangeLog | 优先级变更历史 |
| `operation_logs` | OperationLog | 用户操作审计日志 |
| `system_configs` | SystemConfig | 键值对系统配置 |

详细字段定义见 `sjxt.md` 设计文档第 2 节。

---

## 5. 核心架构设计

### 5.1 API 路由

所有路由集中在 `app/api/`，使用 FastAPI `APIRouter`，在 `main.py` 中统一 `include_router`。所有 API 以 `/api/` 为前缀。当前**未实现全局 JWT 中间件**——路由级别的认证/鉴权尚未完成，需注意。

### 5.2 数据库访问模式

```python
# 依赖注入方式（推荐，带自动 commit/rollback）
async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

`get_db` 作为 FastAPI `Depends` 使用，自动管理事务。对于后台任务（如 scheduler），直接使用 `async_session()` 上下文管理器。

### 5.3 AI 分析引擎

两套服务并存（**注意这个技术债**）：
- **`ai_engine.py`** — 被 `progress.py` 和 `ai.py` 路由调用，功能较完整（`analyze_progress_text` / `analyze_opportunity_full` / `get_analysis_history`）
- **`ai_service.py`** — 被 `ai_analysis.py` 路由调用（`analyze_progress`），功能与前者重叠

两者都调用 DeepSeek API（OpenAI 兼容格式），通过 `httpx.AsyncClient`。API key 优先从环境变量读取，其次从 `system_configs` 表读取。

### 5.4 邮件服务

- 使用 `aiosmtplib` 异步发送
- HTML 模板使用 Jinja2 内部字符串模板（定义在 `email_service.py` 的 `EMAIL_TEMPLATES` 字典中）
- 支持 6 种邮件类型：`weekly_remind`, `ai_alert`, `priority_change`, `bid_approach`, `no_push_warn`, `progress_update`

### 5.5 优先级引擎

多维加权评分系统（满分 100）：
- 大单规模（30 分）
- 招标临近（25 分）
- 未推进时长（20 分）
- AI 风险等级（15 分）
- 竞争对手检测（10 分）
- 客户类型（5 分）

映射：≥80→紧急(1), ≥55→高(2), ≥30→中(3), 其他→低(4)。

### 5.6 定时任务

由 `SchedulerService`（APScheduler `AsyncIOScheduler` 单例）管理，在 FastAPI lifespan 中启停。

| 任务 ID | 调度 | 说明 |
|---------|------|------|
| `weekly_remind` | 每周一可配置时间 | 未推进商机提醒邮件 |
| `bid_approach_check` | 每天 08:00 | 招标临近检查 |
| `no_push_warn` | 每天 09:00 | 超期未推进预警 |
| `auto_priority_upgrade` | 每天 02:00 | 按未推进天数自动升级优先级 |
| `cleanup_expired` | 周日 03:00 | 清理 30 天前邮件日志 |

### 5.7 认证

- JWT 认证（HS256），24 小时过期
- 密码使用 bcrypt 哈希
- 前端在 `localStorage` 中存储 `token` 和 `real_name`
- Axios 拦截器自动注入 `Authorization: Bearer <token>`
- 401 响应自动跳转到 `/login`

---

## 6. 构建和运行命令

### 6.1 Docker Compose 生产模式

```bash
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY 和 SMTP 配置
docker compose up -d
docker compose exec backend alembic upgrade head
docker compose exec backend python3 app/seed.py
# 访问 http://localhost:3000  默认账号 admin / admin123
```

### 6.2 开发模式

```bash
# 启动依赖服务
docker compose up -d postgres redis

# 后端（backend/ 目录下）
cd backend
source venv/bin/activate  # 或自行创建虚拟环境
pip install -r requirements.txt
export DATABASE_URL=postgresql+asyncpg://sjxt:sjxt@localhost:5433/opportunity_db
export DEBUG=true
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8080

# 前端（frontend/ 目录下）
cd frontend
npm install
npm run dev   # Vite dev server on :5173, proxy /api → :8080
```

### 6.3 数据库迁移

```bash
# 创建迁移
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

### 6.4 测试

项目当前**不包含任何测试文件**。如需添加测试，建议结构：
- 后端: `backend/tests/`，使用 `pytest` + `httpx.AsyncClient` + 测试数据库
- 前端: `frontend/src/__tests__/`，使用 Vitest

---

## 7. 代码约定和开发规范

### 7.1 命名约定

- **Python**: `snake_case`（函数、变量、文件名），`PascalCase`（类、模型）
- **JavaScript/Vue**: `camelCase`（变量、函数），`PascalCase`（组件名）
- **API 路由**: 小写复数，`/api/resource/{id}/sub-resource`
- **数据库表**: `snake_case` 复数

### 7.2 后端分层

```
API (router) → Service (业务逻辑) → Model (ORM)
               ↓
            Schemas (Pydantic 数据校验)
```

- API 层只做参数校验 + 调用 service + 返回响应
- Service 层包含核心业务逻辑，可复用
- Model 层只定义 ORM 映射
- Schemas 层定义输入输出数据结构

### 7.3 数据库操作

- 所有写操作需 `await db.flush()` + `await db.refresh(obj)` 获取生成的 ID
- 查询使用 `selectinload` 加载关联关系（避免 N+1）
- `get_db` 依赖自动 commit/rollback，但后台任务需手动管理

### 7.4 错误处理

- API 层使用 `HTTPException` 返回标准错误
- Service 层抛出 `ValueError` / `RuntimeError`，由 API 层捕获转换
- 操作日志通过 `log_service.log_operation()` 记录

### 7.5 前端约定

- 使用 Vue 3 Composition API（`<script setup>`）
- API 请求通过 `src/api/http.js`（Axios 实例）或 `src/api/index.js` 封装的函数
- 样式优先使用 `jira-theme.css` 中的 CSS 变量（`--ds-*`）
- 组件作用域样式使用 `<style scoped>`
- 路由在 `src/router/index.js` 中集中定义

---

## 8. 构建注意事项

### 8.1 Dockerfile

- **后端**: `python:3.11-slim` 基础镜像，安装 `gcc` + `libpq-dev` 以编译 psycopg2 和 bcrypt
- **前端**: Multi-stage 构建，`node:20-alpine` 编译 → `nginx:alpine` 运行

### 8.2 环境变量

核心变量（详见 `.env.example`）：
- `DATABASE_URL` — PostgreSQL 连接串（asyncpg 格式）
- `REDIS_URL` — Redis 连接串
- `JWT_SECRET` — JWT 签名密钥（生产务必修改）
- `DEEPSEEK_API_KEY` — DeepSeek API 密钥
- `SMTP_*` — 邮件服务器配置
- `DEBUG` — 是否启用 SQLAlchemy echo 日志

### 8.3 Nginx 配置

生产环境下前端 Nginx 反代 `/api/` 到 `backend:8000`，单页面应用通过 `try_files` 处理前端路由。

---

## 9. 安全考虑

- **JWT Secret** 生产环境务必修改，不应使用默认值
- 密码使用 bcrypt 哈希存储
- 当前**未实现** JWT 依赖注入中间件——API 路由未校验 token 有效性（`progress.py` 中 `current_user_id` 硬编码为 1 的 TODO）
- CORS 当前配置为允许所有来源（`allow_origins=["*"]`），生产环境应限制
- `system_configs` 表中存储 DeepSeek API key 和 SMTP 密码，需注意泄露风险
- `.env` 文件已在 `.dockerignore` 中排除，不会进入 Docker 镜像
- 前端 token 存储在 `localStorage`，存在 XSS 风险

---

## 10. 已知技术债

1. **两个 AI 服务重叠** — `ai_engine.py` 和 `ai_service.py` 功能高度重复，应合并
2. **无 JWT 认证中间件** — 所有 API 路由目前无实际认证保护
3. **无单元/集成测试** — 项目缺少任何测试
4. **无类型严格检查** — Python 代码未配置 mypy/Pyright
5. **`progress.py` 中硬编码 `current_user_id=1`** — 待改为从 JWT 中提取
6. **`system_link` 在邮件模板中为空字符串** — 待配置实际系统访问链接
7. **前端 Dashboard 中 "待签约金额"等数值显示为硬编码 `—`** — 待接入实际数据
8. **无前端打包优化** — 无代码分割/懒加载配置
