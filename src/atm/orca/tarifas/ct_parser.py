"""CT313 Excel parser and normalizer."""

import datetime
import os
from statistics import median

import pandas as pd

from ..config import INPUT_DIR, STG_FILENAME
from ..constants import CT317_HARDCODE_HH_BASE
from ..text_utils import normalizar_chave, remover_acentos, _to_float_any
from ..logging_config import get_logger
from ..io import ExcelReader
from .preco_final_json import _carregar_mapa_preco_final_json, _aplicar_mapa_preco_final_em_rows_by_name, _score_payload_preco

logger = get_logger(__name__)


def _find_preco_final_sheet(xls):
    for s in xls.sheet_names:
        ns = remover_acentos(s).replace(" ", "").replace("_", "").replace("-", "")
        if "precofinal" in ns:
            return s
    return None


def _guess_sheet(xls, keys):
    for s in xls.sheet_names:
        ns = normalizar_chave(s)
        if all(k in ns for k in keys):
            return s
    return None


def _pick_col(df, required_tokens_sets):
    cols = list(df.columns)
    for c in cols:
        nc = normalizar_chave(c)
        for toks in required_tokens_sets:
            if all(t in nc for t in toks):
                return c
    return None


def _last_non_zero(nums):
    for n in reversed(nums):
        if n is not None and abs(float(n)) > 1e-9:
            return float(n)
    for n in reversed(nums):
        if n is not None:
            return float(n)
    return 0.0


def _is_raw_cost_row_label(lbl):
    n = normalizar_chave(lbl)
    if not n:
        return False
    bad = {
        "indireto",
        "custo indireto pessoal",
        "custo indireto",
        "custo direto",
        "bdi",
        "soma",
    }
    if n in bad:
        return False
    if n in {"d", "premio"}:
        return False
    if n.startswith("previsao "):
        return False
    if n.startswith("resultado "):
        return False
    if n.startswith("desconto "):
        return False
    return True


def _extrair_custos_globais_brutos(caminho, sheet_cd, sheet_ci):
    def parse_sheet(sheet_name):
        df = ExcelReader.read(caminho, sheet_name=sheet_name, header=None)
        itens = []
        total_linha = None
        for _, r in df.iterrows():
            label = str(r.iloc[0] if len(r) > 0 else "").strip()
            if not label:
                continue
            nums = []
            for v in list(r.iloc[1:]):
                fv = _to_float_any(v)
                if fv is not None:
                    nums.append(fv)
            nlabel = normalizar_chave(label)
            if nlabel in {"custo direto", "custo indireto"}:
                total_linha = _last_non_zero(nums)
                continue
            if _is_raw_cost_row_label(label):
                val = _last_non_zero(nums)
                if abs(val) > 1e-9:
                    itens.append({"item": label, "valor": round(float(val), 6)})
        total = (
            float(total_linha)
            if total_linha is not None
            else float(sum(x["valor"] for x in itens))
        )
        return total, itens

    total_cd, itens_cd = parse_sheet(sheet_cd)
    total_ci, itens_ci = parse_sheet(sheet_ci)
    return {
        "valor_direto_total": round(float(total_cd), 6),
        "valor_indireto_total": round(float(total_ci), 6),
        "itens_direto": itens_cd,
        "itens_indireto": itens_ci,
    }


def normalizar_ct313(caminho_ct):
    """
    Le CT_313 bruta e gera CT_313_NORMALIZADA.xlsx com aba STG_TARIFAS.
    Retorna (caminho_stg, n_linhas, custo_hora_tf).
    """
    xls = pd.ExcelFile(caminho_ct)
    pf = _find_preco_final_sheet(xls)
    if not pf:
        return None, 0, 0.0

    dfh = ExcelReader.read(caminho_ct, sheet_name=pf)

    custo_hora_tf = 0.0
    rows_by_name = {}

    def col_by_tokens(df, token_sets):
        cols = list(df.columns)
        for c in cols:
            nc = normalizar_chave(c)
            for toks in token_sets:
                if all(t in nc for t in toks):
                    return c
        return None

    col_nome = col_by_tokens(
        dfh, [["operac"], ["atividade"], ["descricao"], ["servico"]],
    )
    col_tipo = col_by_tokens(dfh, [["tipo"]])
    col_hh = col_by_tokens(
        dfh, [["rendimento", "hh"], ["homem", "hora"], ["hh", "ha"]],
    )
    col_hm = col_by_tokens(
        dfh, [["rendimento", "maq"], ["rendimento", "maquina"], ["hm"], ["maquina", "ha"]],
    )
    col_preco = col_by_tokens(dfh, [["preco"], ["tarifa"], ["valor"]])
    col_custo_h = col_by_tokens(dfh, [["custo", "hora"], ["r", "h"]])

    if col_nome and (col_hh or col_hm):
        total_cells = 0
        failed_cells = 0
        for _, r in dfh.iterrows():
            nome = str(r.get(col_nome, "")).strip()
            if not nome or nome.lower() in {"nan", "none"}:
                continue
            if normalizar_chave(nome) in {"operacoes", "operacao", "atividade"}:
                continue
            hh = _to_float_any(r.get(col_hh)) if col_hh else 0.0
            hm = _to_float_any(r.get(col_hm)) if col_hm else 0.0
            preco = _to_float_any(r.get(col_preco)) if col_preco else 0.0
            tipo = str(r.get(col_tipo, "")).strip() if col_tipo else ""
            custo_h = _to_float_any(r.get(col_custo_h)) if col_custo_h else 0.0
            for val in (hh, hm, preco, custo_h):
                total_cells += 1
                if val is None:
                    failed_cells += 1
            hh = float(hh or 0.0)
            hm = float(hm or 0.0)
            preco = float(preco or 0.0)
            custo_h = float(custo_h or 0.0)
            if hh <= 0 and hm <= 0 and preco <= 0:
                continue
            prev = rows_by_name.get(nome)
            payload = {
                "atividade": nome,
                "tipo": tipo or ("Mecanizada" if hm > 0 else "Manual"),
                "rendimento_hh": hh,
                "rendimento_hm": hm,
                "preco_ha": preco,
                "custo_hora": custo_h,
                "custo_ha": (hh * custo_h) if custo_h > 0 else 0.0,
                "fonte_aba": pf,
            }
            if prev is None:
                rows_by_name[nome] = payload
            else:
                prev_score = (
                    float(prev.get("rendimento_hh", 0) or 0)
                    + float(prev.get("rendimento_hm", 0) or 0)
                    + float(prev.get("preco_ha", 0) or 0)
                    + float(prev.get("custo_hora", 0) or 0)
                )
                cur_score = hh + hm + preco + custo_h
                if cur_score >= prev_score:
                    rows_by_name[nome] = payload
        if total_cells > 0 and failed_cells / total_cells > 0.5:
            logger.warning(
                "High parse failure rate in %s: %d/%d cells failed (%.1f%%)",
                pf,
                failed_cells,
                total_cells,
                failed_cells / total_cells * 100,
            )

    if len(rows_by_name) < 20:
        df = ExcelReader.read(caminho_ct, sheet_name=pf, header=None)
        total_cells = 0
        failed_cells = 0
        for i in range(5, len(df)):
            r = df.iloc[i]
            nome = str(r[2]).strip() if pd.notna(r[2]) else ""
            if not nome or nome == "0":
                continue
            tipo = str(r[4]).strip() if pd.notna(r[4]) else ""
            try:
                hh = float(r[5]) if pd.notna(r[5]) else 0.0
            except (TypeError, ValueError):
                hh = 0.0
                failed_cells += 1
            try:
                hm = float(r[6]) if pd.notna(r[6]) else 0.0
            except (TypeError, ValueError):
                hm = 0.0
                failed_cells += 1
            try:
                preco = float(r[7]) if pd.notna(r[7]) else 0.0
            except (TypeError, ValueError):
                preco = 0.0
                failed_cells += 1
            total_cells += 3
            if hh <= 0 and hm <= 0 and preco <= 0:
                continue
            rows_by_name[nome] = {
                "atividade": nome,
                "tipo": tipo or ("Mecanizada" if hm > 0 else "Manual"),
                "rendimento_hh": hh,
                "rendimento_hm": hm,
                "preco_ha": preco,
                "custo_hora": 0.0,
                "custo_ha": 0.0,
                "fonte_aba": pf,
            }
        if total_cells > 0 and failed_cells / total_cells > 0.5:
            logger.warning(
                "High parse failure rate in %s (fallback): %d/%d cells failed (%.1f%%)",
                pf,
                failed_cells,
                total_cells,
                failed_cells / total_cells * 100,
            )

    mapa_json = _carregar_mapa_preco_final_json()
    if mapa_json:
        _aplicar_mapa_preco_final_em_rows_by_name(
            rows_by_name, mapa_json, f"{pf}|preco_final_json"
        )

    for nome, base in CT317_HARDCODE_HH_BASE.items():
        cur = rows_by_name.get(nome)
        if cur is None:
            cur = {
                "atividade": nome,
                "tipo": base.get("tipo", "Manual"),
                "rendimento_hh": float(base.get("rendimento_hh", 0) or 0),
                "rendimento_hm": float(base.get("rendimento_hm", 0) or 0),
                "preco_ha": 0.0,
                "custo_hora": 0.0,
                "custo_ha": 0.0,
                "fonte_aba": f"{pf}|hardcoded_hh",
            }
            rows_by_name[nome] = cur
            continue
        hh_cur = float(cur.get("rendimento_hh", 0) or 0)
        hm_cur = float(cur.get("rendimento_hm", 0) or 0)
        hh_base = float(base.get("rendimento_hh", 0) or 0)
        hm_base = float(base.get("rendimento_hm", 0) or 0)
        if hh_base > 0 and hh_cur <= 0:
            cur["rendimento_hh"] = hh_base
            cur["rendimento_hm"] = 0.0
            cur["tipo"] = base.get("tipo", "Manual")
            cur["fonte_aba"] = f"{pf}|hardcoded_hh"
        elif hh_cur <= 0 and hm_cur <= 0:
            cur["rendimento_hh"] = hh_base
            cur["rendimento_hm"] = hm_base
            cur["tipo"] = cur.get("tipo") or base.get("tipo", "Manual")
            cur["fonte_aba"] = f"{pf}|hardcoded_hh"
        if float(cur.get("rendimento_hh", 0) or 0) > 0 and float(
            cur.get("rendimento_hm", 0) or 0
        ) > 0:
            cur["rendimento_hm"] = 0.0

    rows = list(rows_by_name.values())

    custos_h_validos = [float(r.get("custo_hora", 0) or 0) for r in rows if float(r.get("custo_hora", 0) or 0) > 0]
    if custos_h_validos:
        custo_hora_tf = float(median(custos_h_validos))

    for r in rows:
        hh = float(r.get("rendimento_hh", 0) or 0)
        ch = float(r.get("custo_hora", 0) or 0)
        if hh > 0 and ch <= 0 and custo_hora_tf > 0:
            ch = custo_hora_tf
            r["custo_hora"] = ch
            r["custo_ha"] = (hh * ch) if ch > 0 else 0.0

    df_stg = pd.DataFrame(rows)
    meta = pd.DataFrame(
        [
            {
                "gerado_em": datetime.datetime.now().isoformat(),
                "arquivo_origem": os.path.basename(caminho_ct),
                "linhas_validas": len(rows),
                "custo_hora_tf": round(custo_hora_tf, 4),
            }
        ]
    )

    stg_path = os.path.join(INPUT_DIR, STG_FILENAME)
    with pd.ExcelWriter(stg_path, engine="openpyxl") as w:
        df_stg.to_excel(w, sheet_name="STG_TARIFAS", index=False)
        meta.to_excel(w, sheet_name="STG_METADATA", index=False)

    return stg_path, len(rows), custo_hora_tf


def carregar_stg_tarifas(stg_path):
    """Le STG_TARIFAS e retorna dict {atividade: {rendimento_hh, preco_ha, custo_hora, custo_ha, tipo}}."""
    df = ExcelReader.read(stg_path, sheet_name="STG_TARIFAS")
    t = {}
    for _, r in df.iterrows():
        nome = str(r.get("atividade", "")).strip()
        if not nome:
            continue
        hh = float(r.get("rendimento_hh") or 0)
        hm = float(r.get("rendimento_hm") or 0)
        t[nome] = {
            "rendimento_hh": hh,
            "rendimento_hm": hm,
            "preco_ha": float(r.get("preco_ha") or 0),
            "custo_hora": float(r.get("custo_hora") or 0),
            "custo_ha": float(r.get("custo_ha") or 0),
            "tipo": str(r.get("tipo") or ""),
            "preco_unit": float(r.get("preco_ha") or 0),
            "recurso": "homem" if hh > 0 else "maquina",
            "eficiencia": 1.0,
        }
    return t
