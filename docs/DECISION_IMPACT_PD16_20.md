# Impacto das decisões PD-16 a PD-20 (análise antes de implementar)

- **Status:** Proposto. Análise de impacto, sem implementação. Nenhum documento do repositório é evidência de que uma propriedade existe: cada uma só vale quando comprovada por teste automatizado.
- **Decisões do responsável (2026-11-22):**
  - PD-16: um usuário pode pertencer a várias organizações no Cloud, com identidade global; cada membership tem papel, permissões e estado próprios; a troca é validada no backend.
  - PD-17: realm compartilhado no Cloud; realm independente por instalação Private; identidade separada por ambiente; realm dedicado por organização só como exceção Enterprise.
  - PD-18: o banco do KAEL é a fonte de verdade de organizações, memberships, papéis e permissões; o Keycloak cuida de identidade e autenticação.
  - PD-19: o backend valida a membership em cada operação; nunca confiar só em `tenant_id` do cliente ou em claim não validada.
  - PD-20: o Private funciona com identidade, banco, armazenamento e configuração independentes, sem dependência obrigatória do Cloud.

## 1. O que não muda
RLS forçado com `organization_id`, chaves compostas entre tabelas, papéis do banco (`kael_app`, `kael_migrator`), contexto por transação, auditoria só de acréscimo, isolamento de jobs e arquivos, e a lista de ameaças já existente. As decisões **confirmam** o desenho proposto em quase tudo.

## 2. Impacto no esquema de dados
| Mudança | Motivo |
|---|---|
| `users`: adicionar `idp_issuer`, e a unicidade passa a ser `(idp_issuer, idp_subject)` | Há vários realms (Private, ambientes, Enterprise). Só o `sub` não basta |
| `users`: adicionar `last_org_id` (preferência de interface) | Facilitar o login. **Não autoriza nada** |
| `memberships`: estados definidos (`invited`, `active`, `suspended`, `removed`) e papel por membership | Papel, permissões e estado próprios por associação |
| `organizations`: adicionar `security_policy` (ex.: MFA exigido por papel) e `realm_ref` (nulo no realm compartilhado) | MFA por organização; exceção de realm dedicado |
| `audit_events`: ação `org.switch` e registro da organização da requisição | Rastrear trocas de organização |
| Futuro: tabela de vínculos entre provedores de SSO e organizações | SSO no realm compartilhado sem vincular contas por e-mail |
| Sem tabela de papéis do Keycloak para autorização | PD-18: o banco do KAEL decide |
| Nenhuma tabela depende de serviços do Cloud no Private | PD-20 |

Ainda em aberto (PD-21): permissões próprias vão além do papel (sobreposições por membership)? Premissa atual: as permissões vêm do papel.

## 3. Impacto nos tokens
- O token carrega **só identidade**: `sub`, `iss`, `aud`, `azp`, `exp` e dados de nível de autenticação (MFA). **Sem** organização, papel ou grupo como autoridade (TM-43).
- Validação por instalação: lista permitida de emissores e `aud` específico por ambiente. Token de desenvolvimento não vale em produção, e token de um Private não vale em outro (TM-41).
- O nível de autenticação (MFA) é comparado com a política da **organização da requisição**. Se insuficiente, a API pede reautenticação reforçada.
- Não há token "da organização": a organização vai no cabeçalho de cada requisição e é revalidada. Isso evita guardar estado e chaves extras. Alternativa descartada por ora: um token assinado pelo KAEL com a organização, que exigiria nova gestão de chaves.

## 4. Impacto no fluxo de troca de organização
Veja o diagrama em `docs/IDENTITY_AND_ISOLATION.md`. Resumo:
1. `GET /v1/me` lista as memberships ativas.
2. `POST /v1/me/active-organization` valida, audita e devolve as permissões.
3. Todas as requisições levam o cabeçalho da organização, e o servidor revalida a membership a cada uma.
4. A interface descarta caches da organização anterior ao trocar.
5. Jobs usam a organização do payload.
Riscos novos: contexto antigo na interface (TM-38) e troca forjada ou com membership revogada (TM-37).

## 5. Impacto nos testes de isolamento
14 testes novos (IT-40 a IT-53) em `docs/ISOLATION_TEST_PLAN.md`, cobrindo: troca sem membership ou suspensa, permissões distintas por organização, MFA por organização, alternância concorrente, interface sem dados da organização anterior, tokens de outro emissor ou ambiente, mesmo `sub` em emissores diferentes, enumeração de usuários, vinculação por e-mail, Private sem acesso ao Cloud, separação de configuração entre ambientes e claims forjadas ignoradas.

## 6. Impacto no modelo de ameaças
Sete ameaças novas (TM-37 a TM-43) e quatro riscos novos (RK-17 a RK-20). A maior mudança de risco é o **raio de impacto do realm compartilhado** (TM-39): um comprometimento do Keycloak afeta todas as organizações do Cloud.

## 7. Impacto nas decisões pendentes
- PD-16 a PD-20 passam a **decididas**.
- Os assuntos que eu tinha numerado como PD-18, PD-19 e PD-20 foram renumerados: papéis personalizados e sobreposições (PD-21), auditoria e acesso emergencial (PD-22) e chaves primárias (PD-23).

## 8. Próximo passo, sem implementar produto
A prova de conceito do isolamento (RLS, papéis, pooling e a suíte IT-01 a IT-11, mais as que tocam o banco) rodando no CI com PostgreSQL real. Ela é o que permite avaliar a aprovação das ADR-001 e ADR-002.
