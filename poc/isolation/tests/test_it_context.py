"""IT-05, IT-06, revogacao de membership e tentativas de falsificacao de organizacao."""
import random
import uuid
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

import pytest
from psycopg import errors

from kael_poc import backend
from kael_poc.db import connect
from support import ISSUER, count, leftover_org_setting, make_tenant, raw_context


# ---------------- IT-05 ----------------
def test_it05_context_does_not_survive_commit_on_reused_connection(app_conn, world):
    with backend.request_transaction(app_conn, world.a.owner_id, world.a.org_id):
        assert count(app_conn, "files") == len(world.a.file_ids)
    # mesma conexao, nova transacao, sem definir contexto (conexao devolvida ao pool)
    assert count(app_conn, "files") == 0
    assert leftover_org_setting(app_conn) in (None, "")


def test_it05_context_does_not_survive_rollback(app_conn, world):
    with pytest.raises(RuntimeError):
        with backend.request_transaction(app_conn, world.a.owner_id, world.a.org_id):
            assert count(app_conn, "files") == len(world.a.file_ids)
            raise RuntimeError("falha simulada na requisicao")
    assert count(app_conn, "files") == 0
    assert leftover_org_setting(app_conn) in (None, "")


def test_it05_alternating_organizations_on_one_connection(app_conn, world):
    plan = [
        (world.a.owner_id, world.a.org_id, set(world.a.file_ids)),
        (world.b.owner_id, world.b.org_id, set(world.b.file_ids)),
        (world.carol, world.a.org_id, set(world.a.file_ids)),
        (world.carol, world.b.org_id, set(world.b.file_ids)),
        (world.a.owner_id, world.a.org_id, set(world.a.file_ids)),
    ]
    for user, org, expected in plan:
        with backend.request_transaction(app_conn, user, org):
            seen = {r[0] for r in app_conn.execute("SELECT id FROM kael.files")}
        assert seen == expected
        assert leftover_org_setting(app_conn) in (None, "")


def test_it05_control_session_level_setting_would_leak(app_conn, world):
    """CONTROLE NEGATIVO: mostra por que o contexto precisa ser local a transacao.
    Se algum codigo usasse set_config(..., false) (sessao), o contexto vazaria na conexao
    reutilizada. O backend nunca faz isso; este teste documenta o perigo."""
    app_conn.execute("SELECT set_config('app.user_id', %s, false)", (str(world.a.owner_id),))
    app_conn.execute("SELECT set_config('app.org_id', %s, false)", (str(world.a.org_id),))
    leaked = count(app_conn, "files")
    assert leaked == len(world.a.file_ids)


# ---------------- IT-06 ----------------
def test_it06_concurrent_transactions_on_reused_connections_never_leak(env, world):
    pool: Queue = Queue()
    connections = [connect(env.app_dsn) for _ in range(4)]
    for conn in connections:
        pool.put(conn)
    combos = [
        (world.a.owner_id, world.a.org_id, set(world.a.file_ids)),
        (world.b.owner_id, world.b.org_id, set(world.b.file_ids)),
        (world.carol, world.a.org_id, set(world.a.file_ids)),
        (world.carol, world.b.org_id, set(world.b.file_ids)),
    ]
    problems: list = []

    def worker(seed: int) -> None:
        rnd = random.Random(seed)
        for _ in range(60):
            user, org, expected = rnd.choice(combos)
            conn = pool.get()
            try:
                residue = leftover_org_setting(conn)
                if residue not in (None, ""):
                    problems.append(("contexto residual", residue))
                with backend.request_transaction(conn, user, org):
                    seen = {r[0] for r in conn.execute("SELECT id FROM kael.files")}
                if seen != expected:
                    problems.append(("dados inesperados", str(org), len(seen)))
            except Exception as exc:  # qualquer erro tambem reprova
                problems.append(("erro", repr(exc)))
            finally:
                pool.put(conn)

    try:
        with ThreadPoolExecutor(max_workers=12) as pool_executor:
            list(pool_executor.map(worker, range(12)))
    finally:
        for conn in connections:
            conn.close()
    assert not problems, problems[:5]


# ---------------- revogacao de membership ----------------
def _tenant_with_member(conn, role="analyst"):
    tenant = make_tenant(conn, "R", n_files=3, n_datasets=0)
    member = backend.provision_user(conn, ISSUER, f"member-{uuid.uuid4()}")
    backend.add_member(conn, tenant.owner_id, tenant.org_id, member, role)
    return tenant, member


def test_rev_active_member_sees_the_organization_control(app_conn):
    tenant, member = _tenant_with_member(app_conn)
    with backend.request_transaction(app_conn, member, tenant.org_id):
        assert count(app_conn, "files") == 3


@pytest.mark.parametrize("new_status", ["removed", "suspended", "invited"])
def test_rev_backend_rejects_member_whose_membership_is_not_active(app_conn, new_status):
    tenant, member = _tenant_with_member(app_conn)
    assert backend.set_member_status(app_conn, tenant.owner_id, tenant.org_id, member, new_status) == 1
    with pytest.raises(backend.OrgNotAuthorized):
        with backend.request_transaction(app_conn, member, tenant.org_id):
            pass


@pytest.mark.parametrize("new_status", ["removed", "suspended"])
def test_rev_database_denies_forced_context_after_revocation(app_conn, new_status):
    tenant, member = _tenant_with_member(app_conn)
    backend.set_member_status(app_conn, tenant.owner_id, tenant.org_id, member, new_status)
    with raw_context(app_conn, user_id=member, org_id=tenant.org_id):
        assert count(app_conn, "files") == 0
        assert count(app_conn, "datasets") == 0
        assert count(app_conn, "audit_events") == 0
    with pytest.raises(errors.InsufficientPrivilege):
        with raw_context(app_conn, user_id=member, org_id=tenant.org_id):
            app_conn.execute(
                "INSERT INTO kael.files (organization_id, name) VALUES (%s, 'x')", (tenant.org_id,)
            )


def test_rev_revocation_takes_effect_inside_an_open_transaction(env, app_conn):
    tenant, member = _tenant_with_member(app_conn)
    with connect(env.app_dsn) as owner_conn:
        with backend.request_transaction(app_conn, member, tenant.org_id):
            before = count(app_conn, "files")
            backend.set_member_status(owner_conn, tenant.owner_id, tenant.org_id, member, "removed")
            after = count(app_conn, "files")
    assert before == 3
    assert after == 0


# ---------------- falsificacao de organizacao ----------------
def test_forgery_backend_rejects_org_without_membership(app_conn, world):
    with pytest.raises(backend.OrgNotAuthorized):
        with backend.request_transaction(app_conn, world.a.owner_id, world.b.org_id):
            pass


def test_forgery_backend_rejects_unknown_org_id(app_conn, world):
    with pytest.raises(backend.OrgNotAuthorized):
        with backend.request_transaction(app_conn, world.a.owner_id, uuid.uuid4()):
            pass


def test_forgery_backend_requires_explicit_org_when_user_has_several(app_conn, world):
    with pytest.raises(backend.OrgNotAuthorized):
        with backend.request_transaction(app_conn, world.carol):
            pass


def test_forgery_backend_derives_org_when_user_has_exactly_one(app_conn, world):
    with backend.request_transaction(app_conn, world.a.owner_id) as ctx:
        assert ctx.org_id == world.a.org_id


@pytest.mark.parametrize("table", ["files", "datasets", "audit_events"])
def test_forgery_org_context_without_membership_sees_nothing_at_database_level(app_conn, world, table):
    # usuario real (alice) com organizacao B forjada diretamente no SQL
    with raw_context(app_conn, user_id=world.a.owner_id, org_id=world.b.org_id):
        assert count(app_conn, table, world.b.org_id) == 0


def test_forgery_organizations_table_hides_org_without_membership(app_conn, world):
    with raw_context(app_conn, user_id=world.a.owner_id, org_id=world.b.org_id):
        seen = app_conn.execute(
            "SELECT count(*) FROM kael.organizations WHERE id = %s", (world.b.org_id,)
        ).fetchone()[0]
    assert seen == 0


def test_forgery_other_real_user_id_does_not_grant_foreign_org(app_conn, world):
    with raw_context(app_conn, user_id=world.b.owner_id, org_id=world.a.org_id):
        assert count(app_conn, "files", world.a.org_id) == 0


def test_forgery_malformed_context_value_fails_closed(app_conn, world):
    with pytest.raises(errors.InvalidTextRepresentation):
        with raw_context(app_conn, user_id=world.a.owner_id, org_id="' OR 1=1 --"):
            app_conn.execute("SELECT count(*) FROM kael.files")


@pytest.mark.xfail(
    strict=True,
    reason=(
        "LIMITAÇÃO CONHECIDA: quem executa SQL arbitrário como kael_app pode forjar user_id e org_id "
        "juntos. A defesa é a camada de aplicação (consultas parametrizadas, nenhum SQL gerado "
        "por modelo) e o menor privilégio do papel."
    ),
)
def test_limit_sql_level_attacker_forging_user_and_org_context(app_conn, world):
    with raw_context(app_conn, user_id=world.b.owner_id, org_id=world.b.org_id):
        leaked = count(app_conn, "files", world.b.org_id)
    assert leaked == 0
