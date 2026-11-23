"""IT-01, IT-02, IT-03, IT-04 e IT-10: SELECT, INSERT, UPDATE, DELETE e lote, como kael_app."""
import uuid

import pytest
from psycopg import errors

from kael_poc import backend
from support import count, make_tenant, raw_context

TENANT_TABLES = ["files", "datasets", "audit_events", "memberships"]


# ---------------- IT-01 ----------------
@pytest.mark.parametrize("table", TENANT_TABLES)
def test_it01_select_other_org_returns_nothing(app_conn, world, table):
    with backend.request_transaction(app_conn, world.a.owner_id, world.a.org_id):
        foreign = count(app_conn, table, world.b.org_id)
        own = count(app_conn, table, world.a.org_id)
    assert foreign == 0
    assert own > 0  # controle positivo: a propria organizacao continua visivel


@pytest.mark.parametrize("table", ["files", "datasets", "memberships"])
def test_it01_update_and_delete_other_org_affect_nothing(app_conn, world, table):
    with backend.request_transaction(app_conn, world.a.owner_id, world.a.org_id):
        upd = app_conn.execute(
            f"UPDATE kael.{table} SET created_at = created_at WHERE organization_id = %s",
            (world.b.org_id,),
        ).rowcount
        dele = app_conn.execute(
            f"DELETE FROM kael.{table} WHERE organization_id = %s", (world.b.org_id,)
        ).rowcount
    assert upd == 0 and dele == 0
    with backend.request_transaction(app_conn, world.b.owner_id, world.b.org_id):
        remaining = count(app_conn, table, world.b.org_id)
    expected = {"files": 3, "datasets": 2, "memberships": 2}[table]
    assert remaining == expected  # dados da organizacao B intactos


def test_it01_organizations_and_users_are_scoped(app_conn, world):
    with backend.request_transaction(app_conn, world.a.owner_id, world.a.org_id):
        orgs = {r[0] for r in app_conn.execute("SELECT id FROM kael.organizations")}
        users = {r[0] for r in app_conn.execute("SELECT id FROM kael.users")}
    assert orgs == {world.a.org_id}
    assert users == {world.a.owner_id}


def test_it01_organizations_cannot_be_deleted_by_the_app(app_conn, world):
    with pytest.raises(errors.InsufficientPrivilege):
        with backend.request_transaction(app_conn, world.a.owner_id, world.a.org_id):
            app_conn.execute("DELETE FROM kael.organizations WHERE id = %s", (world.a.org_id,))


def test_it01_bulk_update_and_delete_without_where_stay_in_own_org(app_conn):
    tenant_c = make_tenant(app_conn, "C", n_files=3, n_datasets=0)
    tenant_d = make_tenant(app_conn, "D", n_files=4, n_datasets=0)
    with backend.request_transaction(app_conn, tenant_c.owner_id, tenant_c.org_id):
        updated = app_conn.execute("UPDATE kael.files SET size_bytes = size_bytes + 1").rowcount
    assert updated == 3
    with backend.request_transaction(app_conn, tenant_d.owner_id, tenant_d.org_id):
        sizes = sorted(r[0] for r in app_conn.execute("SELECT size_bytes FROM kael.files"))
    assert sizes == [100, 101, 102, 103]  # D nao foi tocada
    with backend.request_transaction(app_conn, tenant_c.owner_id, tenant_c.org_id):
        deleted = app_conn.execute("DELETE FROM kael.files WHERE true").rowcount
    assert deleted == 3
    with backend.request_transaction(app_conn, tenant_d.owner_id, tenant_d.org_id):
        assert count(app_conn, "files") == 4


def test_it01_same_user_in_two_orgs_sees_only_the_requested_org(app_conn, world):
    with backend.request_transaction(app_conn, world.carol, world.a.org_id):
        ids_a = {r[0] for r in app_conn.execute("SELECT id FROM kael.files")}
    with backend.request_transaction(app_conn, world.carol, world.b.org_id):
        ids_b = {r[0] for r in app_conn.execute("SELECT id FROM kael.files")}
    assert ids_a == set(world.a.file_ids)
    assert ids_b == set(world.b.file_ids)


# ---------------- IT-02 ----------------
def _foreign_insert(world, table):
    other = world.b.org_id
    return {
        "files": ("INSERT INTO kael.files (organization_id, name) VALUES (%s, 'x')", (other,)),
        "datasets": (
            "INSERT INTO kael.datasets (organization_id, file_id, name) VALUES (%s, %s, 'x')",
            (other, world.b.file_ids[0]),
        ),
        "audit_events": (
            "INSERT INTO kael.audit_events (organization_id, actor_user_id, action) VALUES (%s, %s, 'x')",
            (other, world.a.owner_id),
        ),
        "memberships": (
            "INSERT INTO kael.memberships (organization_id, user_id, role, status) "
            "VALUES (%s, %s, 'viewer', 'active')",
            (other, world.a.owner_id),
        ),
    }[table]


@pytest.mark.parametrize("table", TENANT_TABLES)
def test_it02_insert_with_other_org_id_is_rejected(app_conn, world, table):
    statement, params = _foreign_insert(world, table)
    with pytest.raises(errors.InsufficientPrivilege):
        with backend.request_transaction(app_conn, world.a.owner_id, world.a.org_id):
            app_conn.execute(statement, params)


def test_it02_executemany_with_one_foreign_row_aborts_everything(app_conn, world):
    marker = f"batch-{uuid.uuid4()}"
    rows = [(world.a.org_id, marker), (world.a.org_id, marker), (world.b.org_id, marker)]
    with pytest.raises(errors.InsufficientPrivilege):
        with backend.request_transaction(app_conn, world.a.owner_id, world.a.org_id):
            app_conn.cursor().executemany(
                "INSERT INTO kael.files (organization_id, name) VALUES (%s, %s)", rows
            )
    with backend.request_transaction(app_conn, world.a.owner_id, world.a.org_id):
        leftover = app_conn.execute(
            "SELECT count(*) FROM kael.files WHERE name = %s", (marker,)
        ).fetchone()[0]
    assert leftover == 0  # nada do lote foi gravado


def test_it02_insert_select_into_other_org_is_rejected(app_conn, world):
    with pytest.raises(errors.InsufficientPrivilege):
        with backend.request_transaction(app_conn, world.a.owner_id, world.a.org_id):
            app_conn.execute(
                "INSERT INTO kael.files (organization_id, name) "
                "SELECT %s, name FROM kael.files WHERE organization_id = %s",
                (world.b.org_id, world.a.org_id),
            )


# ---------------- IT-03 ----------------
def test_it03_cross_org_reference_is_rejected_by_composite_fk(app_conn, world):
    with pytest.raises(errors.ForeignKeyViolation):
        with backend.request_transaction(app_conn, world.a.owner_id, world.a.org_id):
            app_conn.execute(
                "INSERT INTO kael.datasets (organization_id, file_id, name) VALUES (%s, %s, 'x')",
                (world.a.org_id, world.b.file_ids[0]),
            )


def test_it03_same_org_reference_is_accepted_control(app_conn):
    tenant = make_tenant(app_conn, "E", n_files=1, n_datasets=1)
    with backend.request_transaction(app_conn, tenant.owner_id, tenant.org_id):
        assert count(app_conn, "datasets", tenant.org_id) == 1


# ---------------- IT-04 ----------------
@pytest.mark.parametrize("table", TENANT_TABLES + ["organizations", "users"])
def test_it04_no_context_sees_nothing(app_conn, world, table):
    assert count(app_conn, table) == 0


def test_it04_user_only_context_sees_no_business_rows(app_conn, world):
    with backend.user_transaction(app_conn, world.a.owner_id):
        for table in ["files", "datasets", "audit_events", "organizations"]:
            assert count(app_conn, table) == 0
        assert count(app_conn, "memberships") > 0  # as proprias memberships sao visiveis


def test_it04_no_context_insert_is_rejected(app_conn, world):
    with pytest.raises(errors.InsufficientPrivilege):
        app_conn.execute(
            "INSERT INTO kael.files (organization_id, name) VALUES (%s, 'x')", (world.a.org_id,)
        )


# ---------------- IT-10 ----------------
@pytest.mark.parametrize("table", ["files", "datasets", "memberships"])
def test_it10_cannot_move_own_rows_to_another_org(app_conn, world, table):
    with pytest.raises(errors.InsufficientPrivilege):
        with backend.request_transaction(app_conn, world.a.owner_id, world.a.org_id):
            app_conn.execute(
                f"UPDATE kael.{table} SET organization_id = %s WHERE organization_id = %s",
                (world.b.org_id, world.a.org_id),
            )
    with backend.request_transaction(app_conn, world.a.owner_id, world.a.org_id):
        assert count(app_conn, table, world.a.org_id) > 0  # continuam em A


@pytest.mark.parametrize("table", ["files", "datasets"])
def test_it10_cannot_pull_rows_of_another_org_into_own_org(app_conn, world, table):
    with backend.request_transaction(app_conn, world.b.owner_id, world.b.org_id):
        stolen = app_conn.execute(
            f"UPDATE kael.{table} SET organization_id = %s WHERE organization_id = %s",
            (world.b.org_id, world.a.org_id),
        ).rowcount
    assert stolen == 0
