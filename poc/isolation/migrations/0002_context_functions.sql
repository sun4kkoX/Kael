-- 0002: funcoes de contexto. Todas SECURITY INVOKER (nenhuma SECURITY DEFINER).
-- Contexto vazio vira NULL, entao a comparacao falha e nenhuma linha e visivel (falha fechada).
CREATE FUNCTION kael.app_user_id() RETURNS uuid
    LANGUAGE sql STABLE
    AS $$ SELECT NULLIF(current_setting('app.user_id', true), '')::uuid $$;
-- STATEMENT
CREATE FUNCTION kael.app_org_id() RETURNS uuid
    LANGUAGE sql STABLE
    AS $$ SELECT NULLIF(current_setting('app.org_id', true), '')::uuid $$;
-- STATEMENT
-- Defesa em profundidade: alem do contexto, o BANCO confere se o usuario do contexto
-- tem membership ativa na organizacao. Revogar a membership vale na hora.
CREATE FUNCTION kael.app_is_member(org uuid) RETURNS boolean
    LANGUAGE sql STABLE
    AS $$
        SELECT EXISTS (
            SELECT 1
            FROM kael.memberships m
            WHERE m.organization_id = org
              AND m.user_id = kael.app_user_id()
              AND m.status = 'active'
        )
    $$;
