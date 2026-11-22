# KAEL — Enterprise AI & Data Intelligence Platform

Plataforma empresarial híbrida (KAEL Cloud e KAEL Private) de análise de dados, IA, BI e automação.

**Status:** Fase 0 — fundação e decisões arquiteturais. Nenhuma funcionalidade de negócio implementada.
**ADRs:** todas em estado *Proposto*. Nada aqui é decisão definitiva até a aprovação formal.

## Princípio
Segurança antes de funcionalidades. Nada é declarado seguro sem testes e evidências.

## Estrutura
- `apps/api` — backend (Python 3.12, FastAPI) — vazio na Fase 0
- `apps/worker` — processamento assíncrono (Dramatiq) — vazio na Fase 0
- `apps/web` — frontend (React, TypeScript, Vite) — vazio na Fase 0
- `infra/compose` — ambiente local de desenvolvimento (Postgres, Redis, MinIO, Keycloak)
- `docs/` — arquitetura, segurança, riscos e ADRs
- `tests/repo` — testes que validam a estrutura e as regras do repositório

## Primeiros passos
Veja `docs/DEVELOPMENT.md`.

## Regras
- Sem segredos no repositório.
- Sem dados reais de clientes em testes.
- `main` protegida: mudanças só por pull request com CI aprovado.
