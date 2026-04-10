"""
Parser analítico de dossiês Excel gerados pelo SRF.
Extrai métricas de negócio por aba e normaliza para JSON estável.
"""
import re
from pathlib import Path
from typing import Any

import pandas as pd


KNOWN_SHEETS = {
    "RESUMO_FINANCEIRO",
    "RESUMO_OPERACIONAL",
    "CRONOGRAMA_DETALHADO",
    "CRONOGRAMA_E_CASCATA",
    "CUSTO_POR_ATIVIDADE",
    "OCUPACAO_TURMAS_DIA",
    "COMPARATIVO_CENARIOS",
    "CRONOGRAMA_MECANIZADO",
    "DASHBOARD",
    "GANTT_SIMPLES",
    "TIMELINE_CASCATA",
}

_MONEY_RE = re.compile(r"R\$\s*([0-9.,]+)")


def _parse_money(val: str) -> float | None:
    if not isinstance(val, str):
        return None
    m = _MONEY_RE.search(val.replace("\xa0", " "))
    if not m:
        return None
    raw = m.group(1).replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def _safe_float(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _df_to_records(df: pd.DataFrame, limit: int = 500) -> list[dict]:
    return df.head(limit).fillna("").to_dict(orient="records")


def _parse_resumo(df: pd.DataFrame) -> dict:
    """Extrai pares Metrica/Valor do RESUMO_FINANCEIRO ou RESUMO_OPERACIONAL."""
    if df.empty or "Metrica" not in df.columns:
        return {"raw": [], "kpis": {}}

    raw = []
    kpis: dict[str, Any] = {}
    for _, row in df.iterrows():
        metric = str(row.get("Metrica", "")).strip()
        valor = str(row.get("Valor", "")).strip()
        if not metric:
            continue
        raw.append({"metrica": metric, "valor": valor})

        money = _parse_money(valor)
        ml = metric.lower()
        if "receita bruta" in ml and "mao" not in ml and "mecan" not in ml:
            kpis["receita_bruta"] = money
        elif "custo mo total" in ml:
            kpis["custo_mo_total"] = money
        elif "lucro direto" in ml or "lucro operacional" in ml:
            kpis["lucro"] = money
        elif "margem" in ml:
            kpis["margem_pct"] = valor
        elif "duracao simulada" in ml and "dias" in ml:
            try:
                kpis["dias_simulados"] = int(float(valor))
            except (ValueError, TypeError):
                pass
        elif "executores" in ml:
            try:
                kpis["executores"] = int(float(valor))
            except (ValueError, TypeError):
                pass
        elif "jornada" in ml:
            try:
                kpis["jornada_h"] = float(valor)
            except (ValueError, TypeError):
                pass
        elif "hh total" in ml:
            kpis["hh_total"] = valor

    return {"raw": raw, "kpis": kpis}


def _parse_cronograma(df: pd.DataFrame) -> dict:
    """Extrai resumo do cronograma detalhado ou combinado."""
    if df.empty:
        return {"total_linhas": 0, "dias": 0, "talhoes": [], "atividades": [], "turmas": []}

    dias = 0
    if "Dia" in df.columns:
        dias = int(df["Dia"].dropna().astype(float, errors="ignore").max() or 0)

    talhoes = sorted(df["Talhao"].dropna().unique().tolist()) if "Talhao" in df.columns else []
    atividades = sorted(df["Atividade"].dropna().unique().tolist()) if "Atividade" in df.columns else []
    turmas = sorted(df["Turma"].dropna().unique().tolist()) if "Turma" in df.columns else []

    hh_total = _safe_float(df["HH"].sum()) if "HH" in df.columns else 0

    by_atividade = []
    if "Atividade" in df.columns and "HH" in df.columns:
        grp = df.groupby("Atividade")["HH"].sum().sort_values(ascending=False).head(15)
        by_atividade = [{"atividade": k, "hh": round(float(v), 1)} for k, v in grp.items()]

    by_turma = []
    if "Turma" in df.columns and "HH" in df.columns:
        grp = df.groupby("Turma")["HH"].sum().sort_values(ascending=False)
        by_turma = [{"turma": k, "hh": round(float(v), 1)} for k, v in grp.items()]

    return {
        "total_linhas": len(df),
        "dias": dias,
        "hh_total": round(hh_total, 1),
        "n_talhoes": len(talhoes),
        "n_atividades": len(atividades),
        "n_turmas": len(turmas),
        "talhoes": talhoes[:20],
        "atividades": atividades,
        "turmas": turmas,
        "por_atividade": by_atividade,
        "por_turma": by_turma,
    }


def _parse_custo_atividade(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"linhas": 0, "items": []}

    items = []
    for _, row in df.iterrows():
        items.append({
            "atividade": str(row.get("Atividade", "")),
            "tipo": str(row.get("Tipo", "")),
            "area_ha": _safe_float(row.get("Area_ha", 0)),
            "hh": _safe_float(row.get("HH", 0)),
            "receita": _safe_float(row.get("Receita_Orcada", 0)),
            "custo_mo": _safe_float(row.get("Custo_MO", 0)),
            "lucro": _safe_float(row.get("Lucro", 0)),
            "margem_pct": _safe_float(row.get("Margem_%", 0)),
        })

    return {"linhas": len(items), "items": items[:30]}


def _parse_ocupacao(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"dias": 0, "resumo": []}

    dias = len(df)
    resumo = []
    uso_cols = [c for c in df.columns if c.endswith("_Uso%")]
    for col in uso_cols:
        turma = col.replace("_Uso%", "")
        avg = _safe_float(df[col].mean())
        max_uso = _safe_float(df[col].max())
        resumo.append({"turma": turma, "uso_medio_pct": round(avg, 1), "uso_max_pct": round(max_uso, 1)})

    total_uso = []
    if "Total_Uso%" in df.columns:
        total_uso = [round(_safe_float(v), 1) for v in df["Total_Uso%"].tolist()]

    return {"dias": dias, "resumo_turmas": resumo, "uso_total_diario": total_uso[:60]}


def _parse_cenarios(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"cenarios": 0, "items": []}
    return {"cenarios": len(df), "items": _df_to_records(df, 20)}


def parse_dossier(xlsx_path: str | Path) -> dict:
    """
    Lê um dossier XLSX completo e devolve análise estruturada por aba.
    Retorno: {file_name, file_type, sheets_found, financeiro, operacional, ...}
    """
    p = Path(xlsx_path)
    result: dict[str, Any] = {
        "file_name": p.name,
        "file_type": "unknown",
        "sheets_found": [],
        "financeiro": None,
        "operacional": None,
        "cronograma": None,
        "custo_atividade": None,
        "ocupacao": None,
        "cenarios": None,
        "mecanizado": None,
    }

    try:
        xls = pd.ExcelFile(str(p), engine="openpyxl")
    except Exception as ex:
        result["error"] = f"Erro ao abrir: {ex}"
        return result

    sheets = xls.sheet_names
    result["sheets_found"] = sheets

    name_lower = p.name.lower()
    if "financeiro" in name_lower:
        result["file_type"] = "financeiro"
    elif "operacional" in name_lower:
        result["file_type"] = "operacional"
    elif "comparativo" in name_lower:
        result["file_type"] = "comparativo"
    elif "mecanizado" in name_lower:
        result["file_type"] = "mecanizado"
    else:
        result["file_type"] = "dossier"

    for sheet in sheets:
        try:
            df = pd.read_excel(xls, sheet_name=sheet, engine="openpyxl")
        except Exception:
            continue

        if sheet in ("RESUMO_FINANCEIRO", "RESUMO_OPERACIONAL"):
            parsed = _parse_resumo(df)
            if sheet == "RESUMO_FINANCEIRO":
                result["financeiro"] = parsed
            else:
                result["operacional"] = parsed

        elif sheet in ("CRONOGRAMA_DETALHADO", "CRONOGRAMA_E_CASCATA"):
            result["cronograma"] = _parse_cronograma(df)

        elif sheet == "CUSTO_POR_ATIVIDADE":
            result["custo_atividade"] = _parse_custo_atividade(df)

        elif sheet == "OCUPACAO_TURMAS_DIA":
            result["ocupacao"] = _parse_ocupacao(df)

        elif sheet == "COMPARATIVO_CENARIOS":
            result["cenarios"] = _parse_cenarios(df)

        elif sheet == "CRONOGRAMA_MECANIZADO":
            result["mecanizado"] = _parse_cronograma(df)

    xls.close()
    return result
