# 架构指南 v3 - Azure Functions + Cosmos DB + Static Web Apps

[English](ARCHITECTURE_GUIDE.md) | [简体中文](ARCHITECTURE_GUIDE-zh_CN.md) | [日本語](ARCHITECTURE_GUIDE-ja_JP.md)

## 系统概览

v3 架构采用**云原生、无服务器、基于身份**的设计，集成以下组件：

- **Azure Functions** - 后端 API 和定时作业
- **Azure Cosmos DB** - NoSQL 容器 + Gremlin 图表
- **Azure Static Web Apps** - Vue 前端
- **Azure OpenAI** - 向量嵌入和聊天模型
- **Azure AI Foundry** - 内置工具（Graph + Cosmos）与自定义工具支持
- **Microsoft Entra ID** - 跨全部服务的身份认证与授权

### 高级架构

```
┌────────────────────────────────────────────────────────────┐
│          Azure 云环境                                      │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  用户浏览器
│    ↓ MSAL Entra ID 认证
│
│  ┌──────────────────────────────────────────────────┐   │
│  │ Azure Static Web Apps (SWA)                      │   │
│  │ - Vue 3 + Vite 前端                             │   │
│  │ - `/api` 代理 → Function App                    │   │
│  └──────────────┬───────────────────────────────────┘   │
│                 ↓
│  ┌──────────────────────────────────────────────────┐   │
│  │ Azure Functions (Python 3.11)                   │   │
│  │ - GET/POST/PATCH/DELETE /todos                 │   │
│  │ - POST /chat (Foundry 代理)                     │   │
│  │ - POST /tools/estimate-hours (自定义)            │   │
│  │ - Timer: 0 0 */6 * * * (日历扫描)              │   │
│  └──────────────┬───────────────────────────────────┘   │
│                 ↓
│  ┌──────────────────────────────────────────────────┐   │
│  │ Azure Cosmos DB                                 │   │
│  │ - NoSQL: todos、owners、projects 容器           │   │
│  │ - Gremlin: todo-graph（关系图谱）              │   │
│  │ - Vector: embedding 字段（向量搜索）           │   │
│  │ - Serverless 计费模式                         │   │
│  └──────────────────────────────────────────────────┘   │
│
│  ┌──────────────────────────────────────────────────┐   │
│  │ Azure OpenAI Service                            │   │
│  │ - gpt-4o-mini（聊天 + 提取）                   │   │
│  │ - text-embedding-3-small（向量）               │   │
│  └──────────────────────────────────────────────────┘   │
│
│  ┌──────────────────────────────────────────────────┐   │
│  │ Azure AI Foundry                                │   │
│  │ - Web UI Agent（gpt-4o-mini 驱动）             │   │
│  │ - 内置: MS Graph + Cosmos 查询工具              │   │
│  │ - 自定义工具: /api/tools/estimate-hours          │   │
│  └──────────────────────────────────────────────────┘   │
│
└────────────────────────────────────────────────────────────┘
```

## 数据流

### 1. SPA → Functions API

```
用户
  ↓ MSAL 认证（Entra ID 登录）
  ↓
Vue 3 SPA 前端
  ├─ GET /api/health
  ├─ GET /api/todos
  ├─ POST /api/todos（创建）
  ├─ PATCH /api/todos/{id}（更新）
  ├─ DELETE /api/todos/{id}（删除）
  ├─ POST /api/chat（Foundry 聊天）
  └─ POST /api/tools/estimate-hours
       ↓
  Azure Functions
       ↓
  Cosmos DB / OpenAI / Graph API
```

### 2. Functions → Cosmos NoSQL

```
接收 POST /api/todos
  ↓
1. 通过 OpenAI 生成向量嵌入
   text-embedding-3-small(title + description)
2. 创建 Todo 文档
   { id, owner_id, title, description, embedding: [...] }
3. Upsert 到 Cosmos NoSQL "todos" 容器
4. 同步到 Gremlin 图表
   - 创建顶点（todo 节点）
   - 创建边（BLOCKED_BY、PRECEDES、SUBTASK_OF、SIMILAR_TO）
```

### 3. 定时任务: 日历扫描

```
Timer: 每 6 小时触发一次
  ↓
1. 查询所有所有者（从 Cosmos 获取）
2. 对于每个所有者：
   - Graph API 认证（client credentials）
   - 调用 calendarView API
   - 抽取会议内容
   - OpenAI 提取行动项
   - 去重后创建 Todo
   - 同步到 Gremlin 图表
```

### 4. Foundry Agent 集成

```
用户：在 Foundry UI 中输入查询
  ↓
Foundry Agent（gpt-4o-mini 驱动）
  ├─ 内置 MS Graph 工具
  │  └─ 日历 API → 获取事件
  ├─ 内置 Cosmos 工具
  │  ├─ SQL 查询 → NoSQL 数据
  │  └─ Gremlin 查询 → 关联 todos
  └─ 自定义工具
     └─ /api/tools/estimate-hours
        → 任务标题描述 → 推荐工时 + 相似历史 todo
  ↓
工具结果链式处理 → 生成自然语言响应
  ↓
在 Foundry UI 显示
```

## Entra ID 与认证

### Web 应用（SPA）

- 平台: SPA（MSAL 浏览器）
- 重定向 URI：`https://[swa].azurestaticapps.net/`
- 范围：`User.Read`、`Calendars.Read`（委托）

### Functions（托管标识）

- 类型: 系统分配
- 用于: Cosmos、OpenAI、Graph API 认证
- 无需密钥（Entra ID 令牌自动获取）

### Graph API（Service Principal）

- 类型：应用注册（client secret）
- 范围：`Calendars.Read`（应用级）
- 日历扫描作业使用

## 安全性

- **零硬编码密钥**：运行时通过 Entra ID/Key Vault 解决
- **Cosmos 分区化**：按 `/owner_id` 隔离数据
- **HTTPS 全链路**：完全加密通信
- **图表表达关系**：边定义 todos 的逻辑关系

Azure 门户路径详见 [DEPLOY_GUIDE_GUI-zh_CN.md](../handson/DEPLOY_GUIDE_GUI-zh_CN.md)，IaC 路径请参见英文版 [DEPLOY_GUIDE.md](../handson/DEPLOY_GUIDE.md)。
