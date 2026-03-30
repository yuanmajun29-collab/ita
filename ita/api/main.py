"""
ITA 肤色分析系统 - FastAPI 主入口

启动方式:
    uvicorn ita.api.main:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from ita.api.routes import router

app = FastAPI(
    title="ITA 肤色分析系统",
    description="基于手机拍照的个人肤色自测程序 - 分析 ITA° 并分类肤色",
    version="1.0.0"
)

# 注册 API 路由
app.include_router(router)

# 静态文件目录
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")

# 挂载静态文件（API 路由之后，避免覆盖 /api/ 路径）
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def serve_index():
        """前端首页"""
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "ITA 肤色分析系统 API 运行中", "docs": "/docs"}
