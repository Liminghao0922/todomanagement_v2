# 完整基础设施架构指南

[English](ARCHITECTURE_GUIDE.md) | [简体中文](ARCHITECTURE_GUIDE-zh_CN.md) | [日本語](ARCHITECTURE_GUIDE-ja_JP.md)

## 系统总览

当前基础设施采用**私有、安全、基于身份**的架构，目标是实现零明文凭据。

![Architecture](../images/01.Architecture.png)

## 核心设计
- 所有工作负载运行在 Azure 私有网络内
- ACR 与 PostgreSQL 使用私有访问与私有 DNS
- 容器应用通过用户分配托管标识（UAI）访问数据库和镜像仓库
- CI/CD 通过 GitHub Actions 完成构建与滚动部署

## 核心组件
- `todomanagement-api`：FastAPI 后端，负责 Todo、项目与身份相关接口
- `todomanagement-web`：Vue 3 前端，通过同源 `/api` 与后端通信
- PostgreSQL Flexible Server：作为生产数据库，使用 Microsoft Entra ID 认证
- Azure Container Registry：存储 API 与 Web 容器镜像
- User Assigned Identity：用于容器应用拉取镜像和访问数据库

## 身份与认证流
- API 容器启动后通过 UAI 获取数据库访问令牌
- Web 容器在构建期注入 Entra 配置，在运行期只需要 `API_PROXY_TARGET`
- GitHub Actions 使用 `AZURE_CREDENTIALS` 登录 Azure，并通过模板工作流部署 Container Apps

## 请求数据流
1. 浏览器访问 Web Container App
2. 前端通过同源 `/api` 调用后端
3. Web Container App 将 `/api` 代理到 internal API Container App
4. API Container App 使用 UAI 获取 PostgreSQL 访问令牌并执行查询
5. 响应通过 HTTPS 返回给浏览器

## 安全模型
- 不在代码或环境中硬编码数据库密码
- 以 Microsoft Entra ID 与令牌认证替代用户名/密码
- 使用最小权限（例如 ACR 的 AcrPull）
- 敏感访问通过 RBAC 控制并可审计

## RBAC 概览
- UAI 需要对 ACR 具有镜像拉取权限
- PostgreSQL 中授予对应 Entra 主体最小化数据库权限
- GitHub Actions 使用具备目标资源组部署权限的 Service Principal

## 建议阅读顺序
1. `README-zh_CN.md`
2. `handson/DEPLOY_GUIDE-zh_CN.md`
3. `infra/README.md`
4. `.github/workflows/*.yml.template`

## 说明
该文档为中文版本摘要。完整细节请参考英文主文档：`docs/ARCHITECTURE_GUIDE.md`。
