# 讲师准备指南（Foundry Focus，初学者版）

[English](INSTRUCTOR_PREP_GUIDE_FOUNDRY_FOCUS.md) | [简体中文](INSTRUCTOR_PREP_GUIDE_FOUNDRY_FOCUS-zh_CN.md) | [日本語](INSTRUCTOR_PREP_GUIDE_FOUNDRY_FOCUS-ja_JP.md)

[参与者指南](DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS-zh_CN.md)

此版本面向初学者。讲师尽量在课前完成全部基础设施准备，参与者只聚焦 Foundry 与 Cosmos DB 工具调用。

## 1. 设计原则

- 参与者尽量只做 Portal/UI 操作。
- 避免参与者使用 Cloud Shell 与长命令行。
- 共享资源统一由讲师预置。
- 课堂中不把基础设施排障交给参与者。

## 2. 与原版实验的范围差异

- 讲师负责：
  - 资源部署
  - 容器镜像构建与部署
  - RBAC 与标识配置
  - 应用联通与冒烟测试
- 参与者负责：
  - Foundry Agent 交互
  - 通过工具访问 Cosmos DB
  - Prompt/Instructions 调优

## 3. 讲师课前必须完成

- 完成整套环境预部署。
- 验证所有 URL、角色和权限可用。
- 预置 Cosmos DB 示例数据。
- 验证每个参与者账号可进入 Foundry playground。

建议参与者权限基线：

- 若需要最小资源创建：资源组 Owner（或至少 Contributor+）
- 若仍保留应用注册环节：Entra ID 的 Application Developer

如果是严格 Foundry-only 课堂，可不要求参与者创建任何基础设施。

## 4. 部署路径建议

### 方案 A（推荐）：讲师预置共享环境

沿用现有讲师指南中的共享环境模式，参与者只消费已准备资源。

### 方案 B：讲师使用 azd 一键部署

如果希望快速起环境，由讲师课前执行：

```powershell
azd up
```

`azd up` 会依次运行两个可单独执行的阶段：`azd provision` 创建基础设施并配置身份、RBAC、Entra 和 Foundry connection；`azd deploy` 构建 MCP 镜像、更新 Agent、发布 Function 与 Static Web App，并执行健康检查。

命名规则（与当前 Bicep 模板保持一致）：

- `<suffix>` = `uniqueString(resourceGroup().id)`。
- Azure AI Services：`aifoundry-<projectName>-<suffix>`
- Cosmos SQL 账号：`cossql<projectName><suffix>`
- Cosmos Gremlin 账号：`cosgr<projectName><suffix>`
- Storage 账号：`st<projectNameNoDashFirst8><suffix>`（`projectName` 转小写，移除 `-`/`_` 后取前 8 位）
- App Service Plan：`asp-<projectName>-<env>`
- Function App 名称：`func-<projectName>-<env>-<suffix>`（在 preview 中资源类型显示为 `Web App`）
- Static Web App：`swa-<projectName>-<suffix>`
- Container Registry：`acr<projectNameFirst10><shortSuffix>`
- Container App：`mcp-<projectNameFirst12>-<shortSuffix>`
- Container Apps 环境：`cae-<projectNameFirst12>-<shortSuffix>`
- Log Analytics 工作区：`log-<projectNameFirst12>-mcp-<shortSuffix>`

按当前示例环境（`projectName=todomanagement`, `environment=todomangementv2`）进行 `azd provision --preview` 时，通常会看到：

```text
Create : Container App                      : mcp-todomanageme-oit3m2
Create : Container Apps Environment         : cae-todomanageme-oit3m2
Create : Azure AI Services                  : aifoundry-todomanagement-oit3m2mzmum7y
Create : Azure AI Services Model Deployment : gpt-5.4-mini
Create : Azure AI Services Model Deployment : text-embedding-3-small
Create : Foundry project                    : proj-todomanagement
Create : Container Registry                 : acrtodomanageoit3m2
Create : Azure Cosmos DB                    : cosgrtodomanagementoit3m2mzmum7y
Create : Azure Cosmos DB                    : cossqltodomanagementoit3m2mzmum7y
Create : Log Analytics workspace            : log-todomanageme-mcp-oit3m2
Create : Storage account                    : sttodomanaoit3m2mzmum7y
Create : App Service plan                   : asp-todomanagement-todomangementv2
Create : Web App                            : func-todomanagement-todomangementv2-oit3m2mzmum7y
Create : Static Web App                     : swa-todomanagement-oit3m2mzmum7y
```

说明：

- 仅讲师执行，不作为学员步骤。
- 将输出值（URL/ID）整理成课堂发放清单。
- 课前做一次完整验证后冻结环境。

## 5. 课前验收清单

- Todo Web 应用可访问且可登录。
- Function 健康检查返回 healthy。
- Cosmos DB 存在预期样例数据。
- Foundry 项目中的模型已部署完成。
- Agent 可以成功调用 Cosmos 工具。
- 可选工具（如 Work IQ Calendar）已连通并验证。
- 参与者可在不使用 CLI 的前提下完成实验。

## 6. 给参与者的统一信息

- Todo 应用 URL
- Foundry 项目 URL
- Agent 名称与版本
- 推荐测试提问列表
- 预期返回示例

初学者版不要求参与者运行构建/部署命令。

## 7. 建议课堂节奏（60-90 分钟）

1. 10 分钟：架构与目标说明
2. 15 分钟：Foundry 界面导览（模型、工具、trace）
3. 25 分钟：Cosmos 工具调用引导练习
4. 15 分钟：Prompt/Instructions 调优
5. 10 分钟：总结与答疑

## 8. 课堂应急方案

遇到基础设施问题时：

- 讲师切换到预先验证的备用环境。
- 参与者继续进行 Foundry 操作部分。
- 跳过部署与故障排查内容。
