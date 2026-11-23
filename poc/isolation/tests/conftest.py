"""Fixtures. Os testes de isolamento rodam SEMPRE como kael_app (sem privilegios).
A credencial administrativa so e usada em kael_poc.db.bootstrap, para criar papeis e banco."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from kael_poc import db, migrate
from kael_poc.db import connect
from kael_poc.evidence import write_evidence
from support import build_world


@pytest.fixture(scope="session")
def env():
    admin_dsn, container = db.admin_dsn_from_environment()
    try:
        poc_env = db.bootstrap(admin_dsn)
        poc_env.applied_migrations = migrate.apply_migrations(poc_env.migrator_dsn)
        yield poc_env
    finally:
        if container is not None:
            container.stop()


@pytest.fixture(scope="session")
def world(env):
    return build_world(env)


@pytest.fixture()
def app_conn(env):
    with connect(env.app_dsn) as conn:
        who = conn.execute("SELECT session_user").fetchone()[0]
        assert who == "kael_app", f"os testes devem rodar como kael_app, nao como {who}"
        yield conn


@pytest.fixture(scope="session", autouse=True)
def _write_evidence(env):
    yield
    out_dir = os.environ.get(
        "KAEL_POC_EVIDENCE_DIR", str(Path(__file__).resolve().parent.parent / "evidence")
    )
    with connect(env.app_dsn) as conn:
        write_evidence(conn, env.applied_migrations, out_dir)
