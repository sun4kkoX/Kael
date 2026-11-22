# Desenvolvimento

## Validar a estrutura (Fase 0)
```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install pytest
make validate        # testes de estrutura e de regras do repositório
make compose-check   # valida a sintaxe do Compose (requer Docker)
```

## Subir a infraestrutura local (opcional)
```bash
cp .env.example .env   # preencha os valores localmente; nunca versione o .env
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env up -d
```
O Compose é só para desenvolvimento: portas ligadas em 127.0.0.1, Keycloak em modo dev.
Nenhuma imagem usa tag `latest`. A tag do MinIO deve ser fixada por você (PD-11).

## Regras
- Dependências novas exigem justificativa no pull request.
- Alterações de arquitetura exigem ADR.
