# Segurança — requisitos

Este documento define **requisitos**, não afirma conformidade. Cada requisito só é considerado atendido com evidência (teste, configuração verificada ou revisão registrada). Não declaramos certificações ou padrões sem auditoria.

## Isolamento multiempresa (SR-ISO)
- SR-ISO-01: o servidor determina a organização a partir da identidade autenticada e de associações verificadas; um `tenant_id` do cliente nunca é fonte de autorização.
- SR-ISO-02: RLS forçado em todas as tabelas de negócio, com políticas para SELECT, INSERT, UPDATE e DELETE.
- SR-ISO-03: a aplicação não usa credenciais administrativas nem papel com `BYPASSRLS`.
- SR-ISO-04: arquivos, relatórios, conversas, configurações, credenciais e integrações isolados por organização.
- SR-ISO-05: operações assíncronas carregam e revalidam o contexto da organização.
- SR-ISO-06: suíte automatizada tenta acessar dados de outra organização e falha em qualquer vazamento.
- Verificação: testes de isolamento no CI, nos perfis Cloud e Private.

## Proteção de credenciais (SR-CRED)
- SR-CRED-01: nenhum segredo no repositório, em imagens ou em logs.
- SR-CRED-02: tokens de integrações cifrados em repouso, associados à organização e ao usuário autorizado.
- SR-CRED-03: rotação e revogação suportadas (inclusive revogação de acesso a Google Sheets e Power BI).
- SR-CRED-04: segredos fornecidos por gerenciador de segredos ou variáveis do ambiente, nunca por código.
- SR-CRED-05: logs filtram senhas, tokens e chaves.
- Verificação: secret scanning do GitHub, testes de log, revisão de configuração.

## Idempotência (SR-IDEM)
- SR-IDEM-01: operações mutáveis da API aceitam chave de idempotência, escopada por organização.
- SR-IDEM-02: jobs e automações toleram reexecução (entrega pelo menos uma vez), sem efeitos duplicados.
- SR-IDEM-03: ações externas (notificações, escrita em planilhas) usam chave de deduplicação.
- Verificação: testes de repetição e de concorrência.

## Portabilidade (SR-PORT)
- SR-PORT-01: dependências externas atrás de interfaces (S3, OIDC, segredos, fila, modelo de IA).
- SR-PORT-02: sem recursos exclusivos de fornecedor sem ADR.
- SR-PORT-03: o Private roda sem serviços proprietários do Cloud.
- Verificação: instalação em ambiente limpo, nos dois perfis.

## Arquivos (SR-FILE)
Validação de formato real, limites de tamanho e tempo, processamento isolado no worker, nunca executar macros ou conteúdo ativo, limpeza de temporários.

## IA (SR-AI)
Sem SQL arbitrário gerado pelo modelo. Conteúdo de planilhas é dado, nunca instrução. Ferramentas explícitas, autorizadas e validadas no servidor. Aprovação humana para ações relevantes. Limites de custo e execução. Registro das operações.

## Auditoria (SR-AUD)
Autenticações, falhas de acesso, mudanças de permissão, execuções de agentes e automações, eventos administrativos. Sem conteúdo sensível desnecessário.

## Repositório (SR-REPO)
`main` protegida, pull request com CI, secret scanning e Dependabot ativos, dependências justificadas.
