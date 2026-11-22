# Arquitetura (Fase 0 — proposta)

Monólito modular. Decisões em `docs/ADR/` (todas *Propostas*).

## Módulos planejados
Identidade e autorização, organizações, motor de dados, motor de IA, BI, automações, integrações, auditoria, administração. Nenhum implementado.

## Stack-base aprovada
Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, Alembic, PostgreSQL, Redis, Dramatiq, S3/MinIO, Keycloak, React, TypeScript, Vite, Tailwind, shadcn/ui, Docker Compose, pytest, Testcontainers, Playwright, GitHub Actions, OpenTelemetry.

## Fronteiras de confiança (a detalhar no THREAT_MODEL.md)
1. Navegador → API: não confiável.
2. API → banco: contexto da organização definido no servidor.
3. Arquivos enviados → worker: processamento isolado.
4. Conteúdo de planilhas → agente de IA: apenas dado.
5. API → integrações externas: credenciais por organização.

## Diagramas
Pendentes.
