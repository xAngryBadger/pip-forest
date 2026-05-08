"""
Estado JSON para monitores CLI auxiliares (read-only consumers).

Schema (documentacao — um unico ficheiro por PID, overwrite atomico):
- timestamp / timestamp_iso: ultima gravacao
- operacao: fazenda_atual, modo (single|lote|multi_equipe), micro_basename, status_geral,
  equipe_atual (em multi-equipe), mensagem_curta
- lote: dias_meta, dias_consumidos, saldo_dias, fazenda_indice, n_fazendas, status_meta_continuo,
  prazo_absoluto
- rendimentos_sessao: lista de {atividade, hh_ha, origem, chave_tarifa}
- buffer_relatorios: lista max N de {ts, titulo, texto} (cronograma resumo, dossier, cascata)

SRF_MONITOR=0 desliga gravacao e append ao buffer.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

# Diretorio do projeto (atm_v5 e monitores correm a partir da pasta do repo)
DIR = os.path.dirname(os.path.abspath(__file__))

_MAX_BUFFER = 48


def monitor_io_enabled() -> bool:
    v = os.environ.get("SRF_MONITOR", "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def monitor_quiet_duplicate_status() -> bool:
    """Se True, o fluxo principal pode omitir blocos duplicados ja espelhados nos monitores."""
    v = os.environ.get("SRF_MONITOR_QUIET", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def default_state_path(pid: Optional[int] = None) -> str:
    pid = int(pid or os.getpid())
    return os.path.join(DIR, f"estado_sessao_{pid}.json")


def ler_estado(path: str) -> Dict[str, Any]:
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def gravar_atomico(path: str, data: Dict[str, Any]) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> None:
    for k, v in patch.items():
        if (
            k in base
            and isinstance(base[k], dict)
            and isinstance(v, dict)
            and k not in ("rendimentos_sessao", "buffer_relatorios")
        ):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def merge_emit(
    path: str,
    partial: Dict[str, Any],
    *,
    pid: Optional[int] = None,
) -> None:
    """Merge parcial no estado existente e grava com timestamp."""
    if not monitor_io_enabled():
        return
    if pid is not None:
        path = default_state_path(pid)
    cur = ler_estado(path)
    _deep_merge(cur, partial)
    cur["timestamp"] = time.time()
    cur["timestamp_iso"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    gravar_atomico(path, cur)


def append_relatorio(
    path: str,
    titulo: str,
    texto: str,
    *,
    pid: Optional[int] = None,
) -> None:
    if not monitor_io_enabled():
        return
    if pid is not None:
        path = default_state_path(pid)
    cur = ler_estado(path)
    buf: List[Dict[str, Any]] = list(cur.get("buffer_relatorios") or [])
    buf.append(
        {
            "ts": time.time(),
            "titulo": str(titulo)[:200],
            "texto": str(texto)[-120000:],
        }
    )
    cur["buffer_relatorios"] = buf[-_MAX_BUFFER:]
    cur["timestamp"] = time.time()
    cur["timestamp_iso"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    gravar_atomico(path, cur)


def build_rendimentos_from_demandas(demandas: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Extrai lista agregada por atividade a partir do dict talhao -> tarefas."""
    agg: Dict[str, Dict[str, Any]] = {}
    for _talhao, tarefas in (demandas or {}).items():
        for t in tarefas or []:
            atv = str(t.get("atividade", ""))
            if not atv:
                continue
            hh = float(t.get("hh_total", 0) or 0)
            area = float(t.get("area", 0) or 0)
            hh_ha = (hh / area) if area > 1e-9 else 0.0
            origem = str(t.get("rendimento_fonte", t.get("origem", "")))
            chave = str(t.get("chave_tarifa", ""))
            if atv not in agg:
                agg[atv] = {
                    "atividade": atv,
                    "hh_total": 0.0,
                    "area_ha": 0.0,
                    "origem": origem,
                    "chave_tarifa": chave,
                }
            agg[atv]["hh_total"] += hh
            agg[atv]["area_ha"] += area
    out: List[Dict[str, Any]] = []
    for row in sorted(agg.values(), key=lambda x: str(x["atividade"])):
        a = float(row["area_ha"] or 0)
        hh_t = float(row["hh_total"] or 0)
        row["hh_ha"] = round(hh_t / a, 4) if a > 1e-9 else 0.0
        out.append(row)
    return out
