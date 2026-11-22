# Modelo de dados (proposta v0.1)

- **Status:** Proposto. Esquema conceitual, ainda sem migrações. Depende da aprovação da ADR-001.
- **Convenções:** chaves `uuid` (estratégia exata em PD-20), datas em `timestamptz`, nomes em inglês nas tabelas e colunas. Toda tabela de negócio tem `organization_id NOT NULL`.

## 1. Regras de isolamento no esquema
1. Toda tabela de negócio tem `organization_id`, com RLS **habilitado e forçado** e políticas separadas de SELECT, INSERT, UPDATE e DELETE.
2. Pais expõem `UNIQUE (organization_id, id)` e filhos referenciam por **chave composta** `(organization_id, <pai>_id)`. Assim o banco recusa uma linha da organização A apontando para um objeto da organização B.
3. Colunas `organization_id` nunca são atualizáveis (política de UPDATE com `WITH CHECK`).
4. Valores sensíveis (credenciais) ficam cifrados pela aplicação (cifra em envelope). Segredos e tokens nunca aparecem em colunas de texto claro nem em `metadata` de auditoria.
5. A auditoria é de acréscimo: o papel da aplicação não tem UPDATE, DELETE nem TRUNCATE nela.

## 2. Tabelas
### 2.1 Plataforma e identidade
| Tabela | Conteúdo principal | Observação |
|---|---|---|
| `organizations` | id, slug, name, status, limits (cotas), created_at | Sem RLS por organização. Leitura restrita pelo papel de aplicação à organização do contexto |
| `users` | id, idp_subject (único), email, display_name, status | Identidade global, mínimo de dados pessoais |
| `memberships` | id, organization_id, user_id, role, status, invited_by, created_at | Único `(organization_id, user_id)`. Política dupla (seção 3) |
| `invitations` | id, organization_id, email, role, token_hash, expires_at, accepted_at, status | Só o hash do token |

### 2.2 Arquivos e dados
| Tabela | Conteúdo principal |
|---|---|
| `files` | id, organization_id, uploaded_by, storage_key (gerada pelo servidor, prefixo por organização), original_name (só exibição), declared_mime, detected_mime, size_bytes, sha256, status (pending, scanning, ready, rejected, deleted), expires_at |
| `datasets` | id, organization_id, file_id (FK composta), name, schema (colunas e tipos), row_count, status, created_by |
| `processing_runs` | id, organization_id, file_id (FK composta), kind, status, started_at, finished_at, error_code, metrics |

### 2.3 Agente de IA
| Tabela | Conteúdo principal |
|---|---|
| `conversations` | id, organization_id, user_id, title, created_at |
| `messages` | id, organization_id, conversation_id (FK composta), role, content, created_at |
| `agent_runs` | id, organization_id, user_id, conversation_id, model, status, tokens_in, tokens_out, cost_estimate, started_at, finished_at |
| `tool_executions` | id, organization_id, agent_run_id, tool_key, params (redigidos), result_status, approval_id, created_at |
| `approvals` | id, organization_id, requested_by, kind, payload, status, decided_by, decided_at |

### 2.4 BI e relatórios (rastreabilidade obrigatória)
| Tabela | Conteúdo principal |
|---|---|
| `kpi_definitions` | id, organization_id, key, name, spec (definição do cálculo), source_dataset_id |
| `kpi_values` | id, organization_id, kpi_id, period_start, period_end, value, source_dataset_id, run_id, computed_at |
| `dashboards` | id, organization_id, name, layout, created_by |
| `reports` | id, organization_id, title, kind, period_start, period_end, sources, criteria, limitations, file_id, status, created_by |

Cada indicador guarda fonte, período e execução, para que seja possível rastreá-lo até a origem.

### 2.5 Integrações e automações
| Tabela | Conteúdo principal |
|---|---|
| `integrations` | id, organization_id, provider (google_sheets, power_bi), connected_by, scopes, status, revoked_at |
| `integration_credentials` | id, organization_id, integration_id, ciphertext, key_ref, created_at, rotated_at |
| `automations` | id, organization_id, name, trigger, conditions, actions, schedule, requires_approval, status, created_by |
| `automation_runs` | id, organization_id, automation_id, idempotency_key, status, attempt, started_at, finished_at. Único `(organization_id, automation_id, idempotency_key)` |

### 2.6 Operação
| Tabela | Conteúdo principal |
|---|---|
| `idempotency_keys` | organization_id, scope, key, request_hash, status, response_ref, created_at, expires_at. Chave primária `(organization_id, scope, key)` |
| `audit_events` | id, organization_id (nulo para eventos de plataforma), actor_user_id, actor_type, action, resource_type, resource_id, outcome, ip, request_id, metadata (sem segredos), occurred_at. Candidata a particionamento por mês (PD-19) |
| `usage_records` | organization_id, period, metric (tokens, armazenamento, processamento), value |
| `retention_policies` | organization_id, resource_type, days. Valores definidos em PD-14 |

## 3. Padrão de políticas de RLS (ilustrativo, ainda não executado)
```sql
CREATE ROLE kael_app LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;

-- Sem SECURITY DEFINER. Contexto vazio vira NULL (falha fechada).
CREATE FUNCTION app_org_id() RETURNS uuid LANGUAGE sql STABLE AS
  $$ SELECT NULLIF(current_setting('app.org_id', true), '')::uuid $$;
CREATE FUNCTION app_user_id() RETURNS uuid LANGUAGE sql STABLE AS
  $$ SELECT NULLIF(current_setting('app.user_id', true), '')::uuid $$;

ALTER TABLE files ENABLE ROW LEVEL SECURITY;
ALTER TABLE files FORCE ROW LEVEL SECURITY;
CREATE POLICY files_select ON files FOR SELECT TO kael_app
  USING (organization_id = app_org_id());
CREATE POLICY files_insert ON files FOR INSERT TO kael_app
  WITH CHECK (organization_id = app_org_id());
CREATE POLICY files_update ON files FOR UPDATE TO kael_app
  USING (organization_id = app_org_id()) WITH CHECK (organization_id = app_org_id());
CREATE POLICY files_delete ON files FOR DELETE TO kael_app
  USING (organization_id = app_org_id());

-- memberships: enxerga as próprias linhas antes de a organização estar definida
CREATE POLICY memberships_select ON memberships FOR SELECT TO kael_app
  USING (user_id = app_user_id() OR organization_id = app_org_id());

-- Auditoria só de acréscimo
REVOKE UPDATE, DELETE, TRUNCATE ON audit_events FROM kael_app;

-- Contexto por transação, com valor verificado e passado por parâmetro:
-- SELECT set_config('app.user_id', $1, true);
-- SELECT set_config('app.org_id',  $2, true);
```
Detalhe importante: depois de um `set_config` local à transação, o parâmetro volta a **texto vazio** (não nulo) na conexão reutilizada, por isso o `NULLIF`.

## 4. Fluxo de dados sensíveis
- **Credenciais de integrações:** cifradas pela aplicação com chave por envelope. Chaves em KMS ou equivalente (PD-03). O banco só vê o texto cifrado.
- **Conteúdo de arquivos:** no armazenamento S3 compatível, com chave `org_id/…` gerada pelo servidor. O nome original nunca vira caminho.
- **Mensagens do agente:** podem conter dados de clientes. Retenção e política do provedor de IA em PD-08 e PD-14.

## 5. Pendências
- Estratégia de chaves (PD-20), particionamento e retenção da auditoria (PD-19).
- Papéis personalizados (PD-18) e organização por usuário (PD-16).
- Validar o desempenho das políticas de RLS em volume (RK-06).
- Escrever migrações **somente depois** da aprovação das ADRs.
