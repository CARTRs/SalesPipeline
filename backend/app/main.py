from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import auth, users, opportunities, progress, email_logs, operation_logs, priority_engine, ai, ai_analysis, dashboard, scheduler, configs
from app.services.scheduler_service import scheduler_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：初始化调度器
    await scheduler_service.start()
    yield
    # 停止时：优雅关闭调度器
    await scheduler_service.stop()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(opportunities.router)
app.include_router(progress.router)
app.include_router(email_logs.router)
app.include_router(operation_logs.router)
app.include_router(priority_engine.router)
app.include_router(ai.router)
app.include_router(ai_analysis.router)
app.include_router(dashboard.router)
app.include_router(scheduler.router)
app.include_router(configs.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
