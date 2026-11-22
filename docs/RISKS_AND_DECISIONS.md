# Riscos e decisões pendentes

## Riscos
| ID | Risco | Impacto | Mitigação planejada | Estado |
|---|---|---|---|---|
| RK-01 | Vazamento entre organizações por contexto RLS mal definido (pooling, jobs) | Crítico | Contexto por transação, testes de vazamento, revisão | Aberto |
| RK-02 | Funções privilegiadas ou papel com BYPASSRLS usados na aplicação | Crítico | Papéis separados, proibir SECURITY DEFINER por padrão | Aberto |
| RK-03 | Vazamento de credenciais de integrações | Alto | Cifra em envelope, rotação, secret scanning | Aberto |
| RK-04 | Prompt injection via conteúdo de planilhas | Alto | Conteúdo como dado, ferramentas validadas, aprovação humana | Aberto |
| RK-05 | Arquivos maliciosos enviados | Alto | Validação de formato, isolamento, sem conteúdo ativo | Aberto |
| RK-06 | Desempenho de RLS em volume | Médio | Medição na PoC, índices por organização | Aberto |
| RK-07 | Efeitos duplicados por reentrega de jobs | Médio | Idempotência, chaves de deduplicação | Aberto |
| RK-08 | Divergência entre Cloud e Private | Alto | Base única, mesma suíte de testes nos dois perfis | Aberto |
| RK-09 | Capacidades da API do Power BI menores que o desejado | Médio | Verificar a API oficial antes de prometer | Aberto |
| RK-10 | Perda de dados ou recuperação não testada | Alto | Backups e restauração testados | Aberto |
| RK-11 | Complexidade operacional do Private | Médio | Documentação e atualizações versionadas | Aberto |
| RK-12 | Perda de mensagens no Redis (durabilidade da fila) | Médio | Persistência configurada, reprocessamento idempotente | Aberto |

## Decisões pendentes
| ID | Pergunta | Necessária antes de |
|---|---|---|
| PD-01 | Keycloak no Cloud: autogerenciado ou serviço equivalente? | Aprovar ADR-002 |
| PD-02 | Gestão de segredos no Private (Vault, segredos do orquestrador, outro)? | Aprovar ADR-002 |
| PD-03 | Gestão das chaves de cifra de credenciais (KMS no Cloud; equivalente no Private)? | Integrações |
| PD-04 | Provedor de nuvem e PostgreSQL gerenciado do Cloud? | Aprovar ADR-001 e 002 |
| PD-05 | Isolamento só por RLS, ou banco/esquema dedicado para clientes grandes no Cloud? | Modelo de dados |
| PD-06 | Redis suficiente como broker ou exigir durabilidade extra? | Worker |
| PD-07 | Verificação antimalware de uploads (ferramenta)? | Motor de dados |
| PD-08 | Modelo de IA padrão e política de dados enviados ao provedor? | Motor de IA |
| PD-09 | Requisitos de residência de dados e LGPD? | Cloud |
| PD-10 | Modelo de licenciamento do Private? | Comercial |
| PD-11 | Tags fixas das imagens (MinIO, Keycloak, Postgres, Redis) e política de atualização | Primeiro uso do Compose |
| PD-12 | Ferramentas de pacotes e lint (gerenciador Python, pnpm ou npm, linters)? | apps/api e apps/web |
| PD-13 | Política de atualização e suporte de versões do Private | Aprovar ADR-002 |
| PD-14 | Política de retenção de dados | Modelo de dados |
| PD-15 | Escopo de SSO (OIDC, SAML) no primeiro lançamento | Identidade |
