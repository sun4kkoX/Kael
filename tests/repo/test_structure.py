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
