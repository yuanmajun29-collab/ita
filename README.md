# ITA 肤色分析系统

基于手机拍照的个人肤色自测程序，通过分析前臂皮肤 + 白色A4纸参考，计算 ITA°（Individual Typology Angle）并分类肤色。

## 🎯 功能

- 📸 **拍照分析**：使用手机摄像头拍照或从相册选择
- 📄 **白纸校准**：自动检测白纸区域进行颜色归一化
- 🧪 **ITA° 计算**：RGB → CIELAB → ITA° 精确转换
- 🏷️ **五级分类**：浅色、中等色、晒黑色、棕色、深色
- 📊 **Fitzpatrick 映射**：对应 Fitzpatrick 皮肤分型

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
cd /root/projects/ita
uvicorn ita.api.main:app --host 0.0.0.0 --port 8000 --reload
```

访问 http://localhost:8000 即可使用。

## 📱 使用方法

1. 在自然光下（白天靠窗），将前臂平放
2. 在手臂旁放一张 A4 白纸
3. 手机平行拍摄，确保同时拍到手臂和白纸
4. 关闭闪光灯、美颜和滤镜
5. 上传照片，等待分析结果

## 🏗️ 项目结构

```
ita/
├── core/                    # 核心算法
│   ├── calibrator.py        # 白纸检测与颜色校准
│   ├── skin_detector.py     # 皮肤区域检测
│   ├── ita_calculator.py    # ITA° 计算引擎
│   └── classifier.py        # 肤色分类器
├── api/                     # FastAPI 后端
│   ├── main.py              # 主入口
│   ├── routes.py            # API 路由
│   └── models.py            # 数据模型
├── static/                  # 前端
│   ├── index.html
│   ├── css/style.css
│   └── js/{app,camera,api}.js
└── requirements.txt
```

## 🔬 ITA° 分类标准

| 分类 | ITA° 范围 | Fitzpatrick | 描述 |
|------|----------|-------------|------|
| 浅色 | > 55° | I-II | 非常白皙 |
| 中等色 | 28° ~ 55° | II-III | 白皙到橄榄色 |
| 晒黑色 | 10° ~ 28° | III-IV | 日晒后偏棕 |
| 棕色 | -30° ~ 10° | IV-V | 天然棕褐色 |
| 深色 | < -30° | V-VI | 深棕色至黑色 |

## 📡 API 接口

- `POST /api/analyze` - 上传图片进行肤色分析
- `GET /api/health` - 健康检查
- `GET /api/result/{id}` - 查询历史结果
- `GET /api/history` - 获取历史记录

## 📄 License

重庆泛智电子科技有限责任公司 © 2026
