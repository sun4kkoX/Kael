-- 0001: esquema minimo da prova de conceito de isolamento.
-- Executada por kael_migrator com SET ROLE kael_owner (objetos pertencem a kael_owner).
-- Delimitador de comandos: linha exata "-- STATEMENT".
CREATE SCHEMA kael AUTHORIZATION kael_owner;
-- STATEMENT
CREATE TABLE kael.organizations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (length(name) BETWEEN 1 AND 200),
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended')),
    created_at timestamptz NOT NULL DEFAULT now()
);
-- STATEMENT
CREATE TABLE kael.users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    idp_issuer text NOT NULL,
    idp_subject text NOT NULL,
    email text,
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (idp_issuer, idp_subject)
);
-- STATEMENT
CREATE TABLE kael.memberships (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES kael.organizations (id),
    user_id uuid NOT NULL REFERENCES kael.users (id),
    role text NOT NULL CHECK (role IN ('owner', 'admin', 'analyst', 'viewer', 'auditor')),
    status text NOT NULL CHECK (status IN ('invited', 'active', 'suspended', 'removed')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, user_id)
);
-- STATEMENT
CREATE INDEX memberships_user_idx ON kael.memberships (user_id, status);
-- STATEMENT
CREATE TABLE kael.files (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES kael.organizations (id),
    uploaded_by uuid REFERENCES kael.users (id),
    name text NOT NULL,
    size_bytes bigint NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, id)
);
-- STATEMENT
CREATE INDEX files_org_idx ON kael.files (organization_id);
-- STATEMENT
CREATE TABLE kael.datasets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES kael.organizations (id),
    file_id uuid NOT NULL,
    name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (organization_id, file_id) REFERENCES kael.files (organization_id, id)
);
-- STATEMENT
CREATE INDEX datasets_org_idx ON kael.datasets (organization_id);
-- STATEMENT
CREATE TABLE kael.audit_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES kael.organizations (id),
    actor_user_id uuid REFERENCES kael.users (id),
    action text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
-- STATEMENT
CREATE INDEX audit_events_org_idx ON kael.audit_events (organization_id);
