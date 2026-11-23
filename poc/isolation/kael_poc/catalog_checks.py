"""Verificacoes de catalogo reutilizaveis (IT-08) e para evidencias."""
from __future__ import annotations

COMMANDS = ("SELECT", "INSERT", "UPDATE", "DELETE")


def find_rls_violations(conn, schema: str = "kael", app_role: str = "kael_app") -> list[str]:
    """Invariantes (qualquer violacao reprova):
    1. toda tabela do esquema tem RLS habilitado e forcado;
    2. nenhuma politica FOR ALL (comandos separados) e nenhuma politica para PUBLIC;
    3. todo privilegio de DML concedido ao papel da aplicacao tem politica do mesmo comando;
    4. toda tabela com organization_id tem politica de SELECT.
    Como a regra 3 e geral, uma tabela nova esquecida sem politica e detectada."""
    violations: list[str] = []
    tables = conn.execute(
        "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity "
        "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = %s AND c.relkind IN ('r', 'p') ORDER BY c.relname",
        (schema,),
    ).fetchall()
    for name, rls_on, rls_forced in tables:
        if not rls_on:
            violations.append(f"{name}: RLS nao habilitado")
        if not rls_forced:
            violations.append(f"{name}: RLS nao forcado")
        pol_rows = conn.execute(
            "SELECT cmd, roles FROM pg_policies WHERE schemaname = %s AND tablename = %s",
            (schema, name),
        ).fetchall()
        cmds = [r[0] for r in pol_rows]
        if "ALL" in cmds:
            violations.append(f"{name}: politica FOR ALL proibida (usar comandos separados)")
        for _, roles in pol_rows:
            if "public" in [str(x).lower() for x in roles]:
                violations.append(f"{name}: politica aplicavel a PUBLIC")
        qualified = f"{schema}.{name}"
        for cmd in COMMANDS:
            granted = conn.execute(
                "SELECT has_table_privilege(%s, %s, %s)", (app_role, qualified, cmd)
            ).fetchone()[0]
            if granted and cmd not in cmds:
                violations.append(f"{name}: privilegio {cmd} concedido sem politica {cmd}")
        has_org = conn.execute(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = %s AND column_name = 'organization_id')",
            (schema, name),
        ).fetchone()[0]
        if has_org and "SELECT" not in cmds:
            violations.append(f"{name}: tem organization_id mas nao tem politica de SELECT")
    return violations
