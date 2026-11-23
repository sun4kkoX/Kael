# Prova de conceito de isolamento multiempresa (PostgreSQL real)

Evidência técnica para a decisão final das ADR-001 e ADR-002. **Não contém funcionalidades de negócio.**
Status: Proposto. Aprovar a implementação não deve ser presumido: a decisão só vem depois dos resultados.

## O que é
- `migrations/`: esquema mínimo (`organizations`, `users`, `memberships`, `files`, `datasets`, `audit_events`), funções de contexto, RLS forçado e privilégios mínimos.
- `kael_poc/`: criação de papéis e banco, executor de migrações, camada "backend" que valida a membership e define o contexto, verificações de catálogo, relatório e evidências.
- `tests/`: testes com PostgreSQL real, sempre como `kael_app`.

## Papéis
| Papel | Função | Restrições |
|---|---|---|
| `kael_owner` | Dono dos objetos | Sem login, sem superuser, sem bypass de RLS |
| `kael_migrator` | Executa migrações (`SET ROLE kael_owner`) | Nunca usado nas requisições nem nos testes de isolamento |
| `kael_app` | Execução da aplicação | Sem superuser, sem bypass de RLS, sem DDL, não é dono de nada, não é membro de outros papéis |

A credencial administrativa do cluster só cria os papéis e o banco (`kael_poc.db.bootstrap`). Senhas dos papéis são aleatórias por execução.

## Como o contexto funciona
O backend (`kael_poc/backend.py`) abre a transação, define `app.user_id`, lê as memberships ativas do usuário, **valida** a organização pedida e só então define `app.org_id`, tudo com `set_config(..., true)` (local à transação) e por parâmetro. Além disso, o próprio banco confere se o usuário do contexto tem membership ativa (`kael.app_is_member`), então revogar a membership vale imediatamente.

## Como rodar
- **CI (referência):** workflow `Isolation PoC` (`.github/workflows/isolation-poc.yml`). Sobe PostgreSQL 16, roda os testes, publica o resumo e as evidências como artefato.
- **Local:** defina `KAEL_POC_ADMIN_DSN` (PostgreSQL real, usuário superuser só para o bootstrap) e rode, em `poc/isolation`: `pip install -r requirements.txt` e `python -m pytest -v`. Sem `KAEL_POC_ADMIN_DSN`, o código tenta Testcontainers (opcional, não exercitado pelo CI) e, se não houver, **falha** em vez de pular.

## Regras que os testes de estrutura do repositório impõem
Sem SQLite, sem `skip`, no máximo um `xfail` (a limitação conhecida, explícita), nenhuma credencial administrativa nos testes, nenhum papel com superuser ou bypass de RLS.

## Resultados
Preenchidos a partir da execução do CI (ver `docs/POC_ISOLATION.md`). Nada aqui é resultado antes de o CI rodar.
