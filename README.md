# Study Focus Analytics

## 项目简介

Study Focus Analytics 是一个面向学生、自习者和远程办公者的学习 / 工作状态分析系统。项目基于视频输入，对单人场景中的在岗情况、离岗行为和专注状态进行分析，并输出学习 / 工作时长、离岗时长、专注度估计等结果，最终通过 Web UI 进行可视化展示。它适用于自习监督、个人复盘、学习时长记录、轻量级办公状态分析等场景。本项目不是通用视频处理或 YOLO 演示项目，而是一个面向真实学习 / 工作场景的行为分析系统，更进一步说，它正在演进为一个学习 / 工作状态复盘工具。

当前产品形态更适合按“本地优先”方向推进：视频分析与界面展示优先在用户本机完成，由本地 Python 分析服务和本地前端协同工作。这样既能降低云端计算和流量成本，也更符合个人学习 / 工作场景下对隐私友好和低部署成本的要求。

当前项目阶段为：

> V1 主链路已完成，进入 V1.5：离线分析体验与结果系统阶段

## 项目背景（Why this project）

当前很多 AI 项目停留在“目标检测 demo”层面，能够画框、能够识别人，但很少真正落到具体使用场景中。

Study Focus Analytics 关注的是一个更贴近真实需求的问题：在学习或工作场景下，如何基于视频输入分析一个人是否在岗、是否持续投入、离岗了多久，以及这些状态如何被结构化展示出来。

这个项目的出发点不是为了堆叠通用检测能力，而是希望围绕一个真实、有用且可持续迭代的场景，做出一条完整的分析与展示链路，并逐步把它打磨成真正可用的复盘工具。

## 项目目标

项目当前聚焦构建一条清晰、可扩展的分析闭环：

`视频输入` -> `人体检测` -> `场景特征提取` -> `在岗 / 离岗状态判断` -> `学习 / 工作时长统计` -> `专注度估计` -> `Web UI 展示`

该闭环的目标不是单纯做目标检测，而是围绕“单人学习 / 工作场景”形成可解释、可统计、可展示、可复盘的状态分析流程。

系统目标不仅是实时分析，更重要的是提供可复盘的分析结果。

## 核心使用方式（推荐）

1. 录制或导入一段学习 / 工作视频
2. 使用系统进行快速分析
3. 获取分析结果：
   - 在岗 / 离岗时间
   - 专注度变化
   - 离岗次数
4. 用于复盘和自我评估

该系统不仅用于“实时监控”，更用于“事后分析”。

## V1 范围

### 当前版本聚焦

V1 将重点收敛在“单人场景的基础状态分析”上，优先完成以下能力：

- 基于摄像头、RTSP 流和本地视频文件的统一输入能力
- 基于 YOLOv8 person 的单人检测能力
- 面向桌面学习 / 工作场景的基础 ROI 与场景特征提取
- `unknown / present / away / studying` 状态判断
- 学习 / 工作时长与离岗时长统计
- 基础专注度估计
- 后端分析结果到 Web UI 的可视化链路

当前项目已经完成上述 V1 主链路能力，并进入 V1.5 阶段。

V1.5 当前唯一主线是：

- 构建离线分析体验闭环
- 让视频文件支持快速分析
- 让用户直接获得清晰、可解释、可消费的结果

### 当前版本暂不实现

以下内容不属于当前阶段的核心交付范围：

- 多人场景分析
- 复杂身份识别或个体追踪
- 高精度姿态估计与细粒度动作识别
- 完整生产级部署方案
- 跨端 App
- 复杂报表系统与长期数据平台化能力
- 云端架构
- Electron
- 数据库系统
- 检测能力扩展

## 核心功能

### 视频输入

- 支持摄像头输入
- 支持 RTSP 实时流输入
- 支持本地录制视频输入
- 统一为后续分析模块提供帧流数据

### 人体检测

- 基于 YOLOv8 person 类别进行单人检测
- 为后续状态判断与场景特征提取提供目标区域基础信息
- 当前聚焦单人学习 / 工作场景，不追求通用复杂场景覆盖

### 状态分析

系统计划围绕以下状态进行基础建模：

- `unknown`：当前帧或当前时间段无法可靠判断状态
- `present`：人物在位，但未满足明确学习 / 工作判定条件
- `away`：人物离开主要工作区域或持续不在岗
- `studying`：人物处于学习 / 工作中的有效在岗状态

### 时长统计

- 统计总学习 / 工作时长
- 统计离岗时长
- 支持基于状态机的时间累计逻辑
- 为后续日报、复盘和趋势分析提供基础数据

### 专注度估计

- 基于在岗状态、连续时长、场景稳定性等特征构建基础 focus score
- 当前阶段采用可解释、可迭代的规则或轻量模型方案
- 不将“专注度”定义为绝对心理状态，而是作为场景行为层面的估计指标

### Web UI 展示

- 展示当前状态
- 展示学习 / 工作累计时长与离岗时长
- 展示基础专注度结果
- 提供面向使用者的直观 Dashboard 视图

## 当前阶段重点

当前版本已经完成：

- 分析主链路（pipeline）
- 行为状态机
- 专注度估计
- Web API
- Dashboard
- MJPEG 视频预览

因此，项目已经从“架构建设阶段”进入“可运行系统 + 可展示 MVP 阶段”。

当前优先级为：

- 离线分析体验
- 结果表达：`summary / timeline / events`
- 状态稳定性优化
- Dashboard 表达优化

## 技术栈

### 后端

- Python 3.10+
- OpenCV
- NumPy
- Ultralytics YOLOv8
- FastAPI

### 前端

- React
- TypeScript

### 运行形态

- 当前 V1 推荐形态是本地运行的 Python 分析后端 + 本地运行的 React 前端
- 当前以前后端在本机联调为主，不依赖云端 GPU 推理服务
- 当前阶段暂不推进 Electron
- 后续如有需要，再演进为基于 Electron 的 Windows 桌面应用

## 项目结构

以下为规划中的 V1 目录结构：

```text
Study Focus Analytics/
├── README.md
├── requirements.txt
├── docs/
│   ├── design.md
│   └── ai_context.md
├── src/
│   ├── main.py
│   ├── config.py
│   ├── utils.py
│   ├── core/
│   ├── io/
│   ├── inference/
│   ├── behavior/
│   ├── pipeline/
│   └── web/
└── tests/
```

目录职责将大致分为：

- `src/io/`：视频输入与数据接入
- `src/inference/`：人体检测与推理能力
- `src/behavior/`：状态机、事件模型、时长统计、专注度估计
- `src/pipeline/`：分析链路编排
- `src/web/`：后端接口与 Web 服务接入
- `docs/`：设计文档与协作上下文文档
- `tests/`：核心模块测试

当前主干已经收口为单一正式 pipeline 实现：

- 正式实现文件：`src/pipeline/analysis_pipeline.py`
- 正式包级导出入口：`from src.pipeline import LocalAnalysisPipeline, PipelineConfig`
- `src/pipeline/pipeline.py` 仅保留为兼容导入转发层，不再承载第二套逻辑

React 前端属于 V1 目标的一部分，但当前仓库中尚未创建独立 `frontend/` 目录。

## Demo（示例展示）

- TODO：后续将在此补充系统运行效果，包括视频片段、关键截图和 Dashboard 展示效果
- 当前项目处于 V1.5 打磨阶段，暂未提供完整 Demo

## 本地优先架构说明

当前项目优先以本地运行形态推进。

- V1：本地 Python 分析服务 + 本地 React 前端
- V1.5：离线分析体验与结果系统
- 当前不以云端集中部署为主要目标

这种推进方式更适合当前阶段：先把离线分析体验、结果表达和复盘价值做扎实，再考虑进一步的桌面化封装。

## 安装与启动

### 1. 创建并激活虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 安装依赖

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. 运行测试

```bash
python3 -m pytest tests -q
```

测试依赖当前包含在 `requirements.txt` 中，至少需要保证以下模块可导入：

- `pytest`
- `opencv-python`（提供 `cv2`）

当前仓库已经在本地完成过一次实际验证：

```bash
python3 -m pytest tests -q
```

结果为 `30 passed`。

### 4. 启动离线视频分析

默认模式为 `analyze`，会执行检测、场景特征提取、状态机、focus score 和统计汇总。

```bash
python src/main.py --input sample.mp4
```

如果视频文件放在项目 `input/` 目录下，直接传文件名即可：

```bash
python src/main.py --input sample.mp4 --no-display
```

如果你在代码中直接复用逐帧分析主链路，优先使用：

```python
from src.pipeline import LocalAnalysisPipeline, PipelineConfig
```

当前视频文件分析正在从“按播放节奏运行”逐步演进到“支持快速离线分析”。当前阶段推荐优先把视频文件分析理解为复盘场景，而不只是播放场景。

### 5. 启动检测预览模式

```bash
python src/main.py --input sample.mp4 --mode detect
```

### 6. 启动摄像头分析

```bash
python src/main.py --camera
```

### 7. 启动 RTSP 分析

```bash
python src/main.py --rtsp-url rtsp://your-stream-address --rtsp-transport tcp
```

### 8. 保存分析结果视频

本地文件输入支持保存输出视频：

```bash
python src/main.py --input sample.mp4 --save --output output/analysis.mp4
```

### 9. 启动 FastAPI 服务

当前仓库已经提供了 V1 的 FastAPI 接口骨架，可用于对接前端或联调接口。

```bash
python -m uvicorn web.api:app --host 127.0.0.1 --port 8000 --reload --app-dir src
```

如果 `8000` 端口已被占用，可以直接改用：

```bash
python -m uvicorn web.api:app --host 127.0.0.1 --port 8001 --reload --app-dir src
```

## Windows 真实联调

当前推荐把真实运行链路整体放到 Windows 本机执行，而不是拆成 Windows + WSL 跨环境联调。

### 1. 准备 Windows Python 环境

在 PowerShell 中：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

如果 `pytest`、`cv2` 或 `fastapi` 导入失败，优先重新执行一次 `python -m pip install -r requirements.txt`。

如果 Dashboard 能打开但 `WS /ws/analysis` 握手失败，通常说明当前 Python 环境缺少 WebSocket 运行依赖。当前仓库已将 `websockets` 包含在 `requirements.txt` 中，重新执行一次依赖安装即可：

```powershell
python -m pip install -r requirements.txt
```

### 2. 启动 Web 服务

在项目根目录执行：

```powershell
python -m uvicorn web.api:app --host 127.0.0.1 --port 8000 --reload --app-dir src
```

如果提示 `WinError 10048`，说明 `8000` 端口已被占用，可改用：

```powershell
python -m uvicorn web.api:app --host 127.0.0.1 --port 8001 --reload --app-dir src
```

浏览器或前端可直接访问：

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/analysis/status`
- `http://127.0.0.1:8000/analysis/latest`
- `http://127.0.0.1:8000/analysis/summary`
- `ws://127.0.0.1:8000/ws/analysis`

### 3. 先验证本地视频文件

推荐先用仓库自带视频验证完整链路：

```powershell
curl -Method POST http://127.0.0.1:8000/analysis/start `
  -ContentType "application/json" `
  -Body '{"source_type":"video_file","source":"input/sample.mp4","debug":false}'
```

验证中可轮询：

```powershell
curl http://127.0.0.1:8000/analysis/status
curl http://127.0.0.1:8000/analysis/latest
curl http://127.0.0.1:8000/analysis/summary
```

停止分析：

```powershell
curl -Method POST http://127.0.0.1:8000/analysis/stop
```

### 4. 再验证 USB 摄像头

Windows 下推荐先从 `source=0` 开始尝试：

```powershell
curl -Method POST http://127.0.0.1:8000/analysis/start `
  -ContentType "application/json" `
  -Body '{"source_type":"camera","source":"0","debug":false}'
```

如果 `0` 打不开，再试 `1`、`2`。当前代码会优先尝试 Windows 常见的 OpenCV 摄像头 backend，再回退到默认 backend。

### 5. 常见问题

- 摄像头打不开：
  - 先确认 Windows 自带“相机”应用能否正常读取设备
  - 关闭可能占用摄像头的应用，例如微信、腾讯会议、OBS、浏览器
  - 尝试把 `source` 从 `0` 改为 `1`

- 视频文件打不开：
  - 优先使用相对项目根目录的路径，例如 `input/sample.mp4`
  - 也可以直接传 Windows 绝对路径，例如 `C:\\Users\\you\\Videos\\sample.mp4`

- 浏览器连不上：
  - 先确认 `uvicorn` 已启动在 `127.0.0.1:8000`
  - 如果 `8000` 已被占用，改用 `8001` 或其他空闲端口重新启动
  - 先访问 `/health`，再访问 `/analysis/status`

启动后可访问：

- `GET /health`
- `GET /analysis/status`
- `GET /analysis/latest`
- `GET /analysis/summary`
- `POST /analysis/start`
- `POST /analysis/stop`
- `WS /ws/analysis`

更完整的请求体、响应体和 WebSocket 消息说明见 [docs/design.md](/d:/0.workspace/study-focus-analytics/docs/design.md) 中的 API Reference 小节。

### 常用命令汇总

```bash
source .venv/bin/activate
python -m pytest tests -q

Note: this project disables pytest's cache provider by default to avoid creating broken cache temp directories in this Windows workspace.
python src/main.py --input sample.mp4
python src/main.py --input sample.mp4 --mode detect
python src/main.py --camera
python -m uvicorn web.api:app --host 127.0.0.1 --port 8000 --reload --app-dir src
```

## Roadmap

### V1

- 完成项目结构重构
- 建立统一数据模型
- 建立单人场景 ROI 机制
- 完成基础场景特征提取
- 建立 `unknown / present / away / studying` 状态机
- 完成学习 / 工作时长与离岗时长统计
- 建立基础 focus score
- 接入本地运行的 FastAPI 分析后端
- 完成本地运行的 React Dashboard 基础展示
- 在浏览器中完成前后端联调
- 不依赖云端 GPU 服务

### V1.5

- 视频文件快速分析模式
- 离线分析结果页
- 事件流输出
- 结果表达优化
- 状态稳定性小步优化
- Dashboard 表达优化

### V2

- 历史结果管理
- 更完整的本地复盘体验
- 本地配置与分析结果组织
- 在明确价值后再增强能力边界

### V3

- 探索 C++ 媒体模块
- 优化 RTSP / 解码 / 性能
- 提升媒体处理与推理链路性能
- 为更稳定的实时分析能力做架构准备

## 文档说明

- `README.md`：面向使用者、GitHub 访客、面试官和项目关注者，用于了解项目定位、目标与当前进展
- `docs/design.md`：面向开发者，用于说明系统设计、模块边界与架构决策
- `docs/ai_context.md`：面向 AI 编码助手，用于提供项目上下文、协作约束与实现导向

## 当前状态说明

当前阶段最优先的工作包括：

- 视频文件快速分析模式
- 离线分析结果页
- 事件流与时间线表达
- 结果系统优化
- 状态稳定性小步优化

项目目前已经从 V1 架构建设阶段进入 V1.5 产品化阶段。当前工作的重点不是继续扩展分析边界，而是先把“快速分析、结果输出、结果理解、结果复盘”这条主线做清楚、做稳定、做出真实使用价值。
