"""
Auditoria rapida da planilha de microplanejamento para ATM v6.

Uso:
  python testes/auditar_planilha_atm6.py "C:\\caminho\\planilha.xlsx" --ct "CT_313_NORMALIZADA.xlsx"
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import atm_v6 as atm


def _sheet_of_interest(xls: pd.ExcelFile) -> str | None:
    for name in xls.sheet_names:
        n = atm.remover_acentos(name).replace(" ", "")
        if "microplanejamento_abril_junho" in n:
            return name
    for name in xls.sheet_names:
        n = atm.remover_acentos(name)
        if "microplanejamento" in n:
            return name
    return xls.sheet_names[0] if xls.sheet_names else None


def _token_counts(atividades: list[str]) -> Counter:
    c = Counter()
    for a in atividades:
        kn = atm.normalizar_chave(a)
        toks = set(kn.split())
        if "pl" in toks:
            c["token_pl"] += 1
        if "cd" in toks:
            c["token_cd"] += 1
        if "plantio" in toks:
            c["token_plantio"] += 1
        if "conducao" in toks:
            c["token_conducao"] += 1
        if "manut" in toks or "manutencao" in toks:
            c["token_manutencao"] += 1
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx", help="Planilha de microplanejamento (.xlsx)")
    ap.add_argument("--ct", default="CT_313_NORMALIZADA.xlsx", help="Planilha CT normalizada")
    args = ap.parse_args()

    if not os.path.exists(args.xlsx):
        print(f"ERRO: arquivo nao encontrado: {args.xlsx}")
        return 2

    xls = pd.ExcelFile(args.xlsx)
    aba = _sheet_of_interest(xls)
    print(f"ABAS={xls.sheet_names}")
    print(f"ABA_MICRO_ESCOLHIDA={aba}")

    cfg = {"tarifas": {}, "de_para": {}, "atividades": {}}
    if os.path.exists(args.ct):
        cfg["tarifas"] = atm.carregar_stg_tarifas(args.ct)
    else:
        print(f"AVISO: CT nao encontrada ({args.ct}); auditoria de de-para parcial.")

    df = atm.carregar_planilha_microplanejamento(cfg, caminho=args.xlsx, modo_auto=True)
    if df is None or df.empty:
        print("ERRO: microplanejamento vazio/nao carregado.")
        return 3

    atividades = sorted(df["atividade"].dropna().astype(str).unique().tolist(), key=str)
    print(f"LINHAS_VALIDAS={len(df)}")
    print(f"ATIVIDADES_UNICAS={len(atividades)}")

    counts = _token_counts(atividades)
    for k in ("token_pl", "token_cd", "token_plantio", "token_conducao", "token_manutencao"):
        print(f"{k.upper()}={counts.get(k, 0)}")

    # Evita escrita em config durante auditoria.
    _save_orig = atm.salvar_config
    atm.salvar_config = lambda _cfg: None
    try:
        if cfg["tarifas"]:
            novos = atm.aplicar_depara_padrao_exame(cfg, atividades)
            print(f"DEPARA_APLICADO={novos}")

            sem_tarifa = []
            for atv in atividades:
                chave = atm.resolver_chave_tarifa(cfg, cfg["tarifas"], atv)
                if chave not in cfg["tarifas"]:
                    sem_tarifa.append(atv)
            print(f"SEM_TARIFA={len(sem_tarifa)}")
            if sem_tarifa:
                print("TOP_SEM_TARIFA:")
                for a in sem_tarifa[:20]:
                    print(f" - {a}")
    finally:
        atm.salvar_config = _save_orig

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
