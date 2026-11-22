.PHONY: validate compose-check

validate:
	python -m pytest -q

# Valida a sintaxe do Compose com valores fictícios (nunca usar em ambiente real).
compose-check:
	POSTGRES_ADMIN_PASSWORD=x REDIS_PASSWORD=x MINIO_ROOT_USER=x MINIO_ROOT_PASSWORD=xxxxxxxx \
	MINIO_IMAGE=minio/minio:fixar-tag KEYCLOAK_ADMIN_USER=x KEYCLOAK_ADMIN_PASSWORD=x \
	docker compose -f infra/compose/docker-compose.dev.yml config -q
