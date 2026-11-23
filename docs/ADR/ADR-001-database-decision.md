# ADR-001 — Decisão de banco de dados

- **Status:** Proposto (não aprovado)
- **Aprovação:** pendente
- **Relacionadas:** ADR-002, docs/SECURITY.md, docs/RISKS_AND_DECISIONS.md

## Contexto
O KAEL opera em modelo híbrido: Cloud (SaaS multiempresa) e Private (instalação dedicada). O isolamento entre organizações é a propriedade de segurança mais importante. A persistência não pode prender o produto a um único fornecedor.

## Direcionadores
Compatibilidade com Cloud e Private, isolamento multiempresa, segurança, portabilidade, custo operacional, backup e recuperação, migrações, observabilidade, dependência de fornecedor.

## Opções avaliadas
1. PostgreSQL autogerenciado
2. PostgreSQL gerenciado (qualquer provedor que ofereça PostgreSQL padrão)
3. Supabase
Outras tecnologias não foram avaliadas por falta de justificativa concreta.

## Matriz comparativa (estimativa preliminar, sem prova de conceito)
| Critério | Autogerenciado | Gerenciado | Supabase |
|---|---|---|---|
| Uso no Private | Adequado: roda em qualquer ambiente do cliente | Parcial: depende de o cliente ter o serviço | Parcial: autohospedagem inclui vários componentes adicionais para operar |
| Uso no Cloud | Parcial: toda a operação é nossa | Adequado | Adequado |
| Isolamento / RLS | Total controle | Total controle (dentro das permissões do serviço) | Suportado, porém integrado à camada de autenticação e API do produto |
| Autenticação | Externa (Keycloak/OIDC) | Externa (Keycloak/OIDC) | Embutida, o que cria acoplamento e duplica o Keycloak já aprovado |
| Portabilidade | Alta | Alta (se só usar SQL e extensões comuns) | Média: depende do quanto se usar recursos próprios |
| Custo operacional | Alto | Médio | Baixo no início, com risco de lock-in |
| Backup e recuperação | A construir e testar | Embutido, a validar (restauração real) | Embutido, a validar |
| Dependência de fornecedor | Nenhuma | Baixa | Média a alta |
| Observabilidade | A construir | Parcial embutida | Parcial embutida |
| Migrações | Alembic | Alembic | Alembic, com cuidado com esquemas gerenciados pela plataforma |

## Decisão proposta
PostgreSQL como núcleo de persistência, acessado apenas via SQLAlchemy 2 e Alembic, usando SQL e extensões amplamente disponíveis. Sem recursos exclusivos de fornecedor.
- **Cloud:** PostgreSQL gerenciado (provedor pendente, PD-04).
- **Private:** PostgreSQL dedicado por cliente (container ou instância do cliente).
- **Autenticação:** fora do banco, por OIDC (Keycloak).
- **Supabase:** não adotado como base. Pode ser reavaliado como provedor de hospedagem PostgreSQL, sem usar suas camadas de autenticação e API.

## Modelo de isolamento proposto (a validar por prova de conceito)
1. Tabelas de negócio com `organization_id` obrigatório.
2. RLS habilitado e **forçado** (`FORCE ROW LEVEL SECURITY`) com políticas explícitas para SELECT, INSERT, UPDATE e DELETE.
3. Papéis separados:
   - papel de aplicação: sem superuser, sem `BYPASSRLS`, sem DDL, não dono das tabelas;
   - papel de migração: executa DDL, nunca usado em requisições;
   - papel administrativo: uso excepcional, auditado.
4. Contexto da organização definido por transação (por exemplo, configuração local à transação), pelo código do servidor, a partir da identidade autenticada e das associações verificadas. Nunca a partir de valor enviado pelo cliente.
5. Com pooling, o contexto deve ser definido e descartado a cada transação, de forma que nenhuma conexão reutilizada carregue o contexto anterior.
6. Operações em background carregam a organização no payload do job, validada no início do processamento, e usam o mesmo mecanismo.
7. Funções `SECURITY DEFINER`: proibidas por padrão. Se necessárias, exigem revisão, `search_path` fixo e teste dedicado.
8. Defesa em profundidade: RLS não substitui autorização na aplicação, e a aplicação não substitui RLS.

## Credenciais e dados sensíveis
- Tokens de integrações (Google, Power BI) são armazenados cifrados pela aplicação (cifra em envelope), nunca em texto claro no banco. A gestão das chaves é pendente (PD-03).
- Logs e auditoria não registram segredos.

## Idempotência
- Tabela de chaves de idempotência escopada por `(organization_id, chave)`, com hash da requisição e resultado. Detalhes de implementação na fase de API.
- Jobs com identificador determinístico e handlers idempotentes (entrega pelo menos uma vez).

## Portabilidade
- Sem extensões ou recursos exclusivos de fornecedor sem nova ADR.
- Migrações versionadas (Alembic), reproduzíveis em Cloud e Private.
- Restauração de backup testada nos dois formatos.

## Consequências
- Positivo: um único modelo de dados, portável e auditável.
- Negativo: a operação do PostgreSQL no Private e o desenho correto de RLS exigem disciplina e testes contínuos.

## Riscos específicos
RK-01 (vazamento por contexto mal definido com pooling), RK-02 (funções privilegiadas), RK-06 (desempenho de RLS em volume). Ver docs/RISKS_AND_DECISIONS.md.

## Critérios para aprovar esta ADR
- Prova de conceito com RLS forçado, papéis separados e pooling, com suíte automatizada que tenta ler, alterar e apagar dados de outra organização e **falha em qualquer vazamento**.
- Teste de restauração de backup.
- Medição de desempenho das políticas RLS em volume representativo.
- Decisão do provedor Cloud (PD-04).

## Decisões de entrada aprovadas pelo responsável (2026-11-22)
Estas decisões **não aprovam esta ADR**. Ela continua *Proposta* até a prova de conceito.
- PD-16: um usuário pode ter memberships em várias organizações, cada uma com papel, permissões e estado próprios.
- PD-18: o banco do KAEL é a fonte de verdade de organizações, memberships, papéis e permissões.
- PD-19: a membership é validada pelo backend a cada operação, e o contexto de organização do banco só é definido com valor verificado.
- PD-20: no Private, o banco é dedicado e independente dos serviços do Cloud.
Impactos no esquema: `users` com `(idp_issuer, idp_subject)` único, `memberships` com estados, `organizations` com `security_policy` e `realm_ref`. Ver docs/DECISION_IMPACT_PD16_20.md. Nada disso é evidência de implementação.
