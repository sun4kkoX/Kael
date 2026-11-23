"""Apoio dos testes: dados sinteticos de duas organizacoes e simulacao de contexto forcado."""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from dataclasses import dataclass

from kael_poc import backend
from kael_poc.db import connect

ISSUER = "https://idp.invalid/realms/poc"


@dataclass
class Tenant:
    org_id: uuid.UUID
    owner_id: uuid.UUID
    file_ids: list
    dataset_ids: list


@dataclass
class World:
    a: Tenant
    b: Tenant
    carol: uuid.UUID  # analyst em A e viewer em B


def make_tenant(conn, label: str, n_files: int = 3, n_datasets: int = 2) -> Tenant:
    owner = backend.provision_user(conn, ISSUER, f"{label}-owner-{uuid.uuid4()}")
    org = backend.create_organization(conn, owner, f"Org {label}")
    files = [
        backend.insert_file(conn, owner, org, f"{label}-file-{i}", size_bytes=100 + i)
        for i in range(n_files)
    ]
    datasets = [
        backend.insert_dataset(conn, owner, org, files[i % n_files], f"{label}-ds-{i}")
        for i in range(n_datasets)
    ]
    backend.write_audit(conn, owner, org, "seed")
    return Tenant(org_id=org, owner_id=owner, file_ids=files, dataset_ids=datasets)


def build_world(env) -> World:
    with connect(env.app_dsn) as conn:
        tenant_a = make_tenant(conn, "A")
        tenant_b = make_tenant(conn, "B")
        carol = backend.provision_user(conn, ISSUER, f"carol-{uuid.uuid4()}")
        backend.add_member(conn, tenant_a.owner_id, tenant_a.org_id, carol, "analyst")
        backend.add_member(conn, tenant_b.owner_id, tenant_b.org_id, carol, "viewer")
    return World(a=tenant_a, b=tenant_b, carol=carol)


@contextmanager
def raw_context(conn, user_id=None, org_id=None):
    """Define o contexto DIRETAMENTE (sem a validacao do backend). Simula codigo com SQL
    arbitrario ou um valor forjado. Local a transacao, como o contexto legitimo."""
    with conn.transaction():
        if user_id is not None:
            conn.execute("SELECT set_config('app.user_id', %s, true)", (str(user_id),))
        if org_id is not None:
            conn.execute("SELECT set_config('app.org_id', %s, true)", (str(org_id),))
        yield


def count(conn, table: str, org_id=None) -> int:
    if org_id is None:
        return conn.execute(f"SELECT count(*) FROM kael.{table}").fetchone()[0]
    return conn.execute(
        f"SELECT count(*) FROM kael.{table} WHERE organization_id = %s", (org_id,)
    ).fetchone()[0]


def leftover_org_setting(conn):
    return conn.execute("SELECT current_setting('app.org_id', true)").fetchone()[0]
