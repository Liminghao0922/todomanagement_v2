# Bicep 模板使用指南 - Todo Management 应用

## 概述

本Bicep模板部署以下Azure资源，所有资源在同一个Virtual Network中：

1. **Virtual Network (VNet)** - 10.0.0.0/16
2. **Azure Database for PostgreSQL Flexible Server** - 支持Entra ID认证
3. **Azure Container Registry (ACR)** - 用于存储容器镜像
4. **Container App Environment** - 运行Container App
5. **Private DNS Zone** - 为PostgreSQL设置私有DNS

## 文件结构

```
infra/
├── main.bicep              # 主模板：创建VNet、PostgreSQL、ACR、Container App Env
├── parameters.json         # 参数文件
├── entra-auth.bicep        # Entra ID认证配置模块
├── container-app.bicep     # Container App部署模块示例
├── deploy.sh              # Linux/macOS部署脚本
├── deploy.ps1             # Windows PowerShell部署脚本
└── README.md              # 本文件
```

## 快速开始

### 前置条件

- Azure CLI 或 Azure PowerShell 已安装
- 有效的Azure订阅
- 对目标订阅拥有足够权限（Owner或Contributor角色）

### 步骤1：修改参数文件

编辑 `parameters.json`，根据需要更改以下参数：

```json
{
  "location": {
    "value": "japaneast"  // 改为您的目标区域
  },
  "environment": {
    "value": "dev"  // 可以是 dev, staging, prod
  },
  "postgresqlAdminPassword": {
    "value": "Change@Me123!"  // 改为强密码
  }
}
```

### 步骤2：使用PowerShell部署（Windows）

```powershell
# 导航到infra目录
cd .\infra

# 运行部署脚本
.\deploy.ps1 -ResourceGroupName "rg-todomanagement-dev" -Location "japaneast"
```

### 步骤3：使用Bash部署（Linux/macOS）

```bash
# 导航到infra目录
cd ./infra

# 运行部署脚本
chmod +x deploy.sh
./deploy.sh
```

### 步骤4：手动使用Azure CLI部署

```bash
# 登录Azure
az login

# 设置订阅
az account set --subscription "<subscription-id>"

# 创建资源组（使用自定义名称）
az group create \
  --name "rg-todomanagement-dev" \
  --location "japaneast"

# 部署Bicep模板
az deployment group create \
  --name "infra-deployment" \
  --resource-group "rg-todomanagement-dev" \
  --template-file "infra/main.bicep" \
  --parameters "infra/parameters.json"
```

## 部署后的资源

部署完成后，您将获得以下资源：

### Virtual Network
- 名称: `vnet-todomanagement-dev`
- 地址范围: 10.0.0.0/16
- 子网:
  - PostgreSQL 子网: 10.0.1.0/24
  - Container App 子网: 10.0.2.0/24

### PostgreSQL Flexible Server
- 自动生成的名称 (例: `postgres-todomanagement-xxxxx`)
- 版本: PostgreSQL 17
- SKU: Standard_B1ms (Burstable)
- 存储: 32GB
- Entra ID认证: 已启用
- 私有DNS: 已配置

### Azure Container Registry
- 自动生成的名称 (例: `acrtodemanagementixxxxx`)
- SKU: Standard
- 位置: 同资源组

### Container App Environment
- 名称: `cae-todomanagement-dev`
- VNet集成: 是（使用Container App子网）
- Log Analytics: 已配置

## 配置PostgreSQL Entra ID认证

### 1. 创建托管身份

对于Container App，需要创建用户分配的托管身份：

```bash
# 创建托管身份
az identity create \
  --resource-group "rg-todomanagement-dev" \
  --name "uai-todomanagement-app"

# 获取身份ID和客户端ID
IDENTITY_ID=$(az identity show \
  --resource-group "rg-todomanagement-dev" \
  --name "uai-todomanagement-app" \
  --query id -o tsv)

IDENTITY_CLIENT_ID=$(az identity show \
  --resource-group "rg-todomanagement-dev" \
  --name "uai-todomanagement-app" \
  --query clientId -o tsv)

echo "Identity ID: $IDENTITY_ID"
echo "Client ID: $IDENTITY_CLIENT_ID"
```

### 2. 在PostgreSQL中创建Entra ID用户

```bash
# 获取PostgreSQL服务器名
POSTGRES_SERVER=$(az postgres flexible-server list \
  --resource-group "rg-todomanagement-dev" \
  --query "[0].name" -o tsv)

# 获取管理员令牌
TOKEN=$(az account get-access-token \
  --resource-type oss-rdbms \
  --query accessToken -o tsv)

# 使用psql连接并创建Entra ID用户
# 您需要在本地安装psql客户端

# 获取PostgreSQL的完全限定域名
POSTGRES_FQDN=$(az postgres flexible-server show \
  --resource-group "rg-todomanagement-dev" \
  --name "$POSTGRES_SERVER" \
  --query fullyQualifiedDomainName -o tsv)

# 连接PostgreSQL（使用管理员账户）
psql -h "$POSTGRES_FQDN" \
  -U postgres \
  -d postgres \
  -c "CREATE ROLE \"<managed-identity-name>\" WITH LOGIN IN ROLE azure_ad_user;"
```

### 3. 授予数据库权限

```sql
-- 以postgres管理员身份连接

-- 创建并分配数据库所有者角色
GRANT ALL PRIVILEGES ON DATABASE tododb TO "managed-identity-name";

-- 或仅授予特定权限
GRANT CONNECT ON DATABASE tododb TO "managed-identity-name";
GRANT USAGE ON SCHEMA public TO "managed-identity-name";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "managed-identity-name";
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO "managed-identity-name";
```

## Container App配置

### 使用container-app.bicep模块

```bicep
module containerApp 'container-app.bicep' = {
  name: 'containerApp-deployment'
  params: {
    containerAppName: 'ca-todomanagement-api'
    containerAppEnvironmentId: containerAppEnvId
    containerRegistryLoginServer: acrLoginServer
    containerImage: '${acrLoginServer}/todomanagement/api:latest'
    postgresqlHostname: postgresqlHostname
    postgresqlDatabaseName: 'tododb'
    containerAppUserAssignedIdentityId: managedIdentityId
    containerAppUserAssignedIdentityClientId: managedIdentityClientId
  }
}
```

### Container App环境变量

Container App将自动获得以下环境变量：

```
DATABASE_HOST=postgres-todomanagement-xxxxx.postgres.database.azure.com
DATABASE_NAME=tododb
DATABASE_PORT=5432
AZURE_CLIENT_ID=<managed-identity-client-id>
MANAGED_IDENTITY_ENABLED=true
```

### 应用中的PostgreSQL连接

在您的应用代码中（Python示例）：

```python
import os
import psycopg2
from azure.identity import DefaultAzureCredential

# 获取Entra ID令牌
credential = DefaultAzureCredential()
token = credential.get_token("https://ossrdbms-aad.database.windows.net").token

# 连接PostgreSQL
conn = psycopg2.connect(
    host=os.getenv("DATABASE_HOST"),
    port=os.getenv("DATABASE_PORT"),
    user=os.getenv("AZURE_CLIENT_ID"),
    password=token,
    database=os.getenv("DATABASE_NAME"),
    sslmode="require"
)
```

## 网络配置

### 子网详情

1. **PostgreSQL子网** (10.0.1.0/24)
   - 委托给: Microsoft.DBforPostgreSQL/flexibleServers
   - 用途: 托管PostgreSQL Flexible Server

2. **Container App子网** (10.0.2.0/24)
   - 用途: 托管Container App Environment

### 私有DNS

- 私有DNS区域: `privatelink.postgres.database.azure.com`
- 已链接到VNet
- Container App可以通过私有DNS解析PostgreSQL服务器

## 成本估计

| 资源 | SKU | 估计成本 |
|------|-----|--------|
| PostgreSQL | Standard_B1ms | ~¥40/月 |
| Container Registry | Standard | ~¥200/月 |
| Container App Env | 共享基础设施 | ~¥200/月 |
| VNet | 标准 | ~¥40/月 |
| 私有DNS | 标准 | ~¥5/月 |

总计约: ~¥500/月（实际成本可能有所不同）

## 故障排查

### PostgreSQL连接问题

```bash
# 检查PostgreSQL服务器状态
az postgres flexible-server show \
  --resource-group "rg-todomanagement-dev" \
  --name "postgres-todomanagement-xxxxx"

# 检查防火墙规则
az postgres flexible-server firewall-rule list \
  --resource-group "rg-todomanagement-dev" \
  --server-name "postgres-todomanagement-xxxxx"
```

### Container App无法连接PostgreSQL

1. 检查子网配置是否正确
2. 确认安全组/NSG规则允许从Container App子网到PostgreSQL子网的连接
3. 验证Entra ID用户是否正确创建在PostgreSQL中
4. 查看Container App日志：

```bash
az containerapp logs show \
  --resource-group "rg-todomanagement-dev" \
  --name "ca-todomanagement-api"
```

## 清理资源

要删除所有创建的资源：

```bash
az group delete \
  --name "rg-todomanagement-dev" \
  --yes --no-wait
```

## 参考资源

- [Azure Bicep文档](https://learn.microsoft.com/zh-cn/azure/azure-resource-manager/bicep/)
- [PostgreSQL Flexible Server文档](https://learn.microsoft.com/zh-cn/azure/postgresql/flexible-server/)
- [Container Apps文档](https://learn.microsoft.com/zh-cn/azure/container-apps/)
- [Entra ID认证 - PostgreSQL](https://learn.microsoft.com/zh-cn/azure/postgresql/flexible-server/how-to-configure-sign-in-azure-ad-authentication)
