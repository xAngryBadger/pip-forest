"""JSON price file I/O functions."""

import os
import json
from statistics import median

from ..config import INPUT_DIR, PRECO_FINAL_JSON_DEFAULT, PRECO_FINAL_JSON_DOWNLOADS, _PRECO_FINAL_JSON_CACHE
from ..text_utils import normalizar_chave, _to_float_json
from ..logging_config import get_logger

logger = get_logger(__name__)


def _candidatos_preco_final_json(cfg=None):
    out = []
    if isinstance(cfg, dict):
        p_cfg = str(cfg.get("preco_final_json_path", "") or "").strip()
        if p_cfg:
            p_cfg = os.path.expanduser(p_cfg)
            if not os.path.isabs(p_cfg):
                p_cfg = os.path.join(INPUT_DIR, p_cfg)
            out.append(p_cfg)
        out.append(os.path.join(INPUT_DIR, PRECO_FINAL_JSON_DEFAULT))
    out.append(PRECO_FINAL_JSON_DOWNLOADS)
    uniq = []
    seen = set()
    for p in out:
        ap = os.path.abspath(os.path.expanduser(str(p)))
        if ap in seen:
            continue
        seen.add(ap)
        uniq.append(ap)
    return uniq


def _score_payload_preco(payload):
    hh = float(payload.get("rendimento_hh", 0) or 0)
    hm = float(payload.get("rendimento_hm", 0) or 0)
    pr = float(payload.get("preco_ha", 0) or payload.get("preco_unit", 0) or 0)
    return (1 if hh > 0 else 0, hh, 1 if pr > 0 else 0, pr, hm)


def _carregar_mapa_preco_final_json(cfg=None):
    """Load price map from JSON file candidates."""
    global _PRECO_FINAL_JSON_CACHE

    caminho = ""
    for c in _candidatos_preco_final_json(cfg):
        if os.path.isfile(c):
            caminho = c
            break
    if not caminho:
        return {}

    try:
        mtime = os.path.getmtime(caminho)
    except OSError:
        logger.exception("_carregar_mapa_preco_final_json: error accessing file")
        return {}

    cache = _PRECO_FINAL_JSON_CACHE or {}
    if (
        cache.get("path") == caminho
        and cache.get("mtime") == mtime
        and isinstance(cache.get("mapa"), dict)
    ):
        return dict(cache.get("mapa") or {})

    try:
        with open(caminho, encoding="utf-8-sig") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.exception("_carregar_mapa_preco_final_json: error reading/parsing JSON")
        return {}

    rows = []
    if isinstance(raw, list):
        rows = raw
    elif isinstance(raw, dict):
        for k in ("data", "rows", "tarifas", "atividades", "preco_final"):
            if isinstance(raw.get(k), list):
                rows = raw.get(k)
                break
        if not rows:
            if raw and all(isinstance(v, dict) for v in raw.values()):
                rows = []
                for k, v in raw.items():
                    item = dict(v)
                    item.setdefault("operacao", k)
                    rows.append(item)

    mapa = {}
    idx_norm = {}
    for item in rows:
        if not isinstance(item, dict):
            continue
        nome = str(
            item.get("operacao")
            or item.get("atividade")
            or item.get("nome")
            or item.get("descricao")
            or ""
        ).strip()
        if not nome:
            continue

        hh = _to_float_json(item.get("rendimento_hh_ha", item.get("rendimento_hh"))) or 0.0
        hm = _to_float_json(item.get("rendimento_maquina_ha", item.get("rendimento_hm"))) or 0.0
        preco = _to_float_json(
            item.get(
                "preco_rs",
                item.get("preco_ha", item.get("preco_unit", item.get("preco"))),
            )
        ) or 0.0
        if hh > 0:
            hm = 0.0
        tipo = str(item.get("tipo") or "").strip()
        if not tipo:
            tipo = "Mecanizada" if hm > 0 and hh <= 0 else "Manual"

        payload = {
            "rendimento_hh": float(hh or 0.0),
            "rendimento_hm": float(hm or 0.0),
            "preco_ha": float(preco or 0.0),
            "preco_unit": float(preco or 0.0),
            "tipo": tipo,
        }
        if (
            payload["rendimento_hh"] <= 0
            and payload["rendimento_hm"] <= 0
            and payload["preco_ha"] <= 0
        ):
            continue

        nk = normalizar_chave(nome)
        if not nk:
            continue
        prev_nome = idx_norm.get(nk)
        if prev_nome is None:
            mapa[nome] = payload
            idx_norm[nk] = nome
        else:
            prev_payload = mapa.get(prev_nome, {})
            if _score_payload_preco(payload) >= _score_payload_preco(prev_payload):
                if prev_nome != nome:
                    mapa.pop(prev_nome, None)
                mapa[nome] = payload
                idx_norm[nk] = nome

    _PRECO_FINAL_JSON_CACHE = {"path": caminho, "mtime": mtime, "mapa": mapa}
    return dict(mapa)


def _aplicar_mapa_preco_final_em_rows_by_name(rows_by_name, mapa_json, fonte_tag):
    if not isinstance(rows_by_name, dict) or not mapa_json:
        return 0
    alterados = 0
    idx_norm = {
        normalizar_chave(k): k
        for k in rows_by_name.keys()
        if isinstance(k, str) and normalizar_chave(k)
    }

    for nome, base in mapa_json.items():
        hh = float(base.get("rendimento_hh", 0) or 0)
        hm = float(base.get("rendimento_hm", 0) or 0)
        preco = float(base.get("preco_ha", 0) or base.get("preco_unit", 0) or 0)
        tipo = str(base.get("tipo") or "").strip()
        if hh > 0:
            hm = 0.0
        if not tipo:
            tipo = "Mecanizada" if hm > 0 and hh <= 0 else "Manual"

        nk = normalizar_chave(nome)
        key = nome if nome in rows_by_name else idx_norm.get(nk)
        if key is None:
            rows_by_name[nome] = {
                "atividade": nome,
                "tipo": tipo,
                "rendimento_hh": hh,
                "rendimento_hm": hm,
                "preco_ha": preco,
                "custo_hora": 0.0,
                "custo_ha": 0.0,
                "fonte_aba": fonte_tag,
            }
            if nk:
                idx_norm[nk] = nome
            alterados += 1
            continue

        row = rows_by_name.get(key)
        if not isinstance(row, dict):
            row = {}
            rows_by_name[key] = row

        mudou = False
        if str(row.get("atividade") or "").strip() != key:
            row["atividade"] = key
            mudou = True

        if hh > 0:
            if float(row.get("rendimento_hh", 0) or 0) != hh:
                row["rendimento_hh"] = hh
                mudou = True
            if float(row.get("rendimento_hm", 0) or 0) != 0.0:
                row["rendimento_hm"] = 0.0
                mudou = True
            if str(row.get("tipo") or "").strip() != (tipo or "Manual"):
                row["tipo"] = tipo or "Manual"
                mudou = True
        elif hm > 0 and float(row.get("rendimento_hh", 0) or 0) <= 0:
            if float(row.get("rendimento_hm", 0) or 0) != hm:
                row["rendimento_hm"] = hm
                mudou = True
            if tipo and str(row.get("tipo") or "").strip() != tipo:
                row["tipo"] = tipo
                mudou = True

        if preco > 0 and float(row.get("preco_ha", 0) or 0) != preco:
            row["preco_ha"] = preco
            mudou = True

        if float(row.get("rendimento_hh", 0) or 0) > 0 and float(
            row.get("rendimento_hm", 0) or 0
        ) > 0:
            row["rendimento_hm"] = 0.0
            mudou = True

        if mudou:
            row["fonte_aba"] = fonte_tag
            alterados += 1
    return alterados