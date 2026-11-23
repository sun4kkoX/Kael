"""Resumo em Markdown a partir do junit.xml e das evidencias.

Uso: python -m kael_poc.report <junit.xml> <diretorio_de_evidencias>
Categorias: PASSOU, FALHOU, ERRO, NAO EXECUTADO, LIMITACAO CONHECIDA (xfail estrito) e
PULADO (proibido: conta como falha).
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

TITLES = {
    "it01": "IT-01 Ler, alterar e apagar linhas de outra organizacao (todas as tabelas)",
    "it02": "IT-02 Inserir com organization_id de outra organizacao (inclui lote)",
    "it03": "IT-03 Referencia cruzada por chave composta",
    "it04": "IT-04 Sem contexto: falha fechada",
    "it05": "IT-05 Contexto transacional e conexao reutilizada",
    "it06": "IT-06 Transacoes concorrentes alternando organizacoes",
    "it07": "IT-07 Papel da aplicacao sem privilegios indevidos",
    "it08": "IT-08 RLS habilitado, forcado e politicas em todas as tabelas",
    "it09": "IT-09 Nenhuma funcao SECURITY DEFINER fora da lista",
    "it10": "IT-10 organization_id imutavel",
    "it11": "IT-11 Auditoria somente de acrescimo",
}
EXTRA = {
    "rev": "Membership revogada, suspensa ou pendente",
    "forgery": "Tentativas de falsificacao de organizacao",
    "limit": "Limitacoes conhecidas (esperadas)",
}
PATTERN = re.compile(r"^test_(it\d\d|rev|forgery|limit)_")


def classify(case: ET.Element) -> str:
    if case.find("failure") is not None:
        return "FALHOU"
    if case.find("error") is not None:
        return "ERRO"
    skipped = case.find("skipped")
    if skipped is not None:
        kind = (skipped.get("type") or "") + (skipped.get("message") or "")
        return "LIMITACAO CONHECIDA" if "xfail" in kind.lower() else "PULADO"
    return "PASSOU"


def main(junit_path: str, evidence_dir: str) -> int:
    path = Path(junit_path)
    groups: dict[str, list[tuple[str, str]]] = {}
    if path.exists():
        for case in ET.parse(path).getroot().iter("testcase"):
            name = case.get("name", "")
            match = PATTERN.match(name)
            key = match.group(1) if match else "outros"
            groups.setdefault(key, []).append((name, classify(case)))

    def aggregate(cases):
        if not cases:
            return "NAO EXECUTADO"
        states = {s for _, s in cases}
        for bad in ("ERRO", "FALHOU", "PULADO"):
            if bad in states:
                return bad
        if states == {"LIMITACAO CONHECIDA"}:
            return "LIMITACAO CONHECIDA"
        return "PASSOU"

    print("# Prova de conceito de isolamento: resultados\n")
    print("| Teste | Casos | Resultado |\n|---|---|---|")
    bad_total = 0
    for key, title in TITLES.items():
        cases = groups.get(key, [])
        result = aggregate(cases)
        bad_total += result != "PASSOU"
        print(f"| {title} | {len(cases)} | **{result}** |")
    for key, title in EXTRA.items():
        cases = groups.get(key, [])
        result = aggregate(cases)
        if key != "limit":
            bad_total += result != "PASSOU"
        print(f"| {title} | {len(cases)} | **{result}** |")
    print()
    print("## Casos individuais\n")
    print("| Caso | Resultado |\n|---|---|")
    for key in list(TITLES) + list(EXTRA) + ["outros"]:
        for name, state in groups.get(key, []):
            print(f"| `{name}` | {state} |")
    print()
    if not path.exists():
        print("**junit.xml nao encontrado: os testes nao chegaram a rodar.**\n")
    ev = Path(evidence_dir)
    for md in sorted(ev.glob("0*.md")):
        print(md.read_text(encoding="utf-8"))
    return 0 if bad_total == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("uso: python -m kael_poc.report <junit.xml> <diretorio_de_evidencias>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
