-- 0004: privilegios minimos para kael_app. Sem DELETE em organizations e users,
-- e audit_events apenas com SELECT e INSERT (append-only).
REVOKE ALL ON SCHEMA kael FROM PUBLIC;
-- STATEMENT
GRANT USAGE ON SCHEMA kael TO kael_app;
-- STATEMENT
GRANT SELECT, INSERT, UPDATE ON kael.organizations TO kael_app;
-- STATEMENT
GRANT SELECT, INSERT, UPDATE ON kael.users TO kael_app;
-- STATEMENT
GRANT SELECT, INSERT, UPDATE, DELETE ON kael.memberships TO kael_app;
-- STATEMENT
GRANT SELECT, INSERT, UPDATE, DELETE ON kael.files TO kael_app;
-- STATEMENT
GRANT SELECT, INSERT, UPDATE, DELETE ON kael.datasets TO kael_app;
-- STATEMENT
GRANT SELECT, INSERT ON kael.audit_events TO kael_app;
-- STATEMENT
REVOKE ALL ON FUNCTION kael.app_user_id() FROM PUBLIC;
-- STATEMENT
REVOKE ALL ON FUNCTION kael.app_org_id() FROM PUBLIC;
-- STATEMENT
REVOKE ALL ON FUNCTION kael.app_is_member(uuid) FROM PUBLIC;
-- STATEMENT
GRANT EXECUTE ON FUNCTION kael.app_user_id() TO kael_app;
-- STATEMENT
GRANT EXECUTE ON FUNCTION kael.app_org_id() TO kael_app;
-- STATEMENT
GRANT EXECUTE ON FUNCTION kael.app_is_member(uuid) TO kael_app;
