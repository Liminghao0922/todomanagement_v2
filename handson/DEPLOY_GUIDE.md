# Deployment Guide (Placeholder)

[English](DEPLOY_GUIDE.md) | [简体中文](DEPLOY_GUIDE-zh_CN.md) | [日本語](DEPLOY_GUIDE-ja_JP.md)

> 🚧 **Placeholder.** This document will be filled in during the v2 deployment validation pass. The intended outline matches `infra/deploy.ps1` and the architecture in [`docs/ARCHITECTURE_GUIDE.md`](../docs/ARCHITECTURE_GUIDE.md):
>
> 1. Prerequisites (Azure CLI, Functions Core Tools, Node, Python, Bicep)
> 2. Bicep deploy via `infra/deploy.ps1` (Cosmos / OpenAI / Functions / SWA / Foundry-handoff / Graph app registration)
> 3. Foundry agent configuration (using `foundry-agent-config.json` as the template)
> 4. Function App code publish (`func azure functionapp publish ...`)
> 5. Static Web App build & deploy
> 6. Smoke tests (sign in → CRUD → vector search → Project Graph → chat)
