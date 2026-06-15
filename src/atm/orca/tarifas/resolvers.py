"""Pure resolution logic for tariffs - HH, HM, price, cost."""

from __future__ import annotations

from statistics import median
from typing import Any

from ..logging_config import get_logger
from ..config import modo_somente_hh
from ..constants import CT317_HARDCODE_HH_BASE
from ..text_utils import normalizar_chave
from .preco_final_json import _to_float_json

logger = get_logger(__name__)

TarifasDict = dict[str, dict[str, Any]]
ConfigDict = dict[str, Any]
TarifaRow = dict[str, Any]


def mediana_rendimento_hh(tarifas: TarifasDict | None) -> float | None:
    """Mediana dos rendimento_hh > 0 em config.tarifas, ou None."""
    vals = []
    for v in (tarifas or {}).values():
        if not isinstance(v, dict):
            continue
        try:
            x = float(v.get("rendimento_hh", 0))
            if x > 0:
                vals.append(x)
        except (TypeError, ValueError):
            pass
    if not vals:
        return None
    vals.sort()
    n = len(vals)
    mid = n // 2
    if n % 2:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) / 2.0


def resolver_rendimento_hh(
    cfg: ConfigDict,
    tarifas: TarifasDict,
    t_nome: str,
    strict: bool = False,
    session_hh: dict[str, float] | None = None,
    atv_micro: str | None = None,
) -> float | None:
    """
    HH/ha for the key t_nome in tarifas.
    session_hh: optional dict {nome_micro or chave_tarifa: hh_ha} valid only for current execution (doesn't save to config).
    Strict mode: no silent median/8 fallbacks - returns None if invalid.
    Exception: mechanized activities (type Mecanizada or HM>0) return 0.0 in strict.
    """
    if session_hh:
        try:
            if atv_micro and atv_micro in session_hh:
                return float(session_hh[atv_micro])
            if t_nome and t_nome in session_hh:
                return float(session_hh[t_nome])
        except (TypeError, ValueError):
            pass
    if t_nome in (tarifas or {}):
        row = tarifas[t_nome]
        r = row.get("rendimento_hh")
        try:
            rf = float(r)
            if rf >= 0:
                if strict and rf <= 0:
                    tipo = str(row.get("tipo", "")).lower()
                    hm = float(row.get("rendimento_hm", 0) or 0)
                    if "mecaniz" in tipo or hm > 0:
                        return 0.0
                    return None
                return rf
        except (TypeError, ValueError):
            if strict:
                return None
    if strict:
        return None
    ex = cfg.get("rendimento_hh_fallback")
    if ex is not None:
        try:
            e = float(ex)
            if e > 0:
                return e
        except (TypeError, ValueError):
            pass
    med = mediana_rendimento_hh(tarifas)
    if med is not None and med > 0:
        return med
    logger.warning("resolver_rendimento_hh: no match for %r, using hardcoded 8.0 h/ha", t_nome)
    return 8.0


def resolver_rendimento_hm(
    cfg: ConfigDict, tarifas: TarifasDict, t_nome: str, strict: bool = False
) -> float:
    """
    HM/ha for the key t_nome in tarifas.
    In strict mode: absence/invalid returns 0.0 (HM doesn't block human flow).
    """
    if t_nome in (tarifas or {}):
        row = tarifas[t_nome]
        r = row.get("rendimento_hm", 0)
        try:
            rf = float(r)
            if rf >= 0:
                return rf
        except (TypeError, ValueError):
            pass
    if strict:
        return 0.0
    ex = cfg.get("rendimento_hm_fallback")
    if ex is not None:
        try:
            e = float(ex)
            if e > 0:
                return e
        except (TypeError, ValueError):
            pass
    return 0.0


def _mediana_campo(tarifas: TarifasDict | None, campo: str) -> float | None:
    vals = []
    for v in (tarifas or {}).values():
        if not isinstance(v, dict):
            continue
        try:
            x = float(v.get(campo, 0))
            if x > 0:
                vals.append(x)
        except (TypeError, ValueError):
            pass
    return median(vals) if vals else None


def resolver_preco_ha(
    cfg: ConfigDict, tarifas: TarifasDict, t_nome: str, strict: bool = False
) -> float:
    if modo_somente_hh(cfg):
        return 0.0
    if t_nome in (tarifas or {}):
        p = tarifas[t_nome].get("preco_ha") or tarifas[t_nome].get("preco_unit")
        try:
            pf = float(p)
            if pf > 0:
                return pf
        except (TypeError, ValueError):
            pass
    if strict:
        return 0.0  # returns 0.0 not None for price in strict mode when modo_somente_hh is False
    fb = cfg.get("preco_ha_fallback")
    if fb:
        try:
            f = float(fb)
            if f > 0:
                return f
        except (TypeError, ValueError):
            pass
    med = _mediana_campo(tarifas, "preco_ha") or _mediana_campo(tarifas, "preco_unit")
    return med if med and med > 0 else 0.0


def resolver_custo_hora(
    cfg: ConfigDict, tarifas: TarifasDict, t_nome: str, strict: bool = False
) -> float:
    if modo_somente_hh(cfg):
        return 0.0
    if t_nome in (tarifas or {}):
        c = tarifas[t_nome].get("custo_hora")
        try:
            cf = float(c)
            if cf > 0:
                return cf
        except (TypeError, ValueError):
            pass
    if strict:
        return 0.0
    fb = cfg.get("custo_hora_tf")
    if fb:
        try:
            f = float(fb)
            if f > 0:
                return f
        except (TypeError, ValueError):
            pass
    med = _mediana_campo(tarifas, "custo_hora")
    return med if med and med > 0 else 0.0


def resolver_chave_tarifa(cfg: ConfigDict, tarifas: TarifasDict, atv: str) -> str:
    """
    Resolve the tariff key for a micro activity.
    Priority:
    1) de_para[activity] when it exists and is in tariffs;
    2) original activity name when it exists in tariffs;
    3) fallback to the mapped key (even if absent) to maintain clear diagnosis.
    """
    de_para: dict[str, str] = cfg.get("de_para", {}) or {}
    tarifas = tarifas or {}

    def _find_key_norm(target: str, keys) -> str | None:
        nt = normalizar_chave(target)
        if not nt:
            return None
        for k in keys:
            if normalizar_chave(k) == nt:
                return k
        for k in keys:
            nk = normalizar_chave(k)
            if nt in nk or nk in nt:
                return k
        return None

    # 1) exact de_para
    t_map = de_para.get(atv)
    # 1b) de_para by normalized key (avoids mismatch of accent/spaces/case)
    if not t_map:
        natv = normalizar_chave(atv)
        for km, vm in de_para.items():
            if normalizar_chave(km) == natv:
                t_map = vm
                break
    t_map = str(t_map or atv)

    # 2) exact search in tariffs
    if t_map in tarifas:
        return t_map
    if atv in tarifas:
        return atv

    # 3) normalized search in tariffs
    k_norm = _find_key_norm(t_map, tarifas.keys())
    if k_norm:
        return k_norm
    a_norm = _find_key_norm(atv, tarifas.keys())
    if a_norm:
        return a_norm

    # 4) fallback diagnosis
    return t_map