"""Executor de migracoes SQL versionadas (prova de conceito).

O produto real usara Alembic. Aqui o objetivo e testar as propriedades do banco, sem ORM.
Cada arquivo roda numa transacao, como kael_migrator com SET ROLE kael_owner.
Delimitador de comandos: linha exata '-- STATEMENT'.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
DELIMITER = "-- STATEMENT"


def split_statements(text: str) -> list[str]:
    chunks, current = [], []
    for line in text.splitlines():
        if line.strip() == DELIMITER:
            chunks.append("\n".join(current))
            current = []
        else:
            current.append(line)
    chunks.append("\n".join(current))
    statements = []
    for chunk in chunks:
        useful = [ln for ln in chunk.splitlines() if ln.strip() and not ln.strip().startswith("--")]
        if useful:
            statements.append(chunk.strip())
    return statements


def apply_migrations(migrator_dsn: str) -> list[tuple[str, str]]:
    applied_now: list[tuple[str, str]] = []
    with psycopg.connect(migrator_dsn, autocommit=True) as conn:
        conn.execute("SET ROLE kael_owner")
        conn.execute("CREATE SCHEMA IF NOT EXISTS kael_meta AUTHORIZATION kael_owner")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS kael_meta.schema_migrations ("
            "filename text PRIMARY KEY, sha256 text NOT NULL, "
            "applied_at timestamptz NOT NULL DEFAULT now())"
        )
        done = {r[0] for r in conn.execute("SELECT filename FROM kael_meta.schema_migrations")}
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in done:
                continue
            text = path.read_text(encoding="utf-8")
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            with conn.transaction():
                for statement in split_statements(text):
                    conn.execute(statement)
                conn.execute(
                    "INSERT INTO kael_meta.schema_migrations (filename, sha256) VALUES (%s, %s)",
                    (path.name, digest),
                )
            applied_now.append((path.name, digest))
    return applied_now
