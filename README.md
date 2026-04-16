# ITA 肤色分析系统

基于手机拍照的个人肤色自测程序，通过分析前臂皮肤 + 白色A4纸参考，计算 ITA°（Individual Typology Angle）并分类肤色。

## 🎯 功能

- 📸 **拍照分析**：使用手机摄像头拍照或从相册选择
- 📄 **白纸校准**：自动检测白纸区域进行颜色归一化
- 🧪 **ITA° 计算**：RGB → CIELAB → ITA° 精确转换
- 🏷️ **五级分类**：浅色、中等色、晒黑色、棕色、深色
- 📊 **Fitzpatrick 映射**：对应 Fitzpatrick 皮肤分型

## 🚀 快速开始

以下命令均在 **仓库根目录** 执行（该目录下应有 `requirements.txt` 与 `ita/` 包目录；若从本仓库克隆，即克隆后的顶层目录）。

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
PYTHONPATH=. uvicorn ita.api.main:app --host 0.0.0.0 --port 8000 --reload
```

- **`--host 0.0.0.0`**：在网卡上监听，便于局域网或其它机器访问（公网还需防火墙/安全组放行 **TCP 8000**）。
- **`--reload`**：修改代码后进程会自动重载；重载瞬间可能出现短暂连接失败，属正常现象。

访问 **http://localhost:8000**（或 `http://<服务器IP>:8000`）即可打开页面；接口文档：**http://localhost:8000/docs**。

#### 对「在线服务」评测结果的解读（与上述 uvicorn 命令对应）

在**已用上述命令启动服务**的前提下，浏览器上传分析、或命令行请求 **`http://127.0.0.1:8000`（或实际 IP:8000）** 得到的 JSON，含义一致。下面是最小自测与读法（与离线 `pytest`/`evaluate_data` 算法相同，但多覆盖**真实端口与网络**）。

**1）健康检查 `GET /api/health`**

```bash
curl -s http://127.0.0.1:8000/api/health
```

| 返回内容 | 怎么读 |
|----------|--------|
| `status` 为 `ok` | 进程与 SQLite 自检通过，服务可用。 |
| `version` | 应与当前包版本一致；若与预期不符，多为未重启旧进程或 `PYTHONPATH` 指向旧代码。 |
| 连接失败 / 超时 | 先确认 uvicorn 终端仍在跑、端口未被占用；远程访问再查防火墙与安全组。 |

**2）分析接口 `POST /api/analyze`（与网页「开始分析」同源）**

```bash
curl -s -X POST -F "file=@data/1.jpg" "http://127.0.0.1:8000/api/analyze"
```

（将 `data/1.jpg` 换成你的图片路径；需在仓库根目录执行，或写成绝对路径。）

| 返回情形 | 怎么读 |
|----------|--------|
| `success: true` | 流水线完成；`result` 内含 `ita`、`category`、`lab`、`calibration` 等，**逐项含义见下文「### 4) 8000 服务评测结果解读」**。 |
| `success: false` | 看 `message`：如未检测到白纸、皮肤区域、格式不支持等，与算法拒识条件一致，非 HTTP 500 即表示服务逻辑正常、仅本张图不达标。 |
| HTTP 4xx/5xx | 与业务 `success` 不同，多为网关、反代、或服务端异常，需查 uvicorn 终端日志。 |

**3）与「未启动 uvicorn」的测试有何不同**

| 方式 | 能说明什么 |
|------|------------|
| `pytest` / `verify_demo`（无监听） | 代码路径与 `data/` 回归是否正确。 |
| **本节约定的 curl / 浏览器 + 8000** | 在以上基础上，额外验证 **进程已监听、端口可达、与生产访问路径一致**。 |

**4）更完整的字段表**

分析 JSON 各字段、质量分、`pytest` 结论等，统一见 **「### 4) 8000 服务评测结果解读」**。

### 公网 IP 与「开始拍照」（两种方式）

浏览器对 **网页内实时摄像头**（`getUserMedia`）要求 **HTTPS** 或 **本机 `localhost` / `127.0.0.1`**。因此：

| 访问方式 | 「开始拍照」行为 | 实时预览 + 质量检测条 | 相册选图 |
|---------|------------------|------------------------|----------|
| `https://你的域名` | 网页内实时取景 | ✅ | ✅ |
| `http://localhost:8000` | 网页内实时取景 | ✅ | ✅ |
| `http://公网IP:8000` | **调起系统相机 / 相册**（`input capture`，非网页内流） | ❌（浏览器限制） | ✅ |

**说明：**

1. **HTTP + 公网 IP**：首页「开始拍照」会走 **系统相机或文件选择**，选片后分析流程与 HTTPS 一致；若需要 **画面内实时质量分** 与 **WebSocket 服务端质检**，请使用 **HTTPS 域名** 访问。
2. **配置 HTTPS**：为服务器绑定域名，用 **Nginx / Caddy** 反向代理到 `127.0.0.1:8000`，配置 **TLS**（如 Let’s Encrypt），通过 **`https://域名`** 访问即可恢复网页内实时预览。

示例（Nginx 片段，证书路径请按实际修改）：

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

## 📱 使用方法

1. 在自然光下（白天靠窗），将前臂平放
2. 在手臂旁放一张 A4 白纸
3. 手机平行拍摄，确保同时拍到手臂和白纸
4. 关闭闪光灯、美颜和滤镜
5. **画面中需以伸展的前臂为主**：系统会拒绝仅有面部特写、过小色块或不成条状的皮肤区域，避免误用非前臂照片
6. 上传照片，等待分析结果

## 🏗️ 项目结构

```
<仓库根>/
├── requirements.txt
├── ita/                     # Python 包
│   ├── core/                # 核心算法
│   │   ├── calibrator.py    # 白纸检测与颜色校准
│   │   ├── skin_detector.py
│   │   ├── arm_validator.py   # 前臂条状区域粗检
│   │   ├── ita_calculator.py
│   │   └── classifier.py
│   └── api/                 # FastAPI 后端
│       ├── main.py
│       ├── routes.py
│       └── models.py
├── static/                  # 前端
│   ├── index.html
│   ├── css/style.css
│   └── js/{app,camera,api}.js
├── scripts/                 # verify_demo、evaluate_data、visualize_data_report
├── tests/                   # pytest
├── data/                    # 样例图（测试与报告用）
└── reports/                 # 可视化报告默认输出（如 data_eval.html，可 gitignore）
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

## ✅ 开发测试与验证 Demo

### 1) 运行自动化接口冒烟测试

```bash
PYTHONPATH=. pytest -q
```

包含用例：
- 健康检查与版本一致性
- 历史/趋势空数据场景
- UV 建议接口基本可用性
- 分析接口非法文件拦截
- **`data/` 目录须存在且至少含一张样例图**（核心流水线、质量分、`/api/analyze` 回归）；无样例则 CI 失败

### 2) 运行本地验证 demo（无需启动 uvicorn）

```bash
PYTHONPATH=. python3 scripts/verify_demo.py
```

该脚本会在进程内调用关键 API，并输出 PASS/FAIL 汇总，便于演示和回归验证。

### 3) 生成 `data/` 验证可视化报告（HTML）

在浏览器中查看每张样例图的 **原图 / 质量叠加**、**ITA° 量尺**、**Lab 与分类**、**质量分对比条** 与分项摘要：

```bash
PYTHONPATH=. python3 scripts/visualize_data_report.py
```

- 默认输出：**`<仓库根>/reports/data_eval.html`**
- 自定义输出路径示例：

```bash
PYTHONPATH=. python3 scripts/visualize_data_report.py ./reports/my_report.html
```

用文件管理器打开生成的 HTML，或将终端打印的 `file://...` 地址粘贴到浏览器地址栏。

### 4) 8000 服务评测结果解读

以下说明适用于：

- 使用 **`PYTHONPATH=. uvicorn ita.api.main:app --host 0.0.0.0 --port 8000 --reload` 启动后**，通过浏览器或 `curl` 访问 **`/api/analyze`** 得到的 JSON；
- **`scripts/evaluate_data.py`** 的终端/JSON 输出、**`reports/data_eval.html` 报告**（与线上一致的分析逻辑）；
- **`pytest` / `verify_demo.py`** 的结论（逻辑同上，不经真实 TCP）。

字段含义相同，**入口差异**见上文「启动后在线评测与解读」表格（在线评测多验证端口与网络）。

#### 分析成功时各字段含义

| 字段 | 含义与读法 |
|------|------------|
| `success` / `message` | 业务是否完成；`success=false` 时看 `message`（如未检测到白纸、皮肤区域、图片无法解码等）。 |
| `ita` | **Individual Typology Angle（°）**；数值越大一般肤色越浅，越小越深。与仪器或文献对比时需相同部位、光照与校准方式。 |
| `category` | 由 ITA° 映射的**五档中文分类**（浅色 / 中等色 / …），非临床诊断。 |
| `fitzpatrick` | 与 ITA 区间对应的 **Fitzpatrick 分型区间**（如 I-II），供防晒等场景参考。 |
| `confidence` | 分类**置信度**（0～1），算法上为到类别中心的高斯型得分；**接近类别边界时往往偏低**，建议结合多次拍摄或看 `all_scores`。 |
| `lab` | **CIELAB**：`L*` 明度、`a*` 红绿、`b*` 黄蓝；与 ITA° 由同一套颜色换算得到。 |
| `calibration` | **白纸均值 RGB**、**皮肤采样 RGB**、**归一化后 RGB**；用于判断光照与白平衡是否合理（白纸过暗时通常会失败或提示改善光线）。 |
| `uv` / `vitd_advice` | 若请求时带了经纬度或时间等，可能附带紫外线与维D相关建议，为估算性质。 |

#### 质量评估（页面实时条、报告里的 quality）

| 项 | 含义 |
|----|------|
| **质量综合分**（0～1） | 模糊、亮度、白纸面积、皮肤覆盖、反光等加权，越高越利于拍照。 |
| **ready** | 是否达到「可以按快门」的门槛；**与 `analyze` 是否成功独立**——例如略模糊时仍可能返回 ITA，但 `ready=false`。 |
| **分项 checks** | 各子项 `score` 与文案提示，便于对症调整姿势与光线。 |

#### 报告中的 PASS / FAIL（`data_eval.html`）

- **PASS**：离线流水线（校准 → 皮肤 → ITA°）跑通。  
- **FAIL**：某一环节失败（常见为无白纸或无皮肤），需对照 `message` 与叠加图排查。

#### 自动化测试结论怎么读

| 结果 | 含义 |
|------|------|
| `pytest` 全部通过 | 健康检查、历史/趋势、UV 建议、非法文件拦截、**`data/` 样例图**等回归通过；说明当前代码与入库样例一致。 |
| `verify_demo.py` 全 PASS | 进程内 TestClient 调用关键 API 正常，适合无 uvicorn 时的冒烟。 |
| 二者均不替代 | **与真实用户照片的医学准确度**无直接等价；准确度依赖拍摄规范与算法边界条件。 |

更多分类阈值见上文「ITA° 分类标准」表。


## 📄 License

重庆泛智电子科技有限责任公司 © 2026
