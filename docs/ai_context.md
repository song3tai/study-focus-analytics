# Study Focus Analytics AI Context

## 1. 项目概述

Study Focus Analytics 是一个面向学生、自习者和远程办公者的学习 / 工作状态分析系统。AI 编码助手必须将本项目理解为“单人场景行为分析工程”，而不是通用视频处理或目标检测演示项目。

系统输入包括：

- 摄像头视频
- RTSP 实时流
- 本地视频文件

系统输出包括：

- 在岗 / 离岗状态
- 学习 / 工作时长
- 离岗时长
- 专注度估计
- 事件流
- 汇总统计结果

最终后端通过 Web API 和 WebSocket 向 React 前端提供结构化数据。

## 2. 当前阶段

当前项目处于 V1 基础版本设计与重构阶段。

当前重点不是继续叠加通用检测功能，也不是继续扩展旧版 demo 的图像处理模式，而是完成以下工作：

1. 重构项目结构
2. 引入统一数据模型
3. 将检测结果升级为结构化结果
4. 增加行为分析层
5. 增加状态机与事件模型
6. 为 FastAPI + React 架构打基础

AI 助手在实现任何功能前，都应先判断该功能是否服务于上述主线。如果不能直接服务这条主线，应默认优先级较低。

## 3. 项目定位变化

项目定位已经明确变化：

- 旧定位：视频处理与 YOLO 检测原型
- 新定位：学习 / 工作状态分析系统

这不是文字层面的改名，而是开发目标的切换。AI 助手必须始终按照新定位进行开发，不能继续把项目理解为通用 `video_frame_processor` demo，也不能把主要工作放在继续扩展旧的检测演示能力上。

以下行为应避免：

- 优先增加新的图像滤镜模式
- 围绕“显示检测框”继续扩展主流程
- 把输出理解为渲染图像而不是结构化分析结果
- 把 `main.py` 持续扩展成总控脚本

后续所有设计和代码修改，都必须围绕“行为分析链路”展开。

## 4. V1 功能边界

### V1 要实现

- 单人场景
- 单摄像头 / 单 RTSP / 单视频输入
- 固定 ROI（学习 / 工作区域）
- person 检测
- 场景特征提取
- `unknown / present / away / studying` 状态机
- 时长统计
- 可解释 focus score
- 事件流
- FastAPI 接口
- React Dashboard 数据支持

### V1 不实现

- 多人跟踪
- 人脸识别
- 身份识别
- 音频语义分析
- 黑盒注意力模型
- 数据库系统
- 用户系统
- 多摄像头平台
- 复杂分布式架构
- Node.js BFF

AI 助手必须把这些“非目标”当作真实约束，而不是暂时未做的待办列表。除非用户明确改变方向，否则不要主动往这些方向扩展。

## 5. 当前推荐目录结构

推荐目录结构如下：

```text
src/
- main.py
- config.py
- utils.py
- core/
  - enums.py
  - models.py
- io/
  - video_reader.py
  - video_writer.py
- inference/
  - ai_detector.py
- behavior/
  - scene_features.py
  - state_tracker.py
  - focus_estimator.py
  - event_builder.py
  - analytics_aggregator.py
- pipeline/
  - analysis_pipeline.py
- web/
  - api.py
  - schemas.py
  - websocket_manager.py
```

如果当前仓库中的实际文件结构尚未完全迁移到这个形态，AI 助手应优先朝这个结构演进，而不是继续加深旧结构耦合。

## 6. 关键模块职责

### core

`core` 负责统一数据模型和枚举定义。它是整个项目的公共语言层，所有关键阶段都应尽量通过这里定义的对象和枚举进行交互。

### io

`io` 负责摄像头、RTSP、视频文件输入，以及可选的视频输出。它只处理输入输出问题，不承担行为分析逻辑。

### inference

`inference` 负责 YOLOv8 检测。V1 中它的职责是对单帧生成结构化 `DetectionResult`，而不是承担状态判断、事件生成或统计。

### behavior

`behavior` 是项目核心模块。这里负责把“检测结果”转换成“行为语义结果”。重点包括：

- 场景特征提取
- 状态机
- 专注度估计
- 事件生成
- 汇总统计

如果 AI 助手在设计新能力时无法明确它应落在 `behavior` 的哪个位置，通常说明设计边界还没有想清楚。不要把行为层逻辑塞进 `main.py`、detector 或 API 层。

### pipeline

`pipeline` 负责逐帧编排，把输入、检测、行为分析、结果聚合连接成一条稳定管线。它是流程编排层，不是业务规则定义层。

### web

`web` 负责 API 和 WebSocket 接口层，对 React 前端暴露结构化数据。它不负责分析逻辑，也不应该复制行为状态机。

## 7. 统一数据流

开发时必须遵循以下统一数据流：

`FramePacket`
→ `DetectionResult`
→ `FrameFeatures`
→ `BehaviorStateSnapshot`
→ `FocusEstimate`
→ `BehaviorEvent(optional)`
→ `ProcessResult`

这是项目从检测 demo 升级为分析系统的关键路径。

必须遵守以下约束：

- 不要跳过中间层
- 不要把逻辑直接塞进 detector
- 不要把逻辑直接塞进 `main.py`
- 不要把状态统计逻辑散落在多个模块中
- 不要用“先画框再人工读取显示状态”的方式替代结构化结果

如果某项新功能无法自然接入这条数据流，应优先调整设计，而不是临时绕过去。

## 8. 推荐核心数据对象

建议在 `core/models.py` 中定义以下核心对象：

- `FramePacket`
- `Detection`
- `DetectionResult`
- `ROI`
- `FrameFeatures`
- `BehaviorStateSnapshot`
- `FocusEstimate`
- `BehaviorEvent`
- `AnalysisSummary`
- `ProcessResult`

建议在 `core/enums.py` 中定义以下枚举：

- `BehaviorState`
- `FocusLevel`
- `EventType`
- `SourceType`

明确要求：

- 不要在不同模块里重复定义这些结构
- 不要大量使用未约束字典替代核心数据模型
- 不要让 API 层、行为层、推理层各自维护一套字段命名
- 能进入核心链路的数据，优先使用统一模型对象承载

如果必须在某个边界使用字典，应保证它只是序列化结果，而不是内部主数据形态。

## 9. 行为状态机规则

V1 推荐状态包括：

- `unknown`
- `present`
- `away`
- `studying`

基本规则如下：

- 检测到人进入 ROI 且持续稳定 → `present`
- `present` 持续足够久且稳定度高 → `studying`
- 连续一段时间未检测到人 → `away`
- 启动早期信息不足 → `unknown`

状态机必须具备去抖逻辑，不能根据单帧检测结果立即切换。

推荐默认阈值：

- `present_confirm_seconds = 1.0`
- `away_confirm_seconds = 2.0`
- `studying_confirm_seconds = 10.0`

AI 助手在实现状态机时应注意：

- 去抖优先于响应速度
- 短时漏检不能直接判定为 `away`
- `studying` 必须建立在更稳定、更持续的条件上
- `unknown` 应保留为信息不足时的合法状态，而不是简单默认值

## 10. 专注度设计原则

V1 的专注度不是黑盒 AI 模型，而是基于规则的可解释估计。

可使用的特征包括：

- 最近窗口内在岗比例
- 最近窗口内离岗次数
- 位置 / 姿态稳定度
- ROI 对齐程度
- 动作波动程度
- `studying` 连续持续时间

输出应包括：

- `focus_score`
- `focus_level`
- `reasons`

实现时优先保证以下属性：

- 可解释
- 简单
- 稳定
- 可调参

不要在 V1 中引入复杂学习模型，也不要把专注度定义成无法解释的神秘指标。专注度模块的目标是提供一个工程上可用、可以逐步改进的估计值。

## 11. 开发规则

开发时必须遵循以下规则：

1. 保持 `main.py` 轻量
2. 检测层与行为层分离
3. 所有关键阶段都应输出结构化结果
4. 保持 OpenCV / BGR 图像兼容性
5. 新能力优先通过新增模块实现
6. 前端与后端通过接口解耦，不用 Jinja 做主展示层
7. 当前 Web 后端就是 Python FastAPI 分析服务
8. 避免过度设计，不要引入微服务、消息队列、数据库、大型配置系统

额外约束：

- 不要把行为逻辑塞进 API 层
- 不要把状态汇总逻辑塞进 detector
- 不要为未来可能的复杂架构提前抽象出过多层次
- 优先写清楚单机单进程内的模块边界

## 12. 当前最优先实现顺序

当前推荐优先级顺序如下：

- 第一优先级：`core/models.py`、`core/enums.py`、detector 结构化输出
- 第二优先级：`scene_features.py`、`state_tracker.py`
- 第三优先级：`focus_estimator.py`、`event_builder.py`、`analytics_aggregator.py`
- 第四优先级：`analysis_pipeline.py`、`ProcessResult` 串联
- 第五优先级：FastAPI、WebSocket、React 接口支持

AI 助手在推进任务时，应优先帮助项目形成“统一结构化链路”，而不是先做展示层细节或次要功能。

## 当前第一批待创建文件

第一批建议优先创建的文件如下：

- `src/core/models.py`
- `src/core/enums.py`
- `src/behavior/scene_features.py`
- `src/behavior/state_tracker.py`

这些文件构成 V1 的最小核心能力。`core` 层负责统一数据语言，`scene_features` 和 `state_tracker` 负责把检测结果转换成可用的行为状态基础。应优先实现这些模块，再继续扩展 `pipeline` 和 `web` 层。

## 13. 测试建议

建议优先新增以下测试：

- `scene_features` 单元测试
- `state_tracker` 状态切换测试
- `focus_estimator` 规则测试
- `event_builder` 事件生成测试
- `pipeline` 集成测试

测试策略说明：

- 不要求一开始就做复杂 E2E
- 但关键规则必须可验证
- 重点测试状态切换边界、阈值逻辑、事件触发和汇总统计
- 行为层测试优先级高于展示层测试

## 14. 前后端边界

前后端边界必须保持清晰：

- Python + FastAPI：分析后端
- React：Web 前端

前端通过 REST / WebSocket 获取：

- 当前状态
- 当前专注度
- 最近事件
- 汇总数据
- 时间线数据

明确要求：

- 后端不负责复杂前端渲染
- 前端不负责分析逻辑
- 状态机、专注度、事件生成和统计都属于后端
- 前端负责可视化和交互，不重复实现后端规则

## 15. 长期演进方向

后续可考虑的方向包括：

- 姿态估计
- 更丰富的行为状态
- 更好的离线分析页
- C++ 媒体模块
- Python + C++ 混合架构

但必须强调：

- V1 阶段不要提前为了这些能力过度重构
- 不要为了未来假想需求破坏当前结构清晰性
- 当前最重要的是把单人场景分析链路做完整

## 16. 文档职责边界

AI 助手必须理解三份文档的职责边界：

- `README.md`：给使用者 / GitHub 访客看
- `docs/design.md`：给开发者看
- `docs/ai_context.md`：给 AI 助手看

不要把 `ai_context.md` 写成 README，也不要把它写成泛泛而谈的架构介绍。它的目标是帮助 AI 助手快速对齐背景、边界、优先级和开发规则。

## 17. 核心原则总结

AI 助手在本项目中的工作必须始终围绕以下原则展开：

- 明确行为分析项目定位
- 建立统一数据模型
- 打通状态机与统计链路
- 为 Web 展示提供结构化结果
- AI 助手必须始终围绕这个目标工作

如果出现方向冲突，优先遵循以下判断顺序：

1. 是否服务于“学习 / 工作状态分析系统”定位
2. 是否强化统一数据模型和结构化链路
3. 是否有助于行为状态机、事件和统计结果
4. 是否有助于 FastAPI / WebSocket / React 展示链路

凡是不直接支撑这条主线的实现，都应谨慎推进。

## 文档职责约束（重要）

修改文档时必须保持三份文档的职责边界清晰：

- `README.md`：面向用户和 GitHub 访客，用于项目介绍
- `docs/design.md`：面向开发者，用于说明架构设计
- `docs/ai_context.md`：面向 AI 编码助手，用于说明开发约束与优先级

必须遵守以下规则：

- 不要把 `README.md` 写成设计文档
- 不要把 `docs/ai_context.md` 写成 README
- 修改文档时必须保持职责边界清晰
