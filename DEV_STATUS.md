# 开发状态记录

> 最后更新：2026-07-09
> 项目：商机智能跟踪与预警系统 (sjxt)

---

## 当前运行状态

| 服务 | 端口 | 状态 |
|------|------|------|
| 前端 (Nginx) | `:3000` | 运行中 |
| 后端 (FastAPI) | `:8080` | 运行中 |
| PostgreSQL | `:5433` | healthy |
| Redis | `:6380` | healthy |

---

## 已实现功能

### 认证
- [x] JWT 登录/登出
- [x] 路由守卫（未登录跳转 /login）
- [x] 密码 bcrypt 哈希存储

### 商机管理
- [x] 商机列表（分页、筛选：状态/优先级/支局/关键词）
- [x] 商机详情（基本信息、进度时间线、AI 分析面板、三角色信息）
- [x] 新建/编辑商机表单
- [x] 商机导入（Excel xlsx）
- [x] 商机导出（Excel xlsx）
- [x] 删除商机

### 进度协作
- [x] 填写进度更新
- [x] 进度时间线展示
- [x] 提交进度时自动触发 AI 分析

### AI 分析
- [x] 单条进度文本分析（DeepSeek API）
- [x] 全量商机分析（聚合所有进度）
- [x] 批量分析所有活跃商机
- [x] AI 推断商机状态（需求确认/方案设计/招标中/投标/商务谈判等）
- [x] AI 风险信号检测
- [x] AI 建议下一步行动
- [x] 分析历史记录查看

### 数据看板
- [x] 统计概览卡片（总商机数/待签约金额/关闭商机/未推进超期）
- [x] 优先级分布（饼图）
- [x] 商机状态分布（柱状图）
- [x] AI 风险等级分布（饼图）
- [x] 支局商机统计（柱状图）
- [x] 近期进度更新列表
- [x] 需关注商机概览（未推进/招标临近/竞争对手）

### 优先级引擎
- [x] 多维加权评分（大单规模/招标临近/未推进时长/AI风险/竞争对手/客户类型）
- [x] 自动/手动调整优先级
- [x] 优先级变更历史

### 定时任务 (APScheduler)
- [x] 每周提醒邮件
- [x] 招标临近检查（每天 08:00）
- [x] 超期未推进预警（每天 09:00）
- [x] 优先级自动升级（每天 02:00）
- [x] 清理过期日志（每周日 03:00）

### 系统设置
- [x] 用户管理（CRUD，三角色 + 管理员）
- [x] AI 配置（DeepSeek API Key/地址/模型）
- [x] 邮件配置（SMTP 服务器/端口/发件人）
- [x] 邮件模板自定义（6 种模板，Jinja2 语法）
- [x] 预警规则配置
- [x] Scheduler 状态查看

### 操作日志
- [x] 操作日志记录（导入/导出/创建/编辑/删除/AI分析/登录）
- [x] 日志查看与筛选

### 邮件服务
- [x] 异步 SMTP 发送
- [x] 6 种 HTML 邮件模板（周度提醒/AI预警/优先级变更/招标提醒/超期预警/进度通知）
- [x] 模板可自定义（数据库存储）

---

## 近期视觉优化（Plane 灵感）

- [x] CSS 动画系统：fadeInUp / scaleIn / slideInRight / shimmer 骨架屏
- [x] 卡片悬浮上移 + 阴影加深效果
- [x] 按钮 hover 上移 + 阴影
- [x] 统计卡片交错入场动画
- [x] 登录页点阵背景 + 卡片入场动画
- [x] 侧栏菜单活动指示条 + 渐变背景
- [x] 看板卡片顶部分色条

---

## 已知问题 / 待办

### 技术债
- [ ] **无 JWT 认证中间件** — 部分 API 路由未校验 token（progress.py 中 `current_user_id` 硬编码为 1）
- [ ] **两个 AI 服务重叠** — `ai_engine.py` 和 `ai_service.py` 功能重复，应合并
- [ ] **无单元/集成测试**
- [ ] **无前端打包优化** — 无代码分割/懒加载，JS 单体 2.3MB
- [ ] **CORS 配置** — 当前 `allow_origins=["*"]`，生产环境应限制

### 已知 Bug
- [ ] `passlib` + `bcrypt 5.x` 不兼容，需锁定 `bcrypt==4.1.3`（已处理）
- [ ] `system_link` 在邮件模板中为空字符串，需配置实际系统链接
- [ ] 看板"待签约金额"之前硬编码 `—`（已修复，接入 AI 数据）

---

## 部署方式

### Docker Compose（当前使用）
```bash
docker compose up -d
docker compose exec backend alembic upgrade head
docker compose exec backend python3 app/seed.py
```

### 构建命令
```bash
# 后端
docker compose build --no-cache backend

# 前端
cd frontend && rm -rf dist && npm run build
docker build --no-cache -t sjxt-frontend:latest frontend/
```

### 访问地址
- 前端：http://localhost:3000
- API 文档：http://localhost:8080/docs
- 默认账号：admin / admin123

---

## 关键文件索引

| 文件 | 说明 |
|------|------|
| `backend/app/api/` | 所有 API 路由 |
| `backend/app/services/ai_engine.py` | AI 分析引擎（DeepSeek） |
| `backend/app/services/email_service.py` | 邮件发送 + 模板 |
| `backend/app/services/priority_engine.py` | 优先级评分引擎 |
| `backend/app/services/scheduler_service.py` | 定时任务管理 |
| `frontend/src/views/` | 所有页面组件 |
| `frontend/src/styles/jira-theme.css` | 全局样式 + 动画 |
| `frontend/src/api/` | API 请求封装 |
