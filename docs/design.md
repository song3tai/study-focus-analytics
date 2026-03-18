# Study Focus Analytics Design

## 文档目的

本文档用于说明 Study Focus Analytics 的系统设计、模块边界、核心数据流和 V1 阶段的架构取舍，面向开发者、未来维护者以及需要理解系统实现方式的人。

本文件关注的是“系统如何组织与实现”，而不是“项目是什么、如何快速了解项目”。如果需要查看项目定位、阶段目标和面向使用者的说明，应阅读 `README.md`。

## 项目定位

Study Focus Analytics 是一个面向学生、自习者和远程办公者的学习 / 工作状态分析系统。它的核心任务不是做通用目标检测，也不是做复杂安防平台，而是在单人、单机位、固定区域的前提下，围绕“人是否在岗、是否处于学习 / 工作状态、持续了多久、专注度如何”这一问题建立一条可解释、可展示、可迭代的分析链路。

当前设计边界明确如下：

- 场景以单人、桌面、自习 / 办公区域为主
- 输入形式以摄像头、RTSP 实时流和本地视频为主
- 分析方式以 YOLO person 检测 + 规则特征 + 轻量状态机为主
- 输出形式以结构化状态、事件、统计结果和 Web UI 展示为主

这意味着项目的重点不在于追求复杂模型堆叠，而在于把单人场景下的分析流程做清楚：输入稳定、特征明确、状态可解释、结果可汇总、前端可展示。

## V1 设计目标

V1 的目标不是做一个大而全的平台，而是建立一套最小但完整的分析闭环，并为后续扩展保留清晰边界。

### 1. 复用已有输入与检测能力

当前仓库已经具备一定的视频读取、RTSP 输入和 YOLOv8 检测基础。V1 应尽可能复用这部分能力，避免在输入和检测层重复造轮子，把主要精力放在行为分析链路的建立上。

### 2. 在 YOLO person 检测之上构建行为分析链路

YOLO person 检测在本项目中不是终点，而是后续分析的起点。V1 需要将“是否检测到人、人在不在 ROI 内、位置是否稳定、持续了多久”等信息转化为行为状态、事件和统计结果，而不是停留在目标框渲染层。

### 3. 建立统一数据模型

V1 需要尽早建立统一的结构化数据模型，使得输入、检测、特征、状态、事件、汇总等对象之间可以稳定流转。统一模型的价值在于：

- 避免处理逻辑散落在多个脚本和临时变量中
- 避免后续 API、测试、前端展示各自定义一套数据格式
- 为离线分析与实时分析复用同一条处理链路提供基础

### 4. 引入可解释状态机

V1 的状态判断应以可解释状态机为核心，而不是直接引入黑盒模型。系统需要明确区分 `unknown / present / away / studying` 四类状态，并通过窗口判断、确认时长和去抖逻辑实现稳定切换。

### 5. 同时支持实时分析与离线分析

虽然实时分析和离线分析在交互方式上不同，但它们应共享尽可能一致的后端处理逻辑。V1 应采用统一的分析管线，让视频文件分析和摄像头 / RTSP 实时分析都使用同样的数据结构与行为逻辑。

### 6. 为 React 前端提供 API / WebSocket 数据

V1 需要明确前后端的解耦边界。后端负责分析和结构化结果输出，前端负责展示当前状态、时间统计、事件流和时间线。REST 用于请求和查询，WebSocket 用于直播式状态推送。

### 7. 保持架构轻量清晰

V1 不需要复杂的企业级架构。当前项目规模下，最重要的是模块职责清楚、数据模型统一、状态链路稳定、前后端接口清晰，而不是引入额外中间层或分布式系统。

## 非目标

以下内容明确不属于 V1 的设计目标：

- 多人复杂跟踪
- 人脸识别
- 身份识别
- 数据库持久化设计
- 用户系统
- 多摄像头集中管理平台
- 黑盒专注力模型
- 复杂分布式架构
- WebRTC 全链路视频方案

这些内容并非永远不会做，而是它们会显著增加系统复杂度，并稀释当前最核心的问题：如何在单人固定场景下构建一条真实可跑、可解释、可展示的行为分析链路。

## 总体架构

系统推荐采用如下总体架构流：

`Video Source -> Input Layer -> Detection Layer -> Scene Feature Layer -> State Tracker -> Focus Estimator -> Event / Summary Aggregator -> FastAPI / WebSocket -> React Dashboard`

### 后端职责

后端承担分析职责，负责：

- 接收和管理视频输入
- 执行人体检测
- 提取场景行为特征
- 维护状态机
- 计算专注度估计
- 生成事件流与统计结果
- 通过 REST 和 WebSocket 向前端暴露结构化数据

后端的核心不是“把视频显示出来”，而是把连续帧转换成稳定的行为语义。

### 前端职责

前端承担展示职责，负责：

- 展示当前状态
- 展示学习 / 工作时长、离岗时长等统计结果
- 展示专注度等级和变化趋势
- 展示事件流、时间线和离线分析结果页
- 为用户提供启动分析、查看结果、理解状态变化的可视化入口

前端不负责行为判断逻辑，不复制状态机，不重新推导专注度。它消费的是后端已经生成的结构化结果。

## 当前代码结构与 V1 架构映射

当前项目最初具备一套偏原型化的视频处理结构，V1 的实现方式是在现有能力基础上逐步重构和迁移，而不是完全重写一套新系统。

建议的映射关系如下：

- `src/video_reader.py` 已迁移为 `src/io/video_reader.py`
- `src/video_writer.py` 已迁移为 `src/io/video_writer.py`
- `src/ai_detector.py` 已收敛为 `src/inference/ai_detector.py`
- 旧版 `frame_processor` 通用图像模式已从 V1 主链路移除
- `src/pipeline.py` 已迁移为 `src/pipeline/analysis_pipeline.py`
- `src/main.py` -> 保持为入口，但只负责 wiring、启动和高层流程连接
- `src/utils.py` -> 保留，作为通用工具模块
- `src/config.py` -> 保留，后续可能增强配置能力

这里的核心原则是：当前不是“推倒重写”，而是“逐步迁移 + 重构”。实现顺序上应优先保证功能可运行，再逐步优化结构、边界和模块职责。

## 模块划分

推荐 V1 采用如下目录分层：

- `src/core/`
- `src/io/`
- `src/inference/`
- `src/behavior/`
- `src/pipeline/`
- `src/web/`

### src/core/

`core` 层负责定义全项目统一的数据模型、基础枚举和值对象。它是各模块之间的公共语言，避免不同层各自传递裸字典、元组或不稳定字段。

建议内容包括：

- 状态枚举，如 `unknown / present / away / studying`
- 事件类型枚举
- 输入源类型枚举，如 `camera / rtsp / file`
- 核心数据对象定义，如 `FramePacket`、`DetectionResult`、`FrameFeatures`、`BehaviorStateSnapshot`、`ProcessResult`
- 通用时间、坐标、区域等值对象

`core` 层不负责业务判断逻辑，但负责定义“业务结果长什么样”。

### src/io/

`io` 层负责所有视频输入输出能力，目标是把不同来源的视频统一包装成一致的帧数据输入。

职责包括：

- 摄像头输入
- RTSP 实时流输入
- 本地视频文件输入
- 输入生命周期管理
- 帧时间戳与来源信息补齐
- 可选视频输出

`io` 层的设计重点是输入统一，而不是分析逻辑。它不应承担行为判断，也不应直接耦合前端接口。

### src/inference/

`inference` 层负责目标检测能力，V1 当前聚焦 YOLOv8 person 检测。

职责包括：

- 加载 YOLOv8 模型
- 对单帧执行 person 检测
- 输出结构化检测结果
- 控制推理参数与性能测量
- 将底层模型输出转换为统一 `Detection` / `DetectionResult`

这一层不应直接做时长统计、状态判断或专注度计算。它的边界很明确：从帧到检测结果。

### src/behavior/

`behavior` 层是项目核心。它将“检测到什么”转化为“用户处于什么状态、发生了什么事件、累计了什么统计结果”。

建议包含以下模块：

- `scene_features`
- `state_tracker`
- `focus_estimator`
- `event_builder`
- `analytics_aggregator`

#### scene_features

`scene_features` 负责从当前帧和检测结果中提取用于行为判断的特征。其职责是把检测层输出转化为更接近业务语义的中间层信息。

典型输出包括：

- 当前是否检测到人
- 人是否位于学习 / 工作区域 ROI 内
- 主目标框位置与大小
- 目标中心点
- ROI 重叠比例
- 运动变化程度
- 稳定度得分

这一步的价值在于把检测结果标准化为行为分析所需的固定字段，使后续状态机不需要关心底层模型细节。

#### state_tracker

`state_tracker` 负责维护系统当前行为状态，是整个行为层最重要的模块。它基于 `FrameFeatures` 和短时历史窗口判断当前状态，并负责状态去抖和状态切换确认。

它的职责包括：

- 定义状态机当前状态
- 维护状态开始时间与持续时间
- 基于窗口而非单帧进行状态判定
- 控制 `unknown / present / away / studying` 的切换逻辑
- 产出当前状态快照
- 为事件生成器提供切换信息

`state_tracker` 不是一个简单 if-else 函数，而是需要维护时间上下文和历史上下文的状态容器。

#### focus_estimator

`focus_estimator` 负责根据行为状态和近期特征生成专注度估计结果。V1 中它不应是黑盒模型，而应是基于规则和简单权重的可解释估计器。

其职责包括：

- 消费最近窗口的状态和特征
- 结合在岗比例、稳定度、离岗次数、ROI 对齐等指标
- 输出 `focus_score`
- 输出离散化的 `focus_level`
- 输出解释原因 `reasons`

该模块的重点不是“绝对准确地测量心理注意力”，而是生成一套稳定、可理解、可逐步改进的专注状态估计。

#### event_builder

`event_builder` 负责将状态切换和关键行为片段转化为结构化事件流。事件是系统的重要输出，因为前端时间线、日志列表和离线回放都依赖它。

典型事件包括：

- 状态从 `unknown` 转为 `present`
- 状态从 `present` 转为 `away`
- 状态从 `present` 或 `away` 转为 `studying`
- 一次离岗结束
- 一段学习会话开始或结束

该模块不维护业务总状态，而是把状态变化格式化为明确、可消费的事件记录。

#### analytics_aggregator

`analytics_aggregator` 负责汇总级统计，包括时长、次数、平均专注度等数据。它从状态流、事件流和专注度结果中累计得出会话级摘要。

其职责包括：

- 累计总时长
- 累计在岗时长
- 累计离岗时长
- 累计 studying 时长
- 统计离岗次数
- 统计平均 / 最大 / 最小 focus score
- 生成 `AnalysisSummary`

它是从“每帧分析结果”走向“用户可读统计结果”的关键一步。

### src/pipeline/

`pipeline` 层负责把前述各模块连接成一条可运行的分析链路。推荐核心模块为 `analysis_pipeline`。

其职责包括：

- 从 `io` 获取 `FramePacket`
- 调用 `inference` 获取 `DetectionResult`
- 调用 `scene_features` 生成 `FrameFeatures`
- 调用 `state_tracker` 更新状态并生成 `BehaviorStateSnapshot`
- 调用 `focus_estimator` 生成 `FocusEstimate`
- 调用 `event_builder` 生成可选事件
- 调用 `analytics_aggregator` 更新汇总数据
- 输出统一 `ProcessResult`

`pipeline` 本身不承载具体规则判断，它的职责是编排和生命周期控制。

### src/web/

`web` 层负责对外暴露分析结果，建议包括：

- `api`
- `schemas`
- `websocket_manager`

#### api

`api` 负责 REST 接口定义和请求入口，如启动分析、停止分析、查询当前状态、查询汇总信息、查询事件与时间线。

#### schemas

`schemas` 负责定义对外接口的数据模式。它与 `core` 层相关，但不完全等同。`core` 面向内部统一模型，`schemas` 面向外部 API 表达，必要时可以做字段裁剪或序列化转换。

#### websocket_manager

`websocket_manager` 负责实时状态广播和连接管理，用于将实时分析结果推送给 React Dashboard。

## 核心数据流

推荐 V1 使用如下统一数据流：

`FramePacket -> DetectionResult -> FrameFeatures -> BehaviorStateSnapshot -> FocusEstimate -> BehaviorEvent(optional) -> ProcessResult`

### FramePacket

输入层输出统一帧对象，包含帧数据、时间戳、来源类型和来源标识。

### DetectionResult

检测层输出结构化检测结果，而不是直接返回绘制后的图像。此时系统已经知道当前帧中是否存在 person、位置在哪里、置信度如何。

### FrameFeatures

行为层先从检测结果中提取场景特征，如是否在 ROI 内、位置是否稳定、目标面积是否合理、运动波动是否过大等。这个阶段的数据比检测结果更贴近行为语义。

### BehaviorStateSnapshot

状态跟踪器基于当前特征和历史窗口生成当前状态快照。它表达的是“系统认为此刻用户处于什么状态，以及这个状态已经持续了多久”。

### FocusEstimate

专注度估计器根据近期窗口和当前状态生成专注度分数、等级及解释理由。

### BehaviorEvent(optional)

当发生状态变化或其他关键行为节点时，系统生成事件对象。并非每帧都会生成事件，因此它是可选输出。

### ProcessResult

每一帧或每个处理周期的最终统一输出，包含当前帧分析结果、当前状态、专注度结果、可选事件和当前汇总信息。

### 为什么要使用统一结构化结果

V1 不应延续“detect-only 渲染图输出”的模式，原因如下：

- 渲染图只适合预览，不适合后续状态分析
- 前端真正需要的是状态、事件、统计和时间线，而不是仅有框线的图像
- 离线分析、实时分析、测试和 API 输出都需要稳定数据结构
- 统一结构化结果更容易做测试、回放、调试和日志记录
- 结构化结果使检测层和行为层之间形成清晰边界，避免逻辑耦合

换句话说，图像渲染是附属能力，结构化结果才是系统核心产物。

## 核心数据结构

以下为推荐核心对象及其主要字段。这里描述的是设计层面的数据模型，不是完整 Python 代码。

### FramePacket

表示输入层交给分析链路的原始帧单元。

建议字段：

- `frame_id`：当前帧的唯一顺序编号
- `timestamp`：帧对应的时间戳，实时流可为采集时间，文件可为播放时间
- `source_type`：输入源类型，如 `camera`、`rtsp`、`file`
- `source_name`：输入源名称或标识
- `is_live`：是否为实时流
- `frame`：实际图像帧数据

### Detection

表示单个检测目标。

建议字段：

- `class_id`：类别 ID
- `class_name`：类别名称，V1 主要为 `person`
- `confidence`：置信度
- `bbox`：边界框，建议使用 `x1, y1, x2, y2` 或统一坐标结构表示

### DetectionResult

表示单帧检测结果。

建议字段：

- `frame_id`：对应输入帧 ID
- `timestamp`：对应输入帧时间戳
- `detections`：检测目标列表
- `inference_ms`：检测耗时

### ROI

表示学习 / 工作区域。

建议字段：

- `x`：左上角横坐标
- `y`：左上角纵坐标
- `w`：宽度
- `h`：高度

V1 中 ROI 建议保持简单，可由配置给出，或通过后续小范围交互方式设定。

### FrameFeatures

表示从当前帧提取的行为分析特征，是状态机的重要输入。

建议字段：

- `person_detected`：是否检测到人
- `person_in_roi`：人是否位于 ROI 内
- `primary_bbox`：当前主目标框
- `bbox_center`：目标框中心点
- `bbox_area`：目标框面积
- `bbox_aspect_ratio`：目标框宽高比
- `roi_overlap_ratio`：目标框与 ROI 的重叠比例
- `motion_delta`：相邻帧之间的运动变化量
- `stability_score`：位置 / 姿态 / 尺度的稳定度得分

### BehaviorStateSnapshot

表示当前时刻的状态快照和累计时长信息。

建议字段：

- `current_state`：当前状态
- `state_duration_sec`：当前状态已持续时长
- `current_session_duration_sec`：当前连续在岗 / 学习会话时长
- `current_away_duration_sec`：当前连续离岗时长
- `total_present_duration_sec`：累计在岗时长
- `total_away_duration_sec`：累计离岗时长
- `total_studying_duration_sec`：累计 studying 时长
- `away_count`：累计离岗次数

### FocusEstimate

表示专注度估计结果。

建议字段：

- `focus_score`：数值型分数，建议统一到固定区间，如 `0-100`
- `focus_level`：离散等级，如 `low / medium / high`
- `reasons`：解释当前得分的原因列表

### BehaviorEvent

表示关键事件。

建议字段：

- `event_type`：事件类型
- `timestamp`：事件时间
- `frame_id`：触发事件的帧 ID
- `state_before`：切换前状态
- `state_after`：切换后状态
- `message`：面向前端或日志的简要说明
- `payload`：附加信息，如时长、阈值命中原因、窗口统计值

### AnalysisSummary

表示会话级汇总结果。

建议字段：

- `total_duration_sec`：总分析时长
- `total_present_duration_sec`：累计在岗时长
- `total_away_duration_sec`：累计离岗时长
- `total_studying_duration_sec`：累计 studying 时长
- `away_count`：累计离岗次数
- `average_focus_score`：平均专注度得分
- `max_focus_score`：最高专注度得分
- `min_focus_score`：最低专注度得分

## 状态机设计

状态机是 V1 的核心设计之一。它需要把波动的检测结果转化为稳定、可解释的行为状态。

### 状态定义

#### unknown

表示当前无法稳定判断用户状态。常见情况包括：

- 连续若干帧未检测到有效 person
- 检测结果不稳定
- 目标位置异常，无法确认是否在有效区域内
- 系统刚启动，尚未积累足够历史窗口

#### present

表示用户处于在岗状态，即人在场、位于主要工作区域附近，但尚未满足进入 `studying` 的确认条件。

这是一种中间稳定状态，表明“人已经在位”，但系统暂不进一步断定其已进入持续学习 / 工作状态。

#### away

表示用户离开主要工作区域，或在一段确认时间内持续不在岗。

`away` 的关键不是某一帧缺失，而是经过确认后，系统认为用户已经离岗。

#### studying

表示用户处于持续、稳定、符合规则的学习 / 工作状态。通常意味着：

- 人在 ROI 内
- 位置和状态相对稳定
- 已连续满足一定时间阈值
- 不存在明显离岗或强波动行为

### 状态图

```text
           +-----------+
           |  unknown  |
           +-----------+
            |    |   \
            |    |    \
            |    |     \
            v    v      v
      +---------+    +------+
      | present |<-->| away |
      +---------+    +------+
            |
            |
            v
      +-----------+
      | studying  |
      +-----------+
            |
            v
         present
```

补充说明：

- `unknown -> present`：检测稳定且确认有人在岗
- `unknown -> away`：启动后较长时间确认无人
- `present -> studying`：满足持续稳定工作 / 学习条件
- `studying -> present`：虽然仍在岗，但不再满足 studying 条件
- `present -> away`：持续确认离岗
- `away -> present`：重新回到在岗状态
- `studying -> away`：发生持续离岗并达到确认阈值
- 任意状态在信息不足时可回落到 `unknown`，但应谨慎触发

### 状态切换规则

推荐 V1 采用“候选状态 + 确认时长 + 窗口判断”的方式，而不是单帧即切换。

建议规则如下：

- 当系统在近窗口内持续检测到 person，且目标位于 ROI 内时，进入 `present` 候选
- 当 `present` 候选持续超过 `present_confirm_seconds` 时，切换到 `present`
- 当近窗口内持续无人、或人持续离开 ROI，进入 `away` 候选
- 当 `away` 候选持续超过 `away_confirm_seconds` 时，切换到 `away`
- 当处于 `present` 状态，且近窗口内满足稳定、在岗、低波动、高 ROI 对齐等条件，并持续超过 `studying_confirm_seconds` 时，切换到 `studying`
- 当处于 `studying` 状态，但稳定度下降、ROI 对齐不足或动作波动明显增大时，可回落到 `present`
- 当处于 `present` 或 `studying`，若持续离岗达到阈值，则切换到 `away`

### 推荐阈值

V1 推荐起始阈值如下：

- `present_confirm_seconds = 1.0`
- `away_confirm_seconds = 2.0`
- `studying_confirm_seconds = 10.0`

这些值不应视为绝对正确，而应作为工程上可运行、便于调试的初始默认值。后续可通过测试样本和真实场景反馈调整。

### 去抖原则

状态切换不能基于单帧判断，必须基于近窗口统计。

推荐原则：

- 不因单帧漏检直接从 `present` 切到 `away`
- 不因单帧抖动直接从 `studying` 回退
- 使用最近若干秒或若干帧的窗口统计而不是瞬时值
- 优先保证状态稳定性，再追求响应速度
- 状态切换时尽可能保留切换原因，便于后续事件解释与调试

## 专注度设计

V1 中的专注度不是心理学意义上的真实注意力测量，而是“基于可观察行为信号的专注状态估计”。

这一定义非常重要。系统只能观察画面中的行为模式，不能直接知道用户在想什么。因此，V1 的 focus score 应被理解为行为层估计，而不是心理状态判决。

### 可参考特征

专注度估计可综合以下信息：

- 最近窗口内在岗比例
- 最近窗口内离岗次数
- 姿态 / 位置稳定度
- ROI 对齐程度
- 动作波动强度
- 连续 studying 时长

可以理解为：越稳定、越持续、越贴近工作区域、越少中断，focus score 越高；反之则越低。

### 输出结构

专注度模块输出：

- `focus_score`
- `focus_level`
- `reasons`

其中：

- `focus_score` 用于数值展示和趋势分析
- `focus_level` 用于前端快速表达当前状态
- `reasons` 用于解释为什么当前得分高或低

### 设计取舍

V1 专注度设计优先遵循以下原则：

- 可解释优先
- 规则优先
- 工程稳定优先
- 不引入复杂学习模型

这样做的原因是，当前项目最重要的是打通链路、建立可靠状态数据和形成可展示结果，而不是过早追求一个看起来“更智能”但不可解释、不可调试的黑盒指标。

## API 边界

前端与后端通过 REST + WebSocket 解耦。

### 当前已实现的 API

当前代码中已经落地的接口包括：

- `GET /health`
- `GET /api/current`
- `GET /api/summary`
- `GET /api/events`
- `WS /ws/analysis`

这些接口当前的职责是：

- `GET /health`：健康检查
- `GET /api/current`：获取最近一次结构化分析结果
- `GET /api/summary`：获取当前内存中的汇总统计
- `GET /api/events`：获取最近事件列表
- `WS /ws/analysis`：通过 WebSocket 返回当前分析结果快照

当前这组接口更适合用于：

- 前后端联调
- Dashboard 基础数据接入
- 单进程内分析结果展示
- V1 阶段验证结构化结果是否完整

### 后续建议的 REST API

在当前基础上，后续可继续扩展以下 REST 接口：

- `POST /api/analyze/file`
- `POST /api/analyze/live/start`
- `POST /api/analyze/live/stop`
- `GET /api/status/current`
- `GET /api/timeline`

职责建议如下：

- `POST /api/analyze/file`：启动离线文件分析任务或提交待分析文件
- `POST /api/analyze/live/start`：启动实时分析
- `POST /api/analyze/live/stop`：停止实时分析
- `GET /api/status/current`：获取当前实时状态快照
- `GET /api/timeline`：获取前端绘制时间线所需的数据

### 后续建议的 WebSocket API

当前实现中 WebSocket 使用的是 `WS /ws/analysis`。如果后续需要进一步收敛命名或拆分实时通道，可考虑演进为更明确的实时接口，例如：

- `WS /ws/live`

其主要职责是：

- 向前端推送实时状态更新
- 推送最新专注度估计
- 推送关键事件
- 推送必要的轻量汇总信息

WebSocket 适合承载实时状态流，REST 适合承载控制请求和历史查询。两者职责明确，有利于前后端解耦。

## 为什么 V1 不引入 Node.js BFF

V1 不建议引入 Node.js BFF，原因如下：

### 1. 当前 AI / 分析逻辑都在 Python

视频输入、检测、行为分析、状态机、统计逻辑天然都在 Python 侧实现。FastAPI 与这些逻辑同处一个运行环境，调用链更短、维护成本更低。

### 2. FastAPI 足以承担当前接口职责

V1 的接口需求主要是：

- 启停分析
- 查询当前状态
- 获取事件和汇总
- 推送实时状态

这些能力 FastAPI 已经完全可以承担，没有必要为此再增加一个中间层。

### 3. 单独增加 Node.js BFF 会增加复杂度

如果引入 Node.js BFF，会带来额外问题：

- 多一个服务进程
- 多一层数据模型映射
- 多一个部署对象
- 多一套接口维护成本
- 额外的前后端与 BFF、BFF 与 Python 之间协议定义

这会让当前体量的项目过早承担不必要的复杂性。

### 4. 当前核心问题不在前端聚合，而在分析链路本身

V1 当前最大的工程问题不是接口聚合，而是：

- 数据模型是否统一
- 行为分析是否稳定
- 状态机是否可解释
- 前后端链路是否打通

在这些核心问题尚未稳定之前，引入 BFF 不会解决主要矛盾，反而会转移注意力。

## V1 实现优先级

V1 建议按四个阶段推进。

### 第一阶段：目录结构重构、统一数据模型、结构化 detector 输出

目标：

- 完成目录结构调整
- 建立 `core` 数据模型
- 把现有检测能力从“渲染导向”改为“结构化结果导向”
- 明确 `FramePacket`、`DetectionResult` 等基础对象

这一阶段的关键是打基础。如果没有统一模型，后续行为层和 Web 层会非常混乱。

### 第二阶段：ROI + scene features、state tracker、event

目标：

- 引入 ROI 机制
- 完成 `scene_features`
- 完成 `state_tracker`
- 建立基础事件模型与 `event_builder`

这一阶段将系统从“能检测人”推进到“能判断状态”。

### 第三阶段：focus estimator、summary、测试

目标：

- 完成 `focus_estimator`
- 完成 `analytics_aggregator`
- 建立会话汇总输出
- 补齐核心模块测试

这一阶段将系统从“能判断状态”推进到“能产出用户真正关心的结果”。

### 第四阶段：FastAPI、WebSocket、React Dashboard

目标：

- 接入 FastAPI
- 接入 WebSocket
- 提供对前端可消费的接口
- 建立 React Dashboard 基础页面

这一阶段将系统从“后端分析原型”推进到“可展示的完整 MVP”。

## 后续演进方向

### V1.5

在 V1 完成基础闭环之后，下一步重点应放在稳定性和结果表达上，而不是扩展系统复杂度。

建议方向：

- 稳定度分析优化
- 离线分析结果页
- 时间线与事件展示优化
- 统计结果解释性增强

### V2

在行为分析链路稳定之后，可以逐步增强感知能力。

建议方向：

- 姿态估计
- 更丰富的行为状态
- 历史分析增强
- 更细粒度的学习 / 工作状态判定

### V3

当性能和系统规模成为明显瓶颈时，再考虑更底层的架构优化。

建议方向：

- C++ 媒体模块
- RTSP / 解码优化
- Python + C++ 混合系统

此阶段应以明确性能瓶颈为前提，而不是预先设计。

## 设计原则总结

Study Focus Analytics 在 V1 阶段应坚持以下设计原则：

- 先做真实、可跑、可展示的 MVP
- 不为未来复杂需求过度设计
- 统一数据模型优先于继续堆功能
- 行为分析层是核心，而不是检测层
- Web 前端负责展示，后端负责分析
- 保持模块边界清晰
- 优先可解释性，而不是“看起来更 AI”

如果用一句话概括 V1 的设计取向，那就是：先把单人场景下“输入、检测、特征、状态、专注度、事件、展示”这条主链路做扎实，再讨论更复杂的能力扩展。
