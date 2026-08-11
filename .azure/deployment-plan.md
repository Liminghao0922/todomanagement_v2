# Azure Evolution Deployment Plan

## Status
Ready for Validation

## Scope
Migrate Todo Management from FastAPI + PostgreSQL + Container Apps to Azure Functions + Cosmos DB (serverless, vector + graph) + Azure Static Web Apps + Azure AI Foundry integration.

## Decisions
- LLM orchestration: Azure AI Foundry (Web UI + Function App integration)
- Cosmos mode: Serverless
- Graph mode: Cosmos DB managed graph (Gremlin)
- Frontend compatibility: Allow moderate API/UI additions
- IaC: Bicep
- Calendar scenario: A (priority advice) + C (auto action item extraction)
- Calendar processing: background periodic scan (timer trigger)
- Relation types: SIMILAR_TO, BLOCKED_BY, PRECEDES, SUBTASK_OF
- Deployment lifecycle: `azd provision` handles infrastructure, identities, RBAC, Entra configuration, and Foundry connections; `azd deploy` handles application artifacts, MCP image activation, Foundry Agent versions, Function/SWA publishing, linking, and health checks.

## Execution Steps
1. Build Azure Functions backend skeleton with Cosmos repositories and calendar/action-item workflows.
2. Add vector embedding flow for Todo write/update and vector search endpoint support.
3. Add graph relation APIs and relation modeling for 4 edge types.
4. Update frontend with AI chat API wrapper and assistant panel.
5. Replace infra Bicep with Function + SWA + Cosmos + OpenAI + Foundry-ready outputs.
6. Update deployment script and parameters.
7. Validate syntax and run project error checks.
8. Split the existing postprovision automation into shared context, postprovision, and postdeploy scripts; wire `azure.yaml` command hooks so `azd up` runs both phases in order.

## Risks
- Foundry built-in tools can vary by tenant/region features; custom tool fallback remains available.
- Gremlin and NoSQL vector are separate Cosmos APIs; this design deploys both account capabilities and app-level abstraction.

## Validation
- API lint/import check
- Frontend type check
- Bicep compile validation
- Provision/deploy split: both PowerShell entry points parse successfully, `azure.yaml` loads successfully, and `azd provision --preview --no-prompt` completes without running application deployment.
- Deployment scripts are physically separated: `azd-common.ps1` owns output discovery/helpers, `azd-postprovision.ps1` owns infrastructure configuration only, and `azd-deploy.ps1` owns application deployment only. No phase switch or cross-script delegation remains.
