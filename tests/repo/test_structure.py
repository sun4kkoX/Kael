"""Testes da Fase 0: validam estrutura, estado das ADRs e regras básicas de segredos.
Não testam funcionalidades de negócio (não existem nesta fase)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "README.md",
    "Makefile",
    ".gitignore",
    ".env.example",
    "docs/ARCHITECTURE.md",
    "docs/SECURITY.md",
    "docs/THREAT_MODEL.md",
    "docs/IDENTITY_AND_ISOLATION.md",
    "docs/DATA_MODEL.md",
    "docs/ISOLATION_TEST_PLAN.md",
    "docs/DECISION_IMPACT_PD16_20.md",
    "docs/POC_ISOLATION.md",
    ".github/workflows/isolation-poc.yml",
    "poc/isolation/README.md",
    "poc/isolation/pyproject.toml",
    "poc/isolation/requirements.txt",
    "poc/isolation/kael_poc/db.py",
    "poc/isolation/kael_poc/migrate.py",
    "poc/isolation/kael_poc/backend.py",
    "poc/isolation/kael_poc/catalog_checks.py",
    "poc/isolation/kael_poc/evidence.py",
    "poc/isolation/kael_poc/report.py",
    "poc/isolation/migrations/0001_schema.sql",
    "poc/isolation/migrations/0002_context_functions.sql",
    "poc/isolation/migrations/0003_rls_policies.sql",
    "poc/isolation/migrations/0004_grants.sql",
    "poc/isolation/tests/conftest.py",
    "poc/isolation/tests/support.py",
    "poc/isolation/tests/test_it_isolation_dml.py",
    "poc/isolation/tests/test_it_roles_and_catalog.py",
    "poc/isolation/tests/test_it_context.py",
    "docs/RISKS_AND_DECISIONS.md",
    "docs/DEVELOPMENT.md",
    "docs/ADR/README.md",
    "docs/ADR/ADR-001-database-decision.md",
    "docs/ADR/ADR-002-hybrid-deployment.md",
    "infra/compose/docker-compose.dev.yml",
    ".github/workflows/ci.yml",
    ".github/pull_request_template.md",
]
REQUIRED_DIRS = ["apps/api", "apps/worker", "apps/web", "infra", "docs/ADR", "tests/repo"]


def test_required_files_exist():
    missing = [f for f in REQUIRED_FILES if not (ROOT / f).is_file()]
    assert not missing, f"Arquivos ausentes: {missing}"


def test_required_dirs_exist():
    missing = [d for d in REQUIRED_DIRS if not (ROOT / d).is_dir()]
    assert not missing, f"Diretórios ausentes: {missing}"


def test_adrs_are_proposed_not_accepted():
    for adr in (ROOT / "docs/ADR").glob("ADR-*.md"):
        text = adr.read_text(encoding="utf-8")
        status = re.search(r"\*\*Status:\*\*\s*(.+)", text)
        assert status, f"{adr.name}: linha de status ausente"
        assert "Proposto" in status.group(1), f"{adr.name}: deve estar Proposto até aprovação formal"
        assert "Aceito" not in status.group(1), f"{adr.name}: não pode constar como Aceito"


def test_no_env_files_in_repo():
    forbidden = [p for p in ROOT.glob("**/.env*") if p.name != ".env.example" and ".git" not in p.parts]
    assert not forbidden, f"Arquivos .env presentes: {forbidden}"


def test_gitignore_blocks_secrets():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in text and "*.pem" in text and "*.key" in text


def test_env_example_has_no_values():
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            key, _, value = line.partition("=")
            assert value == "", f".env.example não pode ter valor: {key}"


def test_compose_has_no_literal_secrets_and_binds_localhost():
    lines = (ROOT / "infra/compose/docker-compose.dev.yml").read_text(encoding="utf-8").splitlines()
    for line in lines:
        if line.strip().startswith("#"):
            continue
        if "PASSWORD" in line and ":" in line:
            assert "${" in line or "$$" in line, f"Possível segredo literal: {line.strip()}"
        if re.match(r'\s*-\s*"\d+:\d+"', line) or re.match(r'\s*-\s*"[\d.]*:?\d+:\d+"', line):
            assert "127.0.0.1" in line, f"Porta exposta fora de localhost: {line.strip()}"
        assert ":latest" not in line, f"Tag latest proibida: {line.strip()}"


def test_threat_model_has_core_sections_and_critical_threats():
    text = (ROOT / "docs/THREAT_MODEL.md").read_text(encoding="utf-8")
    for section in ["## 1. Ativos", "## 2. Atores", "## 3. Fronteiras de confiança", "## 4. Ameaças"]:
        assert section in text, f"Seção ausente no modelo de ameaças: {section}"
    for tid in ["TM-03", "TM-08", "TM-19", "TM-20"]:
        assert tid in text, f"Ameaça crítica ausente: {tid}"


def test_isolation_docs_are_proposals_and_cover_key_rules():
    ident = (ROOT / "docs/IDENTITY_AND_ISOLATION.md").read_text(encoding="utf-8")
    data = (ROOT / "docs/DATA_MODEL.md").read_text(encoding="utf-8")
    plan = (ROOT / "docs/ISOLATION_TEST_PLAN.md").read_text(encoding="utf-8")
    for name, text in [("IDENTITY", ident), ("DATA_MODEL", data), ("ISOLATION_TEST_PLAN", plan)]:
        assert "**Status:** Proposto" in text, f"{name}: deve constar como Proposto"
    assert "FORCE ROW LEVEL SECURITY" in data
    assert "organization_id" in data
    for tid in ["IT-01", "IT-08", "IT-22", "IT-37", "IT-38"]:
        assert tid in plan, f"Teste ausente no plano: {tid}"


def test_pd16_to_pd20_decisions_are_registered_and_covered():
    risks = (ROOT / "docs/RISKS_AND_DECISIONS.md").read_text(encoding="utf-8")
    assert "## Decisões tomadas pelo responsável" in risks
    for pd in ["PD-16", "PD-17", "PD-18", "PD-19", "PD-20"]:
        assert f"| {pd} | Usuário" in risks or f"| {pd} | Realm" in risks or f"| {pd} | O " in risks, f"{pd} não registrada como decisão"
    pending = risks.split("## Decisões tomadas pelo responsável")[0]
    for pd in ["PD-21", "PD-22", "PD-23"]:
        assert f"| {pd} |" in pending, f"{pd} deveria estar pendente"
    plan = (ROOT / "docs/ISOLATION_TEST_PLAN.md").read_text(encoding="utf-8")
    for tid in ["IT-40", "IT-46", "IT-50", "IT-52", "IT-53"]:
        assert tid in plan, f"Teste ausente: {tid}"
    tm = (ROOT / "docs/THREAT_MODEL.md").read_text(encoding="utf-8")
    for tid in ["TM-37", "TM-39", "TM-41", "TM-43"]:
        assert tid in tm, f"Ameaça ausente: {tid}"


def test_adrs_stay_proposed_after_decisions():
    for adr in (ROOT / "docs/ADR").glob("ADR-*.md"):
        text = adr.read_text(encoding="utf-8")
        assert "não aprovam esta ADR" in text, f"{adr.name}: deve deixar claro que continua Proposta"


# ---------------- guardas da prova de conceito de isolamento ----------------
POC = ROOT / "poc/isolation"
DELIMITER = "-- STATEMENT"


def _poc_sources(suffixes):
    return [p for p in POC.rglob("*") if p.is_file() and p.suffix in suffixes and "evidence" not in p.parts]


def _poc_test_files():
    return sorted((POC / "tests").glob("*.py"))


def test_poc_python_sources_compile():
    for path in _poc_sources({".py"}):
        compile(path.read_text(encoding="utf-8"), str(path), "exec")


def test_poc_has_no_forbidden_shortcuts():
    for path in _poc_sources({".py", ".sql"}):
        assert "sqlite" not in path.read_text(encoding="utf-8").lower(), f"{path}: SQLite proibido"
    tests_text = "\n".join(p.read_text(encoding="utf-8") for p in _poc_test_files())
    for forbidden in ["pytest.mark.skip", "skipif", "pytest.skip(", "importorskip"]:
        assert forbidden not in tests_text, f"Teste desabilitado nao e permitido: {forbidden}"
    assert tests_text.count("pytest.mark.xfail") == 1, "Apenas uma limitacao conhecida explicita"
    assert "LIMITAÇÃO CONHECIDA" in tests_text


def test_poc_roles_have_no_dangerous_attributes_in_scripts():
    for path in list((POC / "kael_poc").glob("*.py")) + list((POC / "migrations").glob("*.sql")):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"(?<!NO)SUPERUSER", text), f"{path}: SUPERUSER proibido"
        assert not re.search(r"(?<!NO)BYPASSRLS", text), f"{path}: BYPASSRLS proibido"


def test_poc_isolation_tests_never_use_the_admin_credential():
    for path in _poc_test_files():
        if path.name == "conftest.py":
            continue
        assert "admin_dsn" not in path.read_text(encoding="utf-8").lower(), f"{path.name}: credencial administrativa"
    conftest = (POC / "tests/conftest.py").read_text(encoding="utf-8")
    assert "kael_app" in conftest and "session_user" in conftest


def test_poc_covers_it01_to_it11():
    names = "\n".join(p.read_text(encoding="utf-8") for p in _poc_test_files())
    for n in range(1, 12):
        assert re.search(rf"def test_it{n:02d}_", names), f"Faltam testes IT-{n:02d}"


def test_poc_migrations_are_well_formed_and_enforce_rls_statically():
    migrations = sorted((POC / "migrations").glob("*.sql"))
    assert len(migrations) >= 4
    all_sql = ""
    for path in migrations:
        text = path.read_text(encoding="utf-8")
        all_sql += text + "\n"
        assert text.count("$$") % 2 == 0, f"{path.name}: delimitador $$ desbalanceado"
        for chunk in text.split(DELIMITER):
            assert chunk.count("(") == chunk.count(")"), f"{path.name}: parenteses desbalanceados"
    # a regra vale para o codigo SQL, nao para comentarios
    code_sql = "\n".join(
        line for line in all_sql.splitlines() if not line.strip().startswith("--")
    )
    assert "SECURITY DEFINER" not in code_sql.upper()
    assert "FOR ALL" not in code_sql.upper()
    tables = re.findall(r"CREATE TABLE kael\.(\w+)", code_sql)
    assert {"organizations", "users", "memberships", "files", "datasets", "audit_events"} <= set(tables)
    for table in tables:
        assert f"ALTER TABLE kael.{table} ENABLE ROW LEVEL SECURITY" in code_sql, table
        assert f"ALTER TABLE kael.{table} FORCE ROW LEVEL SECURITY" in code_sql, table


def test_poc_workflow_runs_real_postgres_and_does_not_hide_failures():
    text = (ROOT / ".github/workflows/isolation-poc.yml").read_text(encoding="utf-8")
    assert "postgres:16" in text and "pull_request" in text and "push:" in text
    assert "continue-on-error" not in text
    assert "contents: read" in text
    for line in text.splitlines():
        if "python -m pytest" in line:
            assert "|| true" not in line


def test_poc_doc_declares_status_and_limitations():
    doc = (ROOT / "docs/POC_ISOLATION.md").read_text(encoding="utf-8")
    assert "**Status:** Proposto" in doc
    assert "Limitações conhecidas" in doc
