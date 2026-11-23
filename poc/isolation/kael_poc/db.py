"""Papeis, banco e conexoes da prova de conceito.

Separacao de papeis:
- kael_owner:    dono dos objetos (sem login).
- kael_migrator: executa migracoes (faz SET ROLE kael_owner). Nunca usado em requisicoes.
- kael_app:      papel de execucao da aplicacao. Sem superuser, sem bypass de RLS, sem DDL,
                 nao e dono de nada e nao e membro de outros papeis.

A credencial privilegiada (admin) e usada apenas aqui, para criar papeis e o banco.
Nenhum teste de isolamento usa essa credencial.
"""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

DB_NAME = "kael_poc"

ROLE_SPECS = {
    "kael_owner": "NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION",
    "kael_migrator": "LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION INHERIT",
    "kael_app": "LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION",
}


@dataclass
class PocEnv:
    migrator_dsn: str
    app_dsn: str
    db_name: str = DB_NAME
    applied_migrations: list = field(default_factory=list)


def admin_dsn_from_environment():
    """Devolve (dsn_admin, container_ou_None). Falha, em vez de pular, se nao houver PostgreSQL."""
    dsn = os.environ.get("KAEL_POC_ADMIN_DSN")
    if dsn:
        return dsn, None
    try:
        from testcontainers.postgres import PostgresContainer  # caminho local opcional
    except ImportError as exc:
        raise RuntimeError(
            "Defina KAEL_POC_ADMIN_DSN (PostgreSQL real) ou instale testcontainers com Docker. "
            "A prova de conceito nao roda sem PostgreSQL real."
        ) from exc
    container = PostgresContainer("postgres:16")
    container.start()
    host = container.get_container_host_ip()
    port = container.get_exposed_port(5432)
    dsn = f"postgresql://{container.username}:{container.password}@{host}:{port}/{container.dbname}"
    return dsn, container


def bootstrap(admin_dsn: str) -> PocEnv:
    """Cria papeis e banco do zero. Senhas aleatorias, so em memoria."""
    passwords = {
        "kael_migrator": secrets.token_urlsafe(24),
        "kael_app": secrets.token_urlsafe(24),
    }
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        for role, spec in ROLE_SPECS.items():
            exists = admin.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
            verb = "ALTER" if exists else "CREATE"
            stmt = sql.SQL("{verb} ROLE {name} {spec}").format(
                verb=sql.SQL(verb), name=sql.Identifier(role), spec=sql.SQL(spec)
            )
            if role in passwords:
                stmt = sql.SQL("{stmt} PASSWORD {pw}").format(
                    stmt=stmt, pw=sql.Literal(passwords[role])
                )
            admin.execute(stmt)
        admin.execute("GRANT kael_owner TO kael_migrator")
        admin.execute("REVOKE kael_owner FROM kael_app")
        db = sql.Identifier(DB_NAME)
        admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(db))
        admin.execute(sql.SQL("CREATE DATABASE {} OWNER kael_owner").format(db))
        admin.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(db))
        admin.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO kael_migrator, kael_app").format(db))
    return PocEnv(
        migrator_dsn=make_conninfo(admin_dsn, user="kael_migrator",
                                   password=passwords["kael_migrator"], dbname=DB_NAME),
        app_dsn=make_conninfo(admin_dsn, user="kael_app",
                              password=passwords["kael_app"], dbname=DB_NAME),
    )


def connect(dsn: str) -> psycopg.Connection:
    """Conexao em autocommit: cada transacao e aberta explicitamente com conn.transaction().
    Isso garante BEGIN/COMMIT reais (e nao savepoints), requisito do contexto local a transacao."""
    return psycopg.connect(dsn, autocommit=True)
