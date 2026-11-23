"""Camada 'backend' minima da prova de conceito: valida a membership e define o contexto.

Regras demonstradas:
- o contexto (app.user_id, app.org_id) e definido SOMENTE aqui, por parametro, com
  set_config(..., true), isto e, local a transacao (nunca sessao);
- a organizacao pedida pelo cliente so vale se existir membership ativa verificada no banco.
Nao ha funcionalidades de negocio: apenas operacoes necessarias para montar dados de teste.
"""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from dataclasses import dataclass


class OrgNotAuthorized(Exception):
    """Organizacao inexistente, sem membership ativa ou ambigua."""


@dataclass(frozen=True)
class RequestContext:
    user_id: uuid.UUID
    org_id: uuid.UUID
    role: str


def _set_local(conn, name: str, value) -> None:
    conn.execute("SELECT set_config(%s, %s, true)", (name, str(value)))


@contextmanager
def user_transaction(conn, user_id):
    """Transacao com apenas o usuario definido (login, provisionamento, criacao de organizacao)."""
    with conn.transaction():
        _set_local(conn, "app.user_id", user_id)
        yield


@contextmanager
def request_transaction(conn, user_id, requested_org_id=None):
    """Transacao de uma requisicao: valida a membership e so entao define a organizacao."""
    with conn.transaction():
        _set_local(conn, "app.user_id", user_id)
        rows = conn.execute(
            "SELECT organization_id, role FROM kael.memberships "
            "WHERE user_id = %s AND status = 'active'",
            (user_id,),
        ).fetchall()
        roles = {row[0]: row[1] for row in rows}
        if requested_org_id is not None:
            requested = uuid.UUID(str(requested_org_id))
            if requested not in roles:
                raise OrgNotAuthorized("sem membership ativa na organizacao pedida")
            org_id = requested
        elif len(roles) == 1:
            (org_id,) = roles
        else:
            raise OrgNotAuthorized("organizacao obrigatoria quando ha zero ou varias memberships")
        _set_local(conn, "app.org_id", org_id)
        yield RequestContext(user_id=user_id, org_id=org_id, role=roles[org_id])


# ---------- operacoes minimas para montar dados de teste ----------

def provision_user(conn, issuer: str, subject: str, email: str | None = None) -> uuid.UUID:
    user_id = uuid.uuid4()
    with user_transaction(conn, user_id):
        conn.execute(
            "INSERT INTO kael.users (id, idp_issuer, idp_subject, email) VALUES (%s, %s, %s, %s)",
            (user_id, issuer, subject, email),
        )
    return user_id


def create_organization(conn, owner_id, name: str) -> uuid.UUID:
    org_id = uuid.uuid4()  # gerado no backend: INSERT ... RETURNING exigiria visibilidade previa
    with user_transaction(conn, owner_id):
        conn.execute("INSERT INTO kael.organizations (id, name) VALUES (%s, %s)", (org_id, name))
        _set_local(conn, "app.org_id", org_id)
        conn.execute(
            "INSERT INTO kael.memberships (organization_id, user_id, role, status) "
            "VALUES (%s, %s, 'owner', 'active')",
            (org_id, owner_id),
        )
    return org_id


def add_member(conn, actor_id, org_id, user_id, role: str, status: str = "active") -> None:
    with request_transaction(conn, actor_id, org_id) as ctx:
        conn.execute(
            "INSERT INTO kael.memberships (organization_id, user_id, role, status) "
            "VALUES (%s, %s, %s, %s)",
            (ctx.org_id, user_id, role, status),
        )


def set_member_status(conn, actor_id, org_id, user_id, status: str) -> int:
    with request_transaction(conn, actor_id, org_id) as ctx:
        cur = conn.execute(
            "UPDATE kael.memberships SET status = %s WHERE organization_id = %s AND user_id = %s",
            (status, ctx.org_id, user_id),
        )
        return cur.rowcount


def insert_file(conn, actor_id, org_id, name: str, size_bytes: int = 0) -> uuid.UUID:
    file_id = uuid.uuid4()
    with request_transaction(conn, actor_id, org_id) as ctx:
        conn.execute(
            "INSERT INTO kael.files (id, organization_id, uploaded_by, name, size_bytes) "
            "VALUES (%s, %s, %s, %s, %s)",
            (file_id, ctx.org_id, actor_id, name, size_bytes),
        )
    return file_id


def insert_dataset(conn, actor_id, org_id, file_id, name: str) -> uuid.UUID:
    dataset_id = uuid.uuid4()
    with request_transaction(conn, actor_id, org_id) as ctx:
        conn.execute(
            "INSERT INTO kael.datasets (id, organization_id, file_id, name) VALUES (%s, %s, %s, %s)",
            (dataset_id, ctx.org_id, file_id, name),
        )
    return dataset_id


def write_audit(conn, actor_id, org_id, action: str) -> None:
    with request_transaction(conn, actor_id, org_id) as ctx:
        conn.execute(
            "INSERT INTO kael.audit_events (organization_id, actor_user_id, action) "
            "VALUES (%s, %s, %s)",
            (ctx.org_id, actor_id, action),
        )
