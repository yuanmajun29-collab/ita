# ITA 肤色分析系统

基于手机拍照的个人肤色自测程序。用户将前臂和白色A4纸放在一起拍照，程序自动分析肤色 ITA° 并分类。

## 功能特性

- 📷 **手机拍照分析**：调用手机后置摄像头拍照，或从相册选择
- 🔬 **ITA° 计算**：基于 CIELAB 色彩空间计算个体类型角（ITA°）
- 🤍 **白纸校准**：自动检测白纸区域，校正光照偏差
- 🏷️ **五级分类**：浅色、中等色、晒黑色、棕色、深色
- ☀️ **UV 防护建议**：根据肤色类型提供紫外线防护建议
- 📋 **历史记录**：本地存储分析历史，追踪肤色变化
- 📱 **移动端优化**：响应式设计，适配手机浏览器

## 技术架构

```
ita/
├── ita/
│   ├── core/               # 核心算法
│   │   ├── calibrator.py   # 白纸检测与颜色校准
│   │   ├── skin_detector.py # 皮肤区域检测（YCbCr + HSV）
│   │   ├── ita_calculator.py # ITA° 计算引擎（RGB→XYZ→Lab→ITA°）
│   │   └── classifier.py   # 肤色分类器（五分类 + Fitzpatrick）
│   └── api/                # FastAPI 后端
│       ├── main.py         # 应用入口
│       ├── routes.py       # API 路由
│       └── models.py       # 数据模型
├── static/                 # 前端 Web App
│   ├── index.html          # 单页应用
│   ├── css/style.css       # 样式
│   └── js/
│       ├── app.js          # 主逻辑
│       ├── camera.js       # 摄像头控制
│       └── api.js          # API 封装
└── requirements.txt
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
cd /root/projects/ita
python -m uvicorn ita.api.main:app --host 0.0.0.0 --port 8000
```

### 访问

- 🌐 Web 界面：http://localhost:8000
- 📖 API 文档：http://localhost:8000/docs

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/analyze | 上传图片进行肤色分析 |
| GET | /api/health | 健康检查 |
| GET | /api/categories | 获取所有肤色分类 |
| GET | /api/result/{id} | 查询历史结果 |

## 肤色分类标准

| 类别 | ITA° 范围 | 描述 | Fitzpatrick |
|------|----------|------|-------------|
| 浅色 | > 55° | 非常白皙 | I, II |
| 中等色 | 28° ~ 55° | 白皙到橄榄色 | II, III |
| 晒黑色 | 10° ~ 28° | 日晒后偏棕 | III, IV |
| 棕色 | -30° ~ 10° | 天然棕褐色 | IV, V |
| 深色 | < -30° | 深棕色至黑色 | V, VI |

## ITA° 计算公式

```
ITA° = arctan((L* - 50) / b*) × 180 / π
```

其中 L* 和 b* 来自 CIE L*a*b* 色彩空间（D65 标准光源）。

## 拍照要求

1. 在自然光下拍摄（白天靠窗，避免直射阳光）
2. 手臂平放，旁边放一张白色 A4 纸
3. 手机平行拍摄，避免阴影
4. 关闭闪光灯、美颜和滤镜

## License

MIT
