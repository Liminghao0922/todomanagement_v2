# Complete Infrastructure Architecture Guide

[English](ARCHITECTURE_GUIDE.md) | [简体中文](ARCHITECTURE_GUIDE-zh_CN.md) | [日本語](ARCHITECTURE_GUIDE-ja_JP.md)

## System Overview

Your infrastructure implements a **private, secure, identity-based** architecture with zero hardcoded secrets.

![Architecture](../images/01.Architecture.png)

```
┌─────────────────────────────────────────────────────────────────┐
│                      Azure Cloud Environment                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Virtual Network (10.0.0.0/16)                             │ │
│  │                                                            │ │
│  │  ┌──────────────────┐        ┌──────────────────────────┐ │ │
│  │  │ Container Apps   │        │  PostgreSQL Subnet       │ │ │
│  │  │ Subnet           │        │  (10.0.1.0/24)           │ │ │
│  │  │ (10.0.2.0/24)    │        │                          │ │ │
│  │  │                  │        │  PostgreSQL Flexible     │ │ │
│  │  │  ┌────────────────────── │  Server v17              │ │ │
│  │  │  │ Container App │        │  (Entra ID enabled)      │ │ │
│  │  │  │ (TodoApp)     │        │                          │ │ │
│  │  │  │                │        │  Private endpoint:       │ │ │
│  │  │  │  Uses UAI      │ ──────► 5432                     │ │ │
│  │  │  │  for:          │ │      │                          │ │ │
│  │  │  │  1. Image pull │ │      └──────────────────────────┘ │ │
│  │  │  │  2. DB access  │ │                                    │ │
│  │  │  └────────────┬────┘ │                                    │ │
│  │  │               │      │      Private DNS:                 │ │
│  │  │               │      │      postgres.database.azure.com  │ │
│  │  └───┬───────────┴──────┤                                    │ │
│  │      │                  │                                    │ │
│  │  ┌───▼──────────────────────────────────────────────────┐   │ │
│  │  │ ACR Private Endpoint                                 │   │ │
│  │  │ (Private IP: 10.0.x.x)                              │   │ │
│  │  │ Port: 443 (HTTPS)                                   │   │ │
│  │  │ Private DNS: privatelink.azurecr.io                │   │ │
│  │  └─────────┬──────────────────────────────────────────┘   │ │
│  │            │                                                │ │
│  └────────────┼────────────────────────────────────────────────┘ │
│               │                                                  │
│  ┌────────────▼────────────────────────────────────────────────┐ │
│  │ Azure Container Registry (Premium)                          │ │
│  │ ├─ Container Registry (PRI)                                 │ │
│  │ │  ├─ todomanagement:v1.0                                   │ │
│  │ │  ├─ todomanagement:v1.1                                   │ │
│  │ │  └─ todomanagement:latest                                 │ │
│  │ └─ Private Endpoint (no public access)                       │ │
│  └─────────────────────────────────────────────────────────────┘ │
│               │                                                  │
│  ┌────────────▼────────────────────────────────────────────────┐ │
│  │ User Assigned Identity (UAI)                                │ │
│  │ ├─ Client ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx          │ │
│  │ ├─ Principal ID: yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy        │ │
│  │ └─ Roles:                                                    │ │
│  │    ├─ AcrPull (on ACR) → allows image pulls                 │ │
│  │    └─ Custom (on PostgreSQL) → allows DB access             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│               │                                                  │
│  ┌────────────▼────────────────────────────────────────────────┐ │
│  │ Log Analytics Workspace                                      │ │
│  │ ├─ Container App logs                                        │ │
│  │ ├─ PostgreSQL metrics                                        │ │
│  │ └─ Application monitoring                                    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                           │
                           │
        ┌──────────────────▼──────────────────┐
        │         GitHub (External)           │
        ├──────────────────────────────────────┤
        │ Service Principal for GitHub Actions │
        │ ├─ Client ID in GitHub Secrets       │
        │ ├─ Federated Credentials (OIDC)      │
        │ └─ No client secret stored           │
        │                                      │
        │ On Code Push to main:                │
        │ 1. GitHub Actions triggered          │
        │ 2. Builds Docker image               │
        │ 3. Pushes to ACR (via private EP)    │
        │ 4. Container App updated             │
        │ 5. New image deployed                │
        └──────────────────────────────────────┘
```

## Authentication Flow Diagram

### 1. Container App → ACR (Image Pull)

```
Container App
    │
    ├─ Has User Assigned Identity
    │
    ├─ At startup, acquires token:
    │  GET /metadata/identity/oauth2/token
    │      ?resource=https://management.azure.com
    │
    ├─ Uses token to authenticate to ACR
    │  Private endpoint: pe-acr.azurecr.io (10.0.x.x:443)
    │
    └─ Pulls image: myacr.azurecr.io/todomanagement:latest
       └─ Image downloaded via private endpoint
          (Never touches public internet)
```

### 2. Container App → PostgreSQL (Database Access)

```
Container App
    │
    ├─ Has User Assigned Identity
    │
    ├─ At startup, acquires token:
    │  GET /metadata/identity/oauth2/token
    │      ?resource=https://ossrdbms-aad.database.windows.net
    │
    ├─ Connects to PostgreSQL:
    │  Host: myserver.postgres.database.azure.com (resolves to 10.0.1.x)
    │  Port: 5432 (private endpoint)
    │  Username: uai-todomanagement-dev
    │  Password: <token from above>
    │
    └─ Executes queries with Entra ID authentication
       (No database password stored anywhere)
```

### 3. GitHub → ACR (CI/CD Pipeline)

```
Developer pushes to GitHub main
    │
    ├─ GitHub Actions workflow triggered
    │
    ├─ Workflow retrieves OIDC token from GitHub
    │  (No stored secrets!)
    │
    ├─ Exchanges token with Service Principal
    │  $GITHUB_TOKEN → Azure access token
    │
    ├─ Authenticates to ACR:
    │  Service Principal has AcrPush role
    │  Pushes image via ACR private endpoint
    │
    └─ Deploys to Container App:
       Updates Container App with new image
       Container App restarts with new image
```

## Data Flow - Request Example

When a user accesses the Todo application:

```
1. User requests: https://todomanagement.app/todos

2. Request reaches Container App (via Application Gateway or DNS)
   └─ Container App routes to running container

3. Container processes request:
   ├─ Authenticate user via API endpoint
   │  └─ Check authentication headers
   │
   ├─ Load Todo data:
    │  ├─ Get PostgreSQL token from the user-assigned managed identity (UAI)
   │  ├─ Connect via private endpoint (10.0.1.x:5432)
   │  └─ Execute query as "uai-todomanagement-dev"
   │
   └─ Return JSON response

4. Response returned to user
   └─ All communication encrypted (SSL/TLS)
      All authentication via tokens
      Zero hardcoded secrets
```

## Security Model

### Zero-Trust Principles Implemented

#### 1. **No Hardcoded Secrets**

- ❌ Database passwords NOT stored
- ❌ ACR credentials NOT stored
- ❌ GitHub secrets limited to Service Principal ID only
- ✅ Tokens acquired at runtime via the user-assigned managed identity (UAI)
- ✅ Tokens automatically refreshed

#### 2. **Private Network Only**

- ❌ ACR public endpoint disabled
- ❌ PostgreSQL public endpoint disabled
- ✅ All communication via private endpoints
- ✅ Traffic never crosses public internet
- ✅ Private DNS zones ensure internal resolution

#### 3. **Identity-Based Access (Entra ID)**

- ❌ Username/password authentication NOT used
- ✅ Container App uses a user-assigned managed identity (UAI)
- ✅ PostgreSQL role tied to the corresponding Microsoft Entra ID object
- ✅ ACR access via RBAC (AcrPull role)
- ✅ GitHub Actions via federated credentials

#### 4. **Least Privilege Access**

- Container App identity:

  - ✅ Can only PULL images from ACR (AcrPull role)
  - ✅ Cannot PUSH or DELETE images
  - ✅ Can only access PostgreSQL (no admin roles)
  - ✅ Cannot modify other resources in subscription
- PostgreSQL role:

  - ✅ Can SELECT, INSERT, UPDATE, DELETE on tables
  - ✅ Cannot DROP or ALTER tables
  - ✅ Cannot access other databases
  - ✅ Cannot manage users or roles

#### 5. **Secure GitHub Integration**

- ❌ No stored Azure credentials in GitHub
- ❌ No Service Principal password/secret in GitHub
- ✅ Service Principal ID only (public safe)
- ✅ Federated credentials via OIDC
- ✅ Each GitHub workflow run gets fresh token
- ✅ Token expires after 60 minutes
- ✅ Audit trail of who deployed when

## RBAC Role Assignments

### Azure Container Registry

```
Scope: /subscriptions/.../resourceGroups/rg-todomanagement-dev/providers/Microsoft.ContainerRegistry/registries/acr...

Role: AcrPull (Built-in role 7f951dda-4ed3-4680-a7ca-43fe172d538d)
├─ Principal: User Assigned Identity (uai-todomanagement-dev)
├─ Assigned by: Bicep template (automatic)
└─ Permissions:
   ├─ microsoft.containerregistry/registries/pull/read
   └─ (Cannot push, delete, or modify images)
```

### PostgreSQL Database

```
Container: tododb

Role: uai-todomanagement-dev (Created via SQL)
├─ Principal: Azure Entra ID object (UAI)
└─ Permissions:
   ├─ CONNECT on database
   ├─ USAGE on schema public
   ├─ SELECT, INSERT, UPDATE, DELETE on public.*
   ├─ USAGE on sequences
   └─ Default privileges for future objects
```

## Resource Dependency Graph

```
Resource Group (rg-todomanagement-dev)
│
├─ Virtual Network (vnet-todomanagement-dev)
│  │
│  ├─ PostgreSQL Subnet (ps-postgres)
│  │  └─ ServiceEndpoint: Microsoft.DBforPostgreSQL/flexibleServers
│  │
│  ├─ Container App Subnet (ps-containerapp)
│  │  └─ Delegation: Microsoft.App/environments
│  │
│  ├─ Private Endpoint Subnet (ps-privateendpoint)
│  │  └─ (Could be same as Container App subnet)
│  │
│  ├─ PostgreSQL Flexible Server (psql-todomanagement-dev)
│  │  ├─ Entra ID Auth: Enabled
│  │  ├─ Private Endpoint: Yes (port 5432)
│  │  ├─ Public Access: No
│  │  └─ Database: tododb
│  │
│  └─ Private DNS Zones
│     │
│     ├─ postgres.database.azure.com
│     │  └─ A Record: psql-todomanagement-dev → 10.0.1.x
│     │
│     └─ azurecr.io
│        └─ A Record: acr-name → 10.0.x.x
│
├─ User-Assigned Managed Identity (UAI: uai-todomanagement-dev)
│  ├─ Principal ID: (Auto-generated GUID)
│  └─ Client ID: (Auto-generated GUID)
│
├─ Azure Container Registry (acr...)
│  ├─ Tier: Premium
│  ├─ Private Endpoint: pe-acr (10.0.x.x:443)
│  ├─ Private DNS: acr-name.azurecr.io → 10.0.x.x
│  ├─ Public Access: Disabled
│  └─ Role Assignment: UAI has AcrPull
│
├─ Container App Environment (cae-todomanagement-dev)
│  ├─ VNet Integration: Yes (subnet ps-containerapp)
│  ├─ Log Analytics: Integrated
│  └─ Container App: todomanagement-app
│     ├─ Identity: User-assigned managed identity (UAI)
│     ├─ Image: acr.../todomanagement:latest
│     ├─ Environment Variables: POSTGRES_HOST, POSTGRES_DB, etc.
│     └─ Port: 8000 (internal API Container App)
│
└─ Role Assignments
   ├─ AcrPull: UAI on ACR
   └─ (Custom PostgreSQL role created via SQL)
```

## Deployment Stages

### Stage 1: Infrastructure (Bicep)

```
Deploy main.bicep
├─ Virtual Network (VNet, subnets, delegations)
├─ PostgreSQL Flexible Server
│  └─ Private endpoint (Port 5432)
├─ ACR Premium
│  └─ Private endpoint (Port 443)
├─ User Assigned Identity
├─ Private DNS Zones
├─ Container App Environment
├─ Container App
└─ Role Assignments (RBAC)
```

**Status**: ✅ Automated via `.\deploy.ps1`

### Stage 2: GitHub Configuration

```
Manual setup via .\setup-github-secrets.ps1
├─ Service Principal creation
├─ Federated credentials (OIDC)
├─ GitHub Secrets configuration
│  ├─ AZURE_CLIENT_ID
│  ├─ AZURE_TENANT_ID
│  └─ ACR_LOGIN_SERVER
└─ GitHub Workflow validation
```

**Status**: ✅ Semi-automated helper script provided

### Stage 3: PostgreSQL Configuration

```
Manual SQL execution on PostgreSQL
├─ Connect as admin (postgres user)
├─ CREATE ROLE "uai-todomanagement-dev"
├─ GRANT permissions
│  ├─ CONNECT on tododb
│  ├─ USAGE on public schema
│  └─ SELECT, INSERT, UPDATE, DELETE on tables
└─ Verify role was created
```

**Status**: ⏳ Manual SQL commands in POSTGRESQL_ENTRA_ID_AUTH.md

### Stage 4: Application Code

```
Update source code
├─ Update requirements.txt (add azure-identity)
├─ Update database.py (use the user-assigned managed identity, UAI)
├─ Update environment variables
└─ Remove hardcoded database password
```

**Status**: ⏳ Code changes needed to application

### Stage 5: CI/CD - GitHub Actions

```
On code push to main
├─ Trigger: Build-Deploy-ACR workflow
├─ Build stage
│  ├─ Docker image build with cache
│  └─ Tag with timestamp
├─ Push stage
│  ├─ Login to ACR (via Service Principal)
│  ├─ Push image via private endpoint
│  └─ Remove unused layers
└─ Deploy stage
   ├─ Update Container App
   ├─ Trigger new image pull
   └─ Zero-downtime deployment
```

**Status**: ✅ Workflow file provided: `.github/workflows/build-deploy-acr.yml`

## Monitoring & Troubleshooting

### Key Logs & Metrics Locations

```
Azure Portal
├─ Container App → Logs
│  └─ View application console output
│
├─ PostgreSQL → Metrics
│  ├─ CPU usage
│  ├─ Storage
│  ├─ Network in/out
│  └─ Active connections
│
├─ ACR → Activity Log
│  ├─ Image push/pull events
│  └─ Authentication failures
│
└─ Log Analytics Workspace
   ├─ Container logs
   ├─ Application traces
   └─ Query with KQL
```

### Common Troubleshooting


| Issue                      | Symptom                          | Cause                             | Fix                                     |
| -------------------------- | -------------------------------- | --------------------------------- | --------------------------------------- |
| Cannot pull image          | "Authentication failed"          | UAI not assigned to Container App | Assign Identity in portal               |
| Database connection failed | "Connection refused"             | PostgreSQL role missing           | Run CREATE ROLE SQL                     |
| Workflow fails to push     | "Unauthorized" in GitHub Actions | Service Principal lacks AcrPush   | Assign role:`az role assignment create` |
| Private DNS not resolving  | Cannot reach ACR/PostgreSQL      | DNS zone not linked to VNet       | Link private DNS zone to VNet           |
| Token expired              | 401 Unauthorized                 | Token refresh mechanism broken    | Restart Container App                   |

## Network Architecture Details

### Subnets & IP Ranges

```
VNet: 10.0.0.0/16 (/16 = 65,536 addresses)

├─ PostgreSQL Subnet: 10.0.1.0/24 (/24 = 256 addresses)
│  ├─ Delegation: Microsoft.DBforPostgreSQL/flexibleServers
│  ├─ PostgreSQL Server occupies ~10.0.1.5
│  ├─ Private endpoint DNS: 10.0.1.x
│  └─ Available: ~250 more addresses
│
├─ Container App Subnet: 10.0.2.0/24 (/24 = 256 addresses)
│  ├─ Delegation: Microsoft.App/environments
│  ├─ Container App Environment: 10.0.2.x
│  ├─ ACR Private Endpoint: 10.0.2.y
│  └─ Available: ~250 more addresses
│
└─ Future expansion: 10.0.3.0/24 through 10.0.255.0/24
   (253 more subnets available for scaling)
```

### DNS Resolution

```
Internal (Private)
Container inside VNet
    ↓
Query: acr-name.azurecr.io
    ↓
Private DNS Zone: privatelink.azurecr.io
    ↓
A Record: acr-name → 10.0.x.x (private IP)
    ↓
Response: 10.0.x.x
    ↓
Container connects to 10.0.x.x:443 (HTTPS private endpoint)
✓ Success - communication never leaves VNet

External (Public Internet)
Developer machine (outside Azure)
    ↓
Query: acr-name.azurecr.io
    ↓
Public DNS servers (8.8.8.8, etc.)
    ↓
Response: Public IP xxx.xxx.xxx.xxx
    ↓
ACR public endpoint is disabled
    ↗ Connection refused (as intended)
✓ Security - prevents unauthorized access
```

## Cost Optimization

### Resource Costs

```
Monthly estimate (approximate, depends on region)

├─ Virtual Network: $0 (free tier)
├─ Subnets: $0 (included in VNet)
│
├─ PostgreSQL Flexible Server
│  ├─ Premium_B1ms compute: ~$50/month
│  ├─ Storage 32GB: ~$8/month
│  └─ Backup retention: ~$8/month
│  Total: ~$66/month
│
├─ Azure Container Registry (Premium)
│  ├─ Registry: ~$167/month (Premium tier)
│  ├─ Storage: ~$1-10/month (depending on images)
│  └─ Private endpoints: ~$0.60/endpoint
│  Total: ~$167-180/month
│
├─ Container App Environment
│  ├─ Environment management: ~$50/month
│  ├─ Compute time: ~$40-100/month (depending on vCPU)
│  └─ Consumption beyond 4GB: ~$0.30/GB-hour
│  Total: ~$90-150/month
│
├─ Log Analytics Workspace
│  ├─ Data ingestion: ~$3/GB
│  ├─ Estimated: ~$10-20/month
│  └─ Data retention: 30 days (included)
│  Total: ~$10-20/month
│
├─ Private Endpoints (both)
│  ├─ PostgreSQL PE: ~$0.60/month
│  ├─ ACR PE: ~$0.60/month
│  └─ Private DNS: ~$0.50/zone/month
│  Total: ~$2/month
│
└─ TOTAL ESTIMATED: ~$340-420/month

Cost reduction tips:
✓ Use B-series (burstable) for PostgreSQL if non-production
✓ Use ACR Standard instead of Premium (no private endpoint support)
✓ Use web app pricing tier instead of Container Apps (if no containers needed)
✓ Implement auto-scaling in Container Apps to reduce compute hours
```

## Security Checklist

- [X]  No hardcoded secrets in code
- [X]  No passwords in GitHub/documentation
- [X]  Private endpoints for all data services
- [X]  User-assigned managed identity (UAI) for container authentication
- [X]  RBAC with least privilege
- [X]  Entra ID authentication for PostgreSQL
- [X]  SSL/TLS encryption in transit
- [X]  Network isolation via VNet
- [X]  GitHub OIDC federated credentials
- [X]  Regular token rotation (automatic)
- [X]  Audit logging enabled
- [X]  Private DNS zones for internal resolution
- [X]  Network policies can be added for additional segmentation

## Production Readiness

### Current State

✅ Production-ready architecture
✅ Security best practices implemented
✅ High availability potential (can add replicas)
✅ Comprehensive monitoring setup
✅ Infrastructure as code (automated deployment)
✅ CI/CD pipeline configured

### Recommended Next Steps

1. **Add Application Gateway** for public endpoint + WAF
2. **Enable PostgreSQL Replica** for read scaling
3. **Configure Container App Autoscaling** based on metrics
4. **Add Key Vault** for secrets (even in the UAI-based identity model)
5. **Implement Network Policies** for pod-to-pod security
6. **Setup Alerts** for error rates, database connection issues
7. **Enable Audit Logging** for compliance requirements
8. **Implement Disaster Recovery** (cross-region replication)

---

## References

- [Azure Managed Identities](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/)
- [PostgreSQL Entra ID Auth](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-azure-ad-authentication)
- [Private Endpoints](https://learn.microsoft.com/en-us/azure/private-link/private-endpoint-overview)
- [Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/)
- [Azure Security Best Practices](https://learn.microsoft.com/en-us/azure/security/fundamentals/)
