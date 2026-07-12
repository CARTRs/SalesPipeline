# 商机智能跟踪与预警系统

## 快速启动（Docker Compose）

```bash
# 1. 复制环境变量
cp .env.example .env
# 编辑 .env 填入 DeepSeek API Key 和 SMTP 配置

# 2. 启动所有服务
docker compose up -d

# 3. 运行数据库迁移
docker compose exec backend alembic upgrade head

# 4. 初始化默认数据
docker compose exec backend python3 -c "
import asyncio
from sqlalchemy import select
from app.core.database import async_session
from app.core.security import get_password_hash
from app.models.user import User
async def seed():
    async with async_session() as s:
        r = await s.execute(select(User).where(User.username == 'admin'))
        if not r.scalar_one_or_none():
            s.add(User(username='admin', real_name='系统管理员', email='admin@company.com', role='管理员', hashed_password=get_password_hash('admin123'), is_active=True))
            await s.commit()
            print('管理员创建成功: admin / admin123')
asyncio.run(seed())
"

# 5. 访问系统
# 前端：http://localhost:3000
# 后端API：http://localhost:8080/api/health
# 默认账号：admin / admin123
```

## 开发模式

```bash
# 启动数据库
docker compose up -d postgres redis

# 后端（在 backend/ 目录）
source venv/bin/activate
export DATABASE_URL=postgresql+asyncpg://sjxt:sjxt@localhost:5433/opportunity_db
uvicorn app.main:app --reload --port 8080

# 前端（在 frontend/ 目录）
npm run dev
```

## 技术栈

| 层级 | 选型 |
|------|------|
| 后端 | Python FastAPI + SQLAlchemy 2.0 (async) |
| 前端 | Vue 3 + Element Plus (Jira 风格主题) |
| 数据库 | PostgreSQL 14 |
| 缓存 | Redis 7 |
| AI | DeepSeek API (OpenAI 兼容) |
| 任务调度 | APScheduler |
| 部署 | Docker Compose |
