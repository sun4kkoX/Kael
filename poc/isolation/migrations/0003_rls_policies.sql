-- 0003: RLS habilitado e FORCADO em todas as tabelas, com politicas separadas por comando.
-- Nenhuma politica FOR ALL. Todas as politicas valem somente para kael_app.

-- ---------- organizations ----------
ALTER TABLE kael.organizations ENABLE ROW LEVEL SECURITY;
-- STATEMENT
ALTER TABLE kael.organizations FORCE ROW LEVEL SECURITY;
-- STATEMENT
CREATE POLICY organizations_select ON kael.organizations FOR SELECT TO kael_app
    USING (id = kael.app_org_id() AND kael.app_is_member(id));
-- STATEMENT
CREATE POLICY organizations_insert ON kael.organizations FOR INSERT TO kael_app
    WITH CHECK (kael.app_user_id() IS NOT NULL);
-- STATEMENT
CREATE POLICY organizations_update ON kael.organizations FOR UPDATE TO kael_app
    USING (id = kael.app_org_id() AND kael.app_is_member(id))
    WITH CHECK (id = kael.app_org_id() AND kael.app_is_member(id));

-- ---------- users (cada usuario so enxerga e cria a si mesmo) ----------
-- STATEMENT
ALTER TABLE kael.users ENABLE ROW LEVEL SECURITY;
-- STATEMENT
ALTER TABLE kael.users FORCE ROW LEVEL SECURITY;
-- STATEMENT
CREATE POLICY users_select ON kael.users FOR SELECT TO kael_app
    USING (id = kael.app_user_id());
-- STATEMENT
CREATE POLICY users_insert ON kael.users FOR INSERT TO kael_app
    WITH CHECK (id = kael.app_user_id());
-- STATEMENT
CREATE POLICY users_update ON kael.users FOR UPDATE TO kael_app
    USING (id = kael.app_user_id())
    WITH CHECK (id = kael.app_user_id());

-- ---------- memberships ----------
-- A leitura das proprias memberships precisa funcionar ANTES de a organizacao estar
-- definida (o backend usa isso para validar a organizacao). Nao ha checagem de membership
-- aqui porque ela consultaria a propria tabela (recursao de politica).
-- STATEMENT
ALTER TABLE kael.memberships ENABLE ROW LEVEL SECURITY;
-- STATEMENT
ALTER TABLE kael.memberships FORCE ROW LEVEL SECURITY;
-- STATEMENT
CREATE POLICY memberships_select ON kael.memberships FOR SELECT TO kael_app
    USING (user_id = kael.app_user_id() OR organization_id = kael.app_org_id());
-- STATEMENT
CREATE POLICY memberships_insert ON kael.memberships FOR INSERT TO kael_app
    WITH CHECK (organization_id = kael.app_org_id());
-- STATEMENT
CREATE POLICY memberships_update ON kael.memberships FOR UPDATE TO kael_app
    USING (organization_id = kael.app_org_id())
    WITH CHECK (organization_id = kael.app_org_id());
-- STATEMENT
CREATE POLICY memberships_delete ON kael.memberships FOR DELETE TO kael_app
    USING (organization_id = kael.app_org_id());

-- ---------- files ----------
-- STATEMENT
ALTER TABLE kael.files ENABLE ROW LEVEL SECURITY;
-- STATEMENT
ALTER TABLE kael.files FORCE ROW LEVEL SECURITY;
-- STATEMENT
CREATE POLICY files_select ON kael.files FOR SELECT TO kael_app
    USING (organization_id = kael.app_org_id() AND kael.app_is_member(organization_id));
-- STATEMENT
CREATE POLICY files_insert ON kael.files FOR INSERT TO kael_app
    WITH CHECK (organization_id = kael.app_org_id() AND kael.app_is_member(organization_id));
-- STATEMENT
CREATE POLICY files_update ON kael.files FOR UPDATE TO kael_app
    USING (organization_id = kael.app_org_id() AND kael.app_is_member(organization_id))
    WITH CHECK (organization_id = kael.app_org_id() AND kael.app_is_member(organization_id));
-- STATEMENT
CREATE POLICY files_delete ON kael.files FOR DELETE TO kael_app
    USING (organization_id = kael.app_org_id() AND kael.app_is_member(organization_id));

-- ---------- datasets ----------
-- STATEMENT
ALTER TABLE kael.datasets ENABLE ROW LEVEL SECURITY;
-- STATEMENT
ALTER TABLE kael.datasets FORCE ROW LEVEL SECURITY;
-- STATEMENT
CREATE POLICY datasets_select ON kael.datasets FOR SELECT TO kael_app
    USING (organization_id = kael.app_org_id() AND kael.app_is_member(organization_id));
-- STATEMENT
CREATE POLICY datasets_insert ON kael.datasets FOR INSERT TO kael_app
    WITH CHECK (organization_id = kael.app_org_id() AND kael.app_is_member(organization_id));
-- STATEMENT
CREATE POLICY datasets_update ON kael.datasets FOR UPDATE TO kael_app
    USING (organization_id = kael.app_org_id() AND kael.app_is_member(organization_id))
    WITH CHECK (organization_id = kael.app_org_id() AND kael.app_is_member(organization_id));
-- STATEMENT
CREATE POLICY datasets_delete ON kael.datasets FOR DELETE TO kael_app
    USING (organization_id = kael.app_org_id() AND kael.app_is_member(organization_id));

-- ---------- audit_events (somente leitura e insercao) ----------
-- STATEMENT
ALTER TABLE kael.audit_events ENABLE ROW LEVEL SECURITY;
-- STATEMENT
ALTER TABLE kael.audit_events FORCE ROW LEVEL SECURITY;
-- STATEMENT
CREATE POLICY audit_events_select ON kael.audit_events FOR SELECT TO kael_app
    USING (organization_id = kael.app_org_id() AND kael.app_is_member(organization_id));
-- STATEMENT
CREATE POLICY audit_events_insert ON kael.audit_events FOR INSERT TO kael_app
    WITH CHECK (organization_id = kael.app_org_id() AND kael.app_is_member(organization_id));
