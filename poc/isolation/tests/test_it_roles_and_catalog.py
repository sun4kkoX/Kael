"""IT-07, IT-08, IT-09 e IT-11: papeis, catalogo e auditoria append-only."""
import pytest
from psycopg import errors

from kael_poc import backend
from kael_poc.catalog_checks import find_rls_violations
from kael_poc.db import connect
from support import count

ROLES = ["kael_owner", "kael_migrator", "kael_app"]


# ---------------- IT-07 ----------------
def test_it07_role_attributes_have_no_dangerous_privileges(app_conn):
    rows = app_conn.execute(
        "SELECT rolname, rolsuper, rolbypassrls, rolcreatedb, rolcreaterole, rolreplication, "
        "rolcanlogin FROM pg_roles WHERE rolname = ANY(%s)",
        (ROLES,),
    ).fetchall()
    by_name = {r[0]: r for r in rows}
    assert set(by_name) == set(ROLES)
    for name, sup, bypass, createdb, createrole, repl, login in rows:
        assert not sup, f"{name} nao pode ser superuser"
        assert not bypass, f"{name} nao pode ter bypass de RLS"
        assert not createdb and not createrole and not repl, f"{name} com privilegio extra"
    assert by_name["kael_app"][6] is True
    assert by_name["kael_owner"][6] is False  # dono nao faz login


def test_it07_app_role_is_not_member_of_any_role(app_conn):
    members = app_conn.execute(
        "SELECT r.rolname FROM pg_auth_members am "
        "JOIN pg_roles r ON r.oid = am.roleid JOIN pg_roles m ON m.oid = am.member "
        "WHERE m.rolname = 'kael_app'"
    ).fetchall()
    assert members == []


def test_it07_owner_migrator_and_app_are_separate(app_conn):
    migrator_of = {
        r[0]
        for r in app_conn.execute(
            "SELECT r.rolname FROM pg_auth_members am "
            "JOIN pg_roles r ON r.oid = am.roleid JOIN pg_roles m ON m.oid = am.member "
            "WHERE m.rolname = 'kael_migrator'"
        )
    }
    assert migrator_of == {"kael_owner"}
    owners = {
        r[0]
        for r in app_conn.execute(
            "SELECT pg_get_userbyid(c.relowner) FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'kael' AND c.relkind IN ('r', 'S', 'i')"
        )
    }
    assert owners == {"kael_owner"}


def test_it07_app_role_owns_nothing(app_conn):
    owned = app_conn.execute(
        "SELECT count(*) FROM pg_class WHERE relowner = (SELECT oid FROM pg_roles WHERE rolname = 'kael_app')"
    ).fetchone()[0]
    assert owned == 0


@pytest.mark.parametrize(
    "statement",
    [
        "CREATE TABLE kael.evil (id int)",
        "CREATE TABLE public.evil (id int)",
        "ALTER TABLE kael.files DISABLE ROW LEVEL SECURITY",
        "ALTER TABLE kael.files NO FORCE ROW LEVEL SECURITY",
        "DROP POLICY files_select ON kael.files",
        "DROP TABLE kael.files",
        "SET ROLE kael_owner",
        "SET ROLE postgres",
        "SET SESSION AUTHORIZATION postgres",
        "CREATE ROLE evil_role SUPERUSER",
    ],
)
def test_it07_app_role_cannot_perform_privileged_operations(app_conn, statement):
    with pytest.raises(errors.InsufficientPrivilege):
        app_conn.execute(statement)


def test_it07_app_role_cannot_disable_row_security(app_conn, world):
    app_conn.execute("SET row_security = off")
    with pytest.raises(errors.InsufficientPrivilege):
        app_conn.execute("SELECT count(*) FROM kael.files")


# ---------------- IT-08 ----------------
def test_it08_expected_tables_are_scanned(app_conn):
    tables = {
        r[0]
        for r in app_conn.execute(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'kael' AND c.relkind = 'r'"
        )
    }
    assert {"organizations", "users", "memberships", "files", "datasets", "audit_events"} <= tables


def test_it08_every_table_has_forced_rls_and_explicit_policies(app_conn):
    assert find_rls_violations(app_conn) == []


class _Rollback(Exception):
    pass


def test_it08_detection_logic_catches_an_unprotected_table(env):
    """Controle negativo: prova que o detector nao e cego. Usa kael_migrator (DDL) somente
    para criar, dentro de uma transacao descartada, uma tabela sem protecao."""
    violations = []
    with connect(env.migrator_dsn) as conn:
        conn.execute("SET ROLE kael_owner")
        try:
            with conn.transaction():
                conn.execute("CREATE TABLE kael.bad_table (id uuid, organization_id uuid)")
                conn.execute("GRANT SELECT, INSERT ON kael.bad_table TO kael_app")
                violations = find_rls_violations(conn)
                raise _Rollback()
        except _Rollback:
            pass
    assert any("bad_table" in v for v in violations), violations


# ---------------- IT-09 ----------------
def test_it09_no_security_definer_functions_outside_allowlist(app_conn):
    allowlist = set()  # a prova de conceito nao admite nenhuma
    found = {
        (r[0], r[1])
        for r in app_conn.execute(
            "SELECT n.nspname, p.proname FROM pg_proc p "
            "JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE p.prosecdef AND n.nspname NOT IN ('pg_catalog', 'information_schema')"
        )
    }
    assert found == allowlist


def test_it09_context_functions_exist_and_are_owned_by_owner(app_conn):
    rows = app_conn.execute(
        "SELECT p.proname, pg_get_userbyid(p.proowner) FROM pg_proc p "
        "JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = 'kael'"
    ).fetchall()
    assert {r[0] for r in rows} == {"app_user_id", "app_org_id", "app_is_member"}
    assert {r[1] for r in rows} == {"kael_owner"}


# ---------------- IT-11 ----------------
def test_it11_audit_events_accept_insert_and_select(app_conn, world):
    with backend.request_transaction(app_conn, world.a.owner_id, world.a.org_id):
        app_conn.execute(
            "INSERT INTO kael.audit_events (organization_id, actor_user_id, action) "
            "VALUES (%s, %s, 'it11')",
            (world.a.org_id, world.a.owner_id),
        )
        seen = app_conn.execute(
            "SELECT count(*) FROM kael.audit_events WHERE action = 'it11'"
        ).fetchone()[0]
    assert seen >= 1


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE kael.audit_events SET action = 'adulterado'",
        "DELETE FROM kael.audit_events",
        "TRUNCATE kael.audit_events",
    ],
)
def test_it11_audit_events_are_append_only(app_conn, world, statement):
    with pytest.raises(errors.InsufficientPrivilege):
        with backend.request_transaction(app_conn, world.a.owner_id, world.a.org_id):
            app_conn.execute(statement)
    with backend.request_transaction(app_conn, world.a.owner_id, world.a.org_id):
        assert count(app_conn, "audit_events", world.a.org_id) >= 1  # nada foi apagado
