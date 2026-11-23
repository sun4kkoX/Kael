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
| RK-13 | Injeção de fórmula em exportações CSV e Excel | Médio | Neutralizar células perigosas (TM-15) | Aberto |
| RK-14 | SSRF por URLs fornecidas pelo usuário nas integrações | Alto | Apenas hosts conhecidos (TM-27) | Aberto |
| RK-15 | Bomba de descompressão ou arquivo gigante | Alto | Limites e streaming (TM-14) | Aberto |
| RK-16 | Abuso interno pela equipe KAEL no Cloud | Alto | Mínimo privilégio e acesso emergencial auditado (TM-34) | Aberto |
| RK-17 | Raio de impacto de um comprometimento do realm compartilhado do Keycloak | Alto | Console admin restrito e com MFA, configuração como código, realm dedicado Enterprise (TM-39) | Aberto |
| RK-18 | Troca de organização com contexto desatualizado ou dados em cache na interface | Alto | Organização explícita por requisição, descarte de cache, testes (TM-37, TM-38) | Aberto |
| RK-19 | Token de um ambiente ou instalação aceito em outro | Alto | `iss` e `aud` separados por ambiente (TM-41) | Aberto |
| RK-20 | Dependência oculta do Cloud no Private | Alto | Teste com saída de rede bloqueada (TM-42) | Aberto |

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
| PD-21 | Papéis personalizados por organização e sobreposição de permissões por membership além do papel? | Autorização |
| PD-22 | Particionamento e retenção da auditoria; política de acesso emergencial da equipe KAEL | Auditoria |
| PD-23 | Estratégia de chaves primárias (UUID v4 ou v7 gerado na aplicação) | Modelo de dados |

## Decisões tomadas pelo responsável (2026-11-22)
| ID | Decisão | Documentos afetados |
|---|---|---|
| PD-16 | Usuário com identidade global pode pertencer a várias organizações. Cada membership tem papel, permissões e estado próprios, e a troca é validada no backend | IDENTITY_AND_ISOLATION, DATA_MODEL |
| PD-17 | Realm compartilhado no Cloud. Realm independente por instalação Private e por ambiente. Realm dedicado por organização só como exceção Enterprise | IDENTITY_AND_ISOLATION, ADR-002, ARCHITECTURE |
| PD-18 | O banco do KAEL é a fonte de verdade de organizações, memberships, papéis e permissões. O Keycloak cuida de identidade e autenticação | ADR-001, ADR-002, DATA_MODEL |
| PD-19 | O backend valida a membership em cada operação, sem confiar só em `tenant_id` do cliente ou em claim não validada | IDENTITY_AND_ISOLATION, THREAT_MODEL |
| PD-20 | O Private funciona com identidade, banco, armazenamento e configuração independentes, sem dependência obrigatória do Cloud | ADR-002, ARCHITECTURE, THREAT_MODEL |

Decidir não é implementar: as propriedades só valem quando comprovadas por testes automatizados. Análise em `docs/DECISION_IMPACT_PD16_20.md`.
