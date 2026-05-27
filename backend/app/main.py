"""
内网运维集成工具平台 — FastAPI 主入口
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库"""
    create_db_and_tables()
    yield


app = FastAPI(
    title="内网运维集成工具平台",
    description="资产台账 + Nmap 内网扫描 + Iperf3 网络性能测试 + 在线终端 + 网络拓扑",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS — 内网环境，允许局域网前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(api_router, prefix="/api/v1")


# WebSocket 终端
@app.websocket("/ws/terminal/{asset_id}")
async def ws_terminal(websocket: WebSocket, asset_id: int):
    from app.api.v1.terminal import terminal_ws_handler
    await terminal_ws_handler(websocket, asset_id)


@app.get("/api/health", tags=["健康检查"])
async def health_check():
    return JSONResponse({"status": "ok", "service": "ops-platform"})
