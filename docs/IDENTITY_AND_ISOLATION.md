# Identidade, autorização e isolamento por organização (proposta v0.1)

- **Status:** Proposto. Depende da aprovação das ADR-001 e ADR-002. Nada aqui está implementado.
- **Relacionados:** docs/DATA_MODEL.md, docs/ISOLATION_TEST_PLAN.md, docs/THREAT_MODEL.md (TM-01 a TM-04, TM-08, TM-09, TM-17, TM-30).

## 1. Princípios
1. O **Keycloak autentica** (quem é a pessoa). O **KAEL autoriza** (o que ela pode fazer em cada organização).
2. A organização de uma requisição é **derivada no servidor** a partir da identidade verificada e das associações (memberships) lidas do banco. Um identificador de organização enviado pelo cliente é apenas uma *seleção entre associações já verificadas*, nunca uma prova.
3. A autorização é checada **a cada requisição**, no backend. A interface não decide nada.
4. Falha fechada: sem contexto de organização, nenhuma linha de negócio é visível.
5. Não criamos criptografia própria de senhas, sessões ou tokens.

## 2. Identidade (Keycloak, OIDC)
- Fluxo do navegador: Authorization Code com PKCE. Tokens de acesso de vida curta (alvo: 5 a 15 minutos), com refresh controlado pelo Keycloak.
- A API valida em toda requisição: assinatura (chaves públicas do emissor), `iss`, `aud`, `exp`, e usa `sub` como identificador estável do usuário.
- Claims de organização ou papel no token **não são fonte de autorização**. Podem servir de dica de interface, nada mais.
- Recursos entregues pelo Keycloak: login, recuperação de senha, verificação de e-mail, proteção contra força bruta, MFA, e depois SSO por OIDC/SAML (intermediação de identidade) por organização.
- **Proposta de implantação:** um único realm no Cloud, com a pertença a organizações mantida no banco do KAEL. No Private, um Keycloak da instalação, com federação ao provedor de identidade corporativo quando houver. Ver PD-17.

## 3. Resolução da organização em cada requisição
1. Validar o token (seção 2) e achar o usuário por `sub`. Usuário desconhecido ou desativado: negar.
2. Abrir a transação e definir **apenas o usuário** no contexto (`app.user_id`).
3. Ler as memberships ativas do usuário (a política da tabela `memberships` só mostra as linhas do próprio usuário nesta fase).
4. Escolher a organização:
   - se o usuário tem uma única membership ativa, usa essa;
   - se tem várias, o cliente envia o `org_id` desejado (cabeçalho), e o servidor **só aceita se existir membership ativa** para ele. Caso contrário: negar (resposta idêntica à de recurso inexistente, para não permitir enumeração).
5. Definir `app.org_id` na mesma transação, com valor já verificado, e carregar o papel e as permissões da membership.
6. Autorizar a operação pelas permissões do papel (seção 5) e executar. As políticas de RLS atuam como segunda barreira.
7. Registrar o evento de auditoria quando for operação relevante, ou quando negada por falta de permissão.

Os valores de contexto são sempre passados por parâmetro, nunca concatenados em SQL, e definidos apenas por **uma única função do código** (ponto único, testável). O contexto vale só para a transação e é descartado no fim, o que é necessário com pool de conexões.

## 4. Usuários em várias organizações
Proposta: o usuário é global (uma pessoa, uma identidade) e pode ter memberships em várias organizações. Se isso não for desejado no Cloud, basta limitar a uma. Decisão pendente em PD-16.

## 5. Papéis e permissões (RBAC)
Fase inicial: papéis fixos definidos em código, com permissões granulares (recurso:ação). Papéis personalizados por organização ficam para depois (PD-18).

| Papel | Intenção |
|---|---|
| owner | Responsável pela organização: tudo, inclusive faturamento e exclusão da organização |
| admin | Gerencia usuários, integrações, automações e configurações |
| analyst | Envia arquivos, usa o agente, cria relatórios e dashboards |
| viewer | Lê dashboards e relatórios autorizados |
| auditor | Lê a trilha de auditoria e configurações, sem alterar dados |

Regras:
- Permissões negadas por padrão. Cada endpoint e cada ferramenta do agente declara a permissão exigida.
- Ações críticas (excluir dados, escrever em planilhas externas, executar automações com efeito externo) exigem permissão específica e, quando definido, aprovação humana.
- Ninguém pode elevar o próprio papel. Mudanças de papel são auditadas. O último `owner` não pode ser removido.
- Papéis de administração da organização exigem MFA (política configurável por organização).

## 6. Revogação
- A membership é consultada **em toda requisição**, então remover um usuário ou mudar o papel vale imediatamente, mesmo com token ainda válido.
- Desativar o usuário no Keycloak impede novos tokens. Tokens de vida curta limitam a janela restante.
- Tokens e integrações: revogar uma integração apaga a credencial cifrada e solicita revogação ao provedor.

## 7. Convites
- O convite guarda só o **hash** do token, com validade curta e uso único.
- Aceitar o convite exige usuário autenticado com e-mail verificado e igual ao convidado. O e-mail do convite não prova a identidade sozinho.
- Convites podem ser cancelados. A criação e o aceite são auditados.

## 8. Tarefas assíncronas e automações
- O payload do job leva `organization_id`, o usuário de origem (ou o ator de sistema) e um `run_id`.
- O worker **revalida** na execução: a organização está ativa, a membership e as permissões do usuário de origem ainda valem. Se não, o job falha e é auditado, sem efeito.
- Jobs de sistema usam um papel de ator de sistema com permissões mínimas, nunca as de um administrador.
- Processamento idempotente, com chaves de deduplicação (SR-IDEM).

## 9. Acesso da equipe KAEL (Cloud)
- Sem acesso permanente ao banco de produção de dados de clientes.
- Acesso emergencial por concessão com prazo, motivo e aprovação, totalmente auditado e visível ao cliente. Ver TM-34 e PD-19.

## 10. Papéis do banco (resumo; detalhes na ADR-001)
`kael_app` (aplicação: sem superuser, sem `BYPASSRLS`, não é dono das tabelas), `kael_migrator` (DDL, nunca usado em requisições), e um papel administrativo de uso excepcional e auditado.

## 11. Limite honesto desta abordagem
O contexto por GUC e as políticas de RLS **não** são uma barreira contra código malicioso executando dentro da aplicação, nem contra injeção de SQL. Por isso valem juntas: consultas só parametrizadas, nenhum SQL gerado pelo modelo, papel de banco com privilégios mínimos e a suíte de testes de vazamento. Para clientes que exigirem isolamento físico, existe o KAEL Private (ou banco dedicado, PD-05).
