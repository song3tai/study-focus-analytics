# Study Focus Analytics

## 项目简介

Study Focus Analytics 是一个面向学生、自习者和远程办公者的学习 / 工作状态分析系统。项目基于视频输入，对单人场景中的在岗情况、离岗行为和专注状态进行分析，并输出学习 / 工作时长、离岗时长、专注度估计等结果，最终通过 Web UI 进行可视化展示。它适用于自习监督、个人复盘、学习时长记录、轻量级办公状态分析等场景。本项目不是通用视频处理或 YOLO 演示项目，而是一个面向真实学习 / 工作场景的行为分析系统。

## 项目背景（Why this project）

当前很多 AI 项目停留在“目标检测 demo”层面，能够画框、能够识别人，但很少真正落到具体使用场景中。

Study Focus Analytics 关注的是一个更贴近真实需求的问题：在学习或工作场景下，如何基于视频输入分析一个人是否在岗、是否持续投入、离岗了多久，以及这些状态如何被结构化展示出来。

这个项目的出发点不是为了堆叠通用检测能力，而是希望围绕一个真实、有用且可持续迭代的场景，做出一条完整的分析与展示链路。

## 项目目标

项目当前聚焦构建一条清晰、可扩展的分析闭环：

`视频输入` -> `人体检测` -> `场景特征提取` -> `在岗 / 离岗状态判断` -> `学习 / 工作时长统计` -> `专注度估计` -> `Web UI 展示`

该闭环的目标不是单纯做目标检测，而是围绕“单人学习 / 工作场景”形成可解释、可统计、可展示的状态分析流程。

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

### 当前版本暂不实现

以下内容不属于当前 V1 的核心交付范围：

- 多人场景分析
- 复杂身份识别或个体追踪
- 高精度姿态估计与细粒度动作识别
- 完整生产级部署方案
- 跨端 App
- 复杂报表系统与长期数据平台化能力

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

React 前端属于 V1 目标的一部分，但当前仓库中尚未创建独立 `frontend/` 目录。

## Demo（示例展示）

- TODO：后续将在此补充系统运行效果，包括视频片段、关键截图和 Dashboard 展示效果
- 当前项目处于 V1 开发阶段，暂未提供完整 Demo

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
python -m pytest -q
```

### 4. 启动离线视频分析

默认模式为 `analyze`，会执行检测、场景特征提取、状态机、focus score 和统计汇总。

```bash
python src/main.py --input sample.mp4
```

如果视频文件放在项目 `input/` 目录下，直接传文件名即可：

```bash
python src/main.py --input sample.mp4 --no-display
```

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
python -m uvicorn web.api:create_app --factory --reload --app-dir src
```

启动后可访问：

- `GET /health`
- `GET /api/current`
- `GET /api/summary`
- `GET /api/events`
- `WS /ws/analysis`

### 常用命令汇总

```bash
source .venv/bin/activate
python -m pytest -q
python src/main.py --input sample.mp4
python src/main.py --input sample.mp4 --mode detect
python src/main.py --camera
python -m uvicorn web.api:create_app --factory --reload --app-dir src
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
- 接入 FastAPI
- 完成 React Dashboard 基础展示

### V1.5

- 优化状态分析稳定性
- 优化时间段合并与统计准确性
- 增强离线视频分析结果展示
- 改善可视化细节与结果解释性

### V2

- 引入姿态估计能力
- 增强行为识别能力
- 提升对低头、离座、持续活动等行为的判断质量
- 优化专注度估计逻辑

### V3

- 探索 C++ 媒体处理模块
- 探索 Python + C++ 混合架构
- 提升媒体处理与推理链路性能
- 为更稳定的实时分析能力做架构准备

## 文档说明

- `README.md`：面向使用者、GitHub 访客、面试官和项目关注者，用于了解项目定位、目标与当前进展
- `docs/design.md`：面向开发者，用于说明系统设计、模块边界与架构决策
- `docs/ai_context.md`：面向 AI 编码助手，用于提供项目上下文、协作约束与实现导向

## 当前状态说明

当前阶段最优先的工作包括：

- 完成项目结构重构
- 建立统一数据模型
- 建立状态机与事件模型
- 打通后端分析链路与 Web 展示链路

项目目前仍处于 V1 基础版本设计与实现阶段。当前工作的重点不是扩展功能范围，而是先把“输入、分析、统计、展示”这条主链路做清楚、做稳定、做成一个真正聚焦的工程项目。
