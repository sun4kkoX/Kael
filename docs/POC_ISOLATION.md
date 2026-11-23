# Prova de conceito de isolamento: escopo, desenho e resultados

- **Status:** Proposto. A prova de conceito foi **escrita, mas ainda não foi executada** quando este documento foi criado. Os resultados abaixo ficam como pendentes até a primeira execução do CI.
- **Autorização:** aprovada pelo responsável em 2026-11-22, com escopo e condições registrados abaixo.
- **Código:** `poc/isolation/`. **Workflow:** `.github/workflows/isolation-poc.yml`.

## 1. Escopo autorizado
1. Esquema PostgreSQL mínimo: users, organizations, memberships e tabelas de teste.
2. RLS habilitado e forçado.
3. Separação entre dono, migração e execução da aplicação.
4. Testes IT-01 a IT-11 com PostgreSQL real, incluindo SELECT, INSERT, UPDATE, DELETE e lote.
5. Testes de contexto transacional, conexões reutilizadas, membership revogada e falsificação de organização.
6. Workflow no GitHub Actions.

## 2. Condições respeitadas
| Condição | Como é garantida |
|---|---|
| Sem funcionalidades de negócio | Apenas tabelas de teste e operações para montar dados |
| Sem SQLite | Teste de estrutura do repositório rejeita a palavra "sqlite" no código da PoC |
| Sem testes só com credencial privilegiada | Fixture exige `session_user = kael_app`. Teste de estrutura rejeita uso de DSN administrativo nos testes |
| Sem superuser nem bypass de RLS no papel da app | IT-07 consulta o catálogo e tenta operações privilegiadas. Teste de estrutura rejeita atributos perigosos nos scripts |
| Contexto transacional e validado no backend | `set_config(..., true)` por parâmetro, validação de membership antes de definir a organização (IT-05 e testes de falsificação) |
| Sem mascarar falhas nem desabilitar testes | Teste de estrutura rejeita `skip`. O relatório trata pulo como falha. Há um único `xfail` estrito, explícito e listado como limitação |

## 3. Desenho (variante da ADR-001)
- A ADR-001 propôs políticas com `organization_id = app_org_id()`. A PoC usa uma **variante com defesa em profundidade**: as políticas também exigem `app_is_member(organization_id)`, uma função `SECURITY INVOKER` que confere membership ativa do usuário do contexto. Assim, revogar uma membership vale mesmo com contexto antigo.
- `memberships` **não** usa essa checagem, porque consultaria a própria tabela (recursão de política). Ela usa `user_id = app_user_id() OR organization_id = app_org_id()`.
- Sem funções `SECURITY DEFINER`. Sem DELETE em `organizations` e `users`. `audit_events` é somente SELECT e INSERT.
- Se os resultados forem aceitos, a ADR-001 deve ser atualizada para refletir esta variante.

## 4. Limitações conhecidas (declaradas antes da execução)
1. **Atacante com SQL arbitrário como `kael_app`** pode forjar `app.user_id` e `app.org_id` juntos e ler dados da organização escolhida. O RLS por contexto não é barreira contra isso. É coberto por teste `xfail` estrito (`test_limit_...`), que mostra a propriedade desejada e a falha esperada. A defesa é a aplicação: consultas parametrizadas, nenhum SQL gerado por modelo e menor privilégio.
2. **Autorização por papel (RBAC)** não está no banco nesta PoC: qualquer membro ativo com contexto válido pode, no nível do banco, inserir membros ou alterar dados da organização. O RBAC fica na aplicação.
3. **Listagem de membros por organização** depende do contexto de organização na tabela `memberships`, sem checagem de membership (recursão de política). Uma visão ou função vetada poderá resolver isso depois.
4. **Verificações de integridade referencial** (chaves estrangeiras e únicas) ignoram RLS por definição do PostgreSQL: um erro de chave duplicada pode revelar a existência de um valor.
5. **Desempenho** das políticas (RK-06) não é medido aqui.
6. **Usuários** só enxergam a si mesmos nesta PoC.
7. Backup e restauração, pooler externo (como PgBouncer) e PostgreSQL gerenciado **não** são exercitados.
8. A PoC cobre o **banco**. Não cobre API, tokens, Keycloak nem armazenamento de arquivos.

## 5. Como ler as evidências
No GitHub, aba **Actions**, workflow **Isolation PoC**:
- o **resumo** da execução mostra o resultado de IT-01 a IT-11 e os casos individuais;
- o artefato **poc-isolation-evidence** traz `junit.xml` e arquivos de evidência (ambiente, papéis, privilégios, RLS por tabela, políticas e migrações aplicadas).

## 6. Resultados
**Pendentes.** Serão registrados aqui somente depois de uma execução real do CI, com o endereço da execução. Falhas serão registradas como falhas, sem alteração do teste para fazê-lo passar.

| Teste | Resultado | Execução |
|---|---|---|
| IT-01 a IT-11 | Pendente | |
| Revogação, falsificação | Pendente | |
| Limitação conhecida | Pendente | |
