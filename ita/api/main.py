"""
ITA 肤色分析系统 - FastAPI 主入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from ita.api.routes import router as api_router

# 创建应用
app = FastAPI(
    title="ITA 肤色分析系统",
    description="基于手机拍照的个人肤色自测程序，通过白纸校准计算 ITA° 并分类肤色",
    version="1.0.0"
)

# CORS 配置（允许移动端访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(api_router, prefix="/api")


# 挂载静态文件
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


@app.get("/")
async def root():
    """根路径重定向"""
    return {"message": "ITA 肤色分析系统 API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
