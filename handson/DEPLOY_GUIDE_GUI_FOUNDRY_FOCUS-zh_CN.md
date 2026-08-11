# Todo Management v2 实验指南（Foundry Focus，初学者版）

[English](DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS.md) | [简体中文](DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS-zh_CN.md) | [日本語](DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS-ja_JP.md)

此版本聚焦 Foundry 操作。基础设施由讲师在课前准备完成。

预计耗时：60-90 分钟。

## 1. 你需要从讲师处获得

- Todo 应用 URL
- Foundry 项目 URL
- Agent 名称与版本
- 课堂测试账号与登录方式
- 预期输出示例

本版本不要求参与者使用 Cloud Shell。

## 2. 学习目标

- 理解 Agent instructions 如何影响输出。
- 使用 Foundry Tools 操作 Cosmos DB 数据。
- 阅读 trace 与工具调用元数据。
- 通过提示词和指令调优结果质量。

## 3. 操作步骤

### 3.1 登录并确认应用基础功能

1. 打开 Todo 应用 URL。
2. 使用分配账号登录。
3. 确认 `Todos` 与 `Projects` 页面可打开。
4. 打开一个项目并确认图视图可显示。

### 3.2 打开 Foundry Agent Playground

1. 打开讲师提供的 Foundry 项目 URL。
2. 打开指定 Agent。
3. 确认工具已预先挂载：
   - Azure Cosmos DB
   - （可选）Work IQ Calendar

### 3.3 执行 Cosmos 工具调用练习

按顺序发送以下提示词：

1. `List all databases in my Cosmos DB account.`
2. `List containers in database todo-db.`
3. `Find todos that mention MVP or validation.`
4. `Show high-priority tasks for Current Project.`

预期结果：

- Agent 会触发工具调用。
- 返回结果包含来自 Cosmos DB 的数据。

### 3.4 查看 Traces

1. 打开本次会话的 `Traces`。
2. 定位工具调用参数与返回值。
3. 解释为什么调用该工具。
4. 对比返回结果与预期是否一致。

### 3.5 提示词与指令调优

选择一种方式优化并对比效果：

- 增加输出格式约束（长度、结构）
- 要求答案标注工具证据
- 要求输出可执行的优先级建议

重新执行一个查询，对比前后质量。

## 4. 完成标准

- 你能主动触发 Cosmos 工具调用。
- 你能解释至少一条 trace 的完整链路。
- 你能通过提示词改进输出质量。

## 5. 可选挑战

若课堂启用了 Work IQ Calendar：

- 让 Agent 总结近期会议。
- 让 Agent 基于日历约束调整任务优先级。

## 6. 故障处理（参与者视角）

- 登录失败：联系讲师处理账号或租户配置。
- 工具调用失败：先继续做 trace 观察，讲师并行处理后端。
- 输出为空：提高提示词具体度，并检查时间/过滤条件。
