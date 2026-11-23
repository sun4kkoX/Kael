# Plano de testes de isolamento (proposta v0.1)

- **Status:** Proposto. Os testes ainda não existem. Este plano define o que a prova de conceito de RLS (ADR-001) e a primeira versão da API precisam provar.
- **Regra:** qualquer vazamento entre organizações é falha de teste. Nada de dados reais de clientes: apenas dados sintéticos de duas organizações de teste (A e B).
- **Ferramentas:** pytest com Testcontainers (PostgreSQL real), cenários de API e, para a interface, Playwright.

## 1. Banco de dados (nível SQL)
| ID | Teste | Resultado esperado | Ameaça |
|---|---|---|---|
| IT-01 | Com contexto da organização A, ler, alterar e apagar linhas da B em **cada** tabela de negócio | Zero linhas afetadas | TM-08 |
| IT-02 | Inserir linha com `organization_id` da B estando no contexto da A | Recusado (WITH CHECK) | TM-08 |
| IT-03 | Referência cruzada por chave composta (ex.: dataset da A apontando para arquivo da B) | Violação de chave estrangeira | TM-08 |
| IT-04 | Consulta **sem** contexto definido | Zero linhas (falha fechada) | TM-08 |
| IT-05 | Reuso da mesma conexão do pool: transação com A, depois transação sem contexto | Nenhum dado da A visível | TM-08 |
| IT-06 | Transações concorrentes alternando organizações em muitas conexões | Nunca aparece dado de outra organização | TM-08 |
| IT-07 | Catálogo: o papel `kael_app` não é superuser, não tem `BYPASSRLS`, não é dono das tabelas | Verificação passa | TM-09 |
| IT-08 | Catálogo: **toda** tabela com `organization_id` tem RLS habilitado, forçado e as 4 políticas | Falha se alguma tabela nova esquecer | TM-09 |
| IT-09 | Nenhuma função `SECURITY DEFINER` fora de uma lista aprovada | Falha se surgir nova | TM-09 |
| IT-10 | Alterar `organization_id` de uma linha existente | Recusado | TM-08 |
| IT-11 | UPDATE, DELETE e TRUNCATE em `audit_events` pelo papel da aplicação | Negado | TM-36 |

## 2. API (nível de aplicação)
| ID | Teste | Resultado esperado | Ameaça |
|---|---|---|---|
| IT-20 | Requisição sem token, com token expirado, revogado, com `aud` ou `iss` errados | 401 | TM-02 |
| IT-21 | Usuário autenticado sem nenhuma membership | Negado | TM-03 |
| IT-22 | Usuário da A envia `org_id` da B no cabeçalho | Negado, resposta igual à de recurso inexistente | TM-03 |
| IT-23 | IDOR: usuário da A acessa por ID cada recurso da B (arquivos, relatórios, conversas, integrações) | 404 em todos | TM-03 |
| IT-24 | Elevação de privilégio: analyst tenta mudar o próprio papel, convidar admin, ver auditoria | Negado | TM-04 |
| IT-25 | Mass assignment: enviar campos extras (`organization_id`, `role`) no corpo | Ignorados ou rejeitados pelo modelo estrito | TM-04 |
| IT-26 | Membership removida enquanto o token ainda vale | Acesso negado imediatamente | TM-30 |
| IT-27 | Convite: token reutilizado, expirado, e-mail diferente do autenticado | Negado | TM-03 |
| IT-28 | Remover o último owner | Recusado | TM-04 |
| IT-29 | Respostas e logs não contêm segredos nem tokens | Verificação passa | TM-33 |

## 3. Armazenamento, worker, integrações e IA
| ID | Teste | Resultado esperado | Ameaça |
|---|---|---|---|
| IT-30 | Gerar URL de download de arquivo de outra organização | Negado antes de gerar a URL | TM-17 |
| IT-31 | Nome de arquivo hostil (`../`, caracteres especiais) | Chave do servidor inalterada, sem path traversal | TM-16 |
| IT-32 | Job com `organization_id` da A e usuário sem permissão na A | Falha auditada, sem efeito | TM-30 |
| IT-33 | Job executado após revogação da membership | Falha auditada, sem efeito | TM-30 |
| IT-34 | Reexecução do mesmo job e da mesma automação | Efeito único (idempotência) | TM-29 |
| IT-35 | Credencial de integração da A lida por usuário da B, e banco consultado direto | Negado, e só texto cifrado no banco | TM-24, TM-26 |
| IT-36 | Callback OAuth com `state` de outra organização ou usuário | Rejeitado | TM-26 |
| IT-37 | Agente: parâmetro de organização inventado pelo modelo e ID de dataset da B | Ignorado e negado, pois a organização vem da sessão | TM-20 |
| IT-38 | Planilha com instruções escondidas pedindo para ignorar regras ou usar outra ferramenta | Tratada como dado, nenhuma ferramenta nova habilitada | TM-19 |
| IT-39 | Exportação com células iniciadas por `=`, `+`, `-`, `@` | Neutralizadas | TM-15 |

## 3b. Multi-organização, realms e ambientes (decisões PD-16 a PD-20)
| ID | Teste | Resultado esperado | Ameaça |
|---|---|---|---|
| IT-40 | Trocar para organização sem membership | Negado e auditado, resposta igual à de recurso inexistente | TM-37 |
| IT-41 | Trocar para organização com membership suspensa ou removida | Negado | TM-37 |
| IT-42 | Usuário `admin` na A e `viewer` na B tenta ação de admin com o cabeçalho da B | Negado (permissão vale só na organização da requisição) | TM-37 |
| IT-43 | Política de MFA da organização: token sem o nível exigido acessa a organização que exige MFA | Reautenticação reforçada exigida | TM-37 |
| IT-44 | Requisições concorrentes com o mesmo token alternando organizações A e B | Cada resposta só contém dados da organização do seu cabeçalho | TM-37 |
| IT-45 | Interface (Playwright): após trocar de organização, nada da anterior fica em tela nem em cache | Nenhum dado da organização anterior | TM-38 |
| IT-46 | Token de outro emissor, de outro ambiente ou de outra instalação Private | 401 | TM-41 |
| IT-47 | Mesmo `sub` vindo de emissores diferentes | Usuários distintos, nunca o mesmo | TM-41 |
| IT-48 | Busca e listagem de usuários só mostram quem tem membership na organização da requisição | Nenhum usuário de outra organização | TM-39 |
| IT-49 | Provedor de SSO de uma organização tenta assumir o e-mail de usuário existente em outra | Vinculação recusada sem verificação explícita | TM-40 |
| IT-50 | Private com saída de rede para hosts do Cloud bloqueada: instalação e suíte completa | Tudo passa, nenhuma chamada ao Cloud | TM-42 |
| IT-51 | Verificação de configuração: desenvolvimento, homologação e produção com `iss`, `aud` e segredos distintos | Falha se houver repetição | TM-41 |
| IT-52 | Token assinado com claims forjadas de organização, papel ou grupo | Ignoradas, permissões vêm só do banco | TM-43 |
| IT-53 | Mudança de papel ou remoção de membership entre duas requisições do mesmo token | A segunda requisição já reflete a mudança | TM-37 |

## 4. Critérios de aceite
- Todos os testes IT-01 a IT-11 passam no PostgreSQL real, nos perfis Cloud e Private (ADR-002).
- IT-20 a IT-29 passam em toda rota existente. **Rota nova sem teste negativo não passa em revisão.**
- IT-08 impede o esquecimento de RLS em tabelas futuras.
- IT-40 a IT-53 passam antes de qualquer lançamento multi-organização.
- Os testes rodam no CI a cada pull request.
- Este plano não é evidência de implementação: a propriedade só vale quando o teste existe e passa.

## 5. Pendências
- Escolher a forma de gerar dados sintéticos multiempresa.
- Medir desempenho das políticas com volume representativo (RK-06).
- Incluir os testes de carga e de recuperação de backup no plano geral (TESTING.md, ainda a escrever).
