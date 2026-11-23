"""Gera evidencias em Markdown a partir do banco real (como kael_app, sem credencial privilegiada)."""
from __future__ import annotations

from pathlib import Path


def _table(headers, rows) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in row) + " |")
    return "\n".join(out) + "\n"


def write_evidence(app_conn, applied_migrations, out_dir) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    version = app_conn.execute("SELECT version()").fetchone()[0]
    who = app_conn.execute("SELECT session_user, current_user").fetchone()
    (out / "00_ambiente.md").write_text(
        "## Ambiente\n\n"
        f"- PostgreSQL: `{version}`\n"
        f"- Conexao dos testes: session_user=`{who[0]}`, current_user=`{who[1]}`\n",
        encoding="utf-8",
    )

    roles = app_conn.execute(
        "SELECT rolname, rolsuper, rolbypassrls, rolcreatedb, rolcreaterole, rolreplication, "
        "rolcanlogin, rolinherit FROM pg_roles WHERE rolname IN ('kael_owner','kael_migrator','kael_app') "
        "ORDER BY rolname"
    ).fetchall()
    members = app_conn.execute(
        "SELECT r.rolname, m.rolname FROM pg_auth_members am "
        "JOIN pg_roles r ON r.oid = am.roleid JOIN pg_roles m ON m.oid = am.member "
        "WHERE m.rolname IN ('kael_owner','kael_migrator','kael_app') ORDER BY 1, 2"
    ).fetchall()
    (out / "01_papeis.md").write_text(
        "## Papeis do banco\n\n"
        + _table(["papel", "superuser", "bypassrls", "createdb", "createrole", "replication", "login", "inherit"], roles)
        + "\n### Membros (papel concedido, membro)\n\n"
        + _table(["papel", "membro"], members),
        encoding="utf-8",
    )

    privs = app_conn.execute(
        "SELECT table_name, string_agg(privilege_type, ', ' ORDER BY privilege_type) "
        "FROM information_schema.role_table_grants "
        "WHERE grantee = 'kael_app' AND table_schema = 'kael' GROUP BY table_name ORDER BY table_name"
    ).fetchall()
    (out / "02_privilegios_kael_app.md").write_text(
        "## Privilegios de kael_app por tabela\n\n" + _table(["tabela", "privilegios"], privs),
        encoding="utf-8",
    )

    flags = app_conn.execute(
        "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity, pg_get_userbyid(c.relowner) "
        "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'kael' AND c.relkind = 'r' ORDER BY c.relname"
    ).fetchall()
    (out / "03_rls_por_tabela.md").write_text(
        "## RLS por tabela\n\n" + _table(["tabela", "rls habilitado", "rls forcado", "dono"], flags),
        encoding="utf-8",
    )

    pols = app_conn.execute(
        "SELECT tablename, policyname, cmd, roles, qual, with_check FROM pg_policies "
        "WHERE schemaname = 'kael' ORDER BY tablename, cmd, policyname"
    ).fetchall()
    (out / "04_politicas.md").write_text(
        "## Politicas de RLS\n\n"
        + _table(["tabela", "politica", "comando", "papeis", "using", "with check"], pols),
        encoding="utf-8",
    )

    (out / "05_migracoes.md").write_text(
        "## Migracoes aplicadas nesta execucao\n\n"
        + _table(["arquivo", "sha256"], applied_migrations),
        encoding="utf-8",
    )
