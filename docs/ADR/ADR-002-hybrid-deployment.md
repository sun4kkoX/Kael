# ADR-002 — Arquitetura de implantação híbrida Cloud/Private

- **Status:** Proposto (não aprovado)
- **Aprovação:** pendente
- **Relacionadas:** ADR-001, docs/SECURITY.md, docs/RISKS_AND_DECISIONS.md

## Contexto
O KAEL deve atender empresas que usam SaaS (Cloud) e empresas que exigem instalação dedicada (Private), sem manter duas plataformas com código duplicado.

## Opções consideradas
- **A. Base de código única, com perfis de implantação (proposta).**
- B. Duas bases de código independentes. Rejeitada: duplicação e divergência de segurança.
- C. Fork por cliente Private. Rejeitada: custo de manutenção e atualização.

## Decisão proposta
Monólito modular único, sem microserviços até haver necessidade comprovada. Diferenças entre Cloud e Private ficam em configuração e em `infra/`, nunca em ramificações de lógica de negócio.

## Perfis de implantação
| Aspecto | Cloud | Private |
|---|---|---|
| Tenancy | Multiempresa com RLS | Uma organização cliente por instalação (RLS permanece ativo) |
| Banco | PostgreSQL gerenciado | PostgreSQL dedicado |
| Armazenamento | S3 compatível | MinIO ou S3 compatível do cliente |
| Identidade | Keycloak (gerenciado por nós ou provedor equivalente, PD-01) | Keycloak da instalação, com possibilidade de federar ao IdP corporativo (OIDC/SAML) |
| Segredos | Gerenciador de segredos do provedor (PD-04) | Solução compatível com o ambiente do cliente (PD-02) |
| Atualizações | Contínuas e controladas por nós | Versionadas, documentadas, com janela do cliente (PD-13) |
| Observabilidade | OpenTelemetry centralizado | OpenTelemetry exportável para a stack do cliente |
| Backup | Nossa responsabilidade | Responsabilidade compartilhada, documentada |

Manter o RLS ativo também no Private garante que os dois perfis executem o mesmo código e os mesmos testes de isolamento.

## Fronteiras de portabilidade (interfaces)
O núcleo depende de interfaces, não de fornecedores: armazenamento de objetos (API S3), identidade (OIDC), repositório de segredos, fila de tarefas, provedor de modelo de IA (substituível por configuração) e envio de notificações. Cada implementação específica fica em `infra` ou em adaptadores.

## Requisitos transversais
- **Segurança:** requisitos em docs/SECURITY.md valem nos dois perfis. Nenhum controle é removido para facilitar o Private.
- **Isolamento multiempresa:** o servidor determina a organização pela identidade verificada (ADR-001).
- **Credenciais:** segredos nunca em código, imagem ou log. Segredos de integrações cifrados por organização. Rotação e revogação suportadas.
- **Idempotência:** operações mutáveis expostas por API aceitam chave de idempotência. Jobs e automações são idempotentes, pois a fila entrega pelo menos uma vez.
- **Portabilidade:** configuração por variáveis de ambiente e arquivos, imagens versionadas, nenhuma dependência obrigatória de serviço proprietário no Private.

## Ambientes
Desenvolvimento, homologação e produção separados. Sem dados reais de clientes em testes. Migrações destrutivas exigem validação, backup e autorização.

## Consequências
- Positivo: uma base de código, uma suíte de testes, manutenção menor.
- Negativo: exige disciplina de interfaces, testes executados nos dois perfis e documentação de instalação do Private.

## Critérios para aprovar esta ADR
- Subir o mesmo conjunto de testes de isolamento nos dois perfis.
- Procedimentos de instalação e atualização do Private escritos e executados em ambiente limpo.
- Decisões PD-01, PD-02, PD-04 e PD-13 resolvidas.
