"""
SRF text utilities — pure string/normalization helpers.

Zero internal dependencies. Every other SRF module may safely import from here.
"""

import re
import unicodedata

# ──────────────────────────────────────────────
# ACCENT / KEY NORMALIZATION
# ──────────────────────────────────────────────

def remover_acentos(texto):
    """Remove diacritics, lowercases, strips. Returns '' for non-str."""
    if not isinstance(texto, str):
        return ""
    return (
        "".join(
            c
            for c in unicodedata.normalize("NFD", texto)
            if unicodedata.category(c) != "Mn"
        )
        .lower()
        .strip()
    )


_RE_PUNCT = re.compile(r"[^a-z0-9 ]+")
_RE_SPACES = re.compile(r"\s+")


def normalizar_chave(texto):
    """remover_acentos + strip punctuation + collapse whitespace. Canonical lookup key."""
    s = remover_acentos(texto)
    s = _RE_PUNCT.sub(" ", s)
    return _RE_SPACES.sub(" ", s).strip()


def _normalizar_chave_atividade_semantica(texto):
    """
    Normaliza texto de atividade preservando semantica de tokens de fase.
    Regra de negocio (supervisor): PL=Plantio, CD=Conducao.
    Mantem retrocompatibilidade com chaves legadas ao ser usado em conjunto com
    _candidatos_chave_atividade().
    """
    base = normalizar_chave(texto)
    if not base:
        return base
    toks = base.split()
    out = []
    for i, t in enumerate(toks):
        prev = toks[i - 1] if i > 0 else ""
        if t == "pl" and prev in ("impl", "implant", "implantacao"):
            out.append("plantio")
        elif t == "cd" and prev in ("impl", "implant", "implantacao"):
            out.append("conducao")
        else:
            out.append(t)
    return " ".join(out).strip()


def _candidatos_chave_atividade(texto):
    """
    Gera variantes de chave para lookup robusto:
    1) legado (PL/CD literal), 2) semantico (Plantio/Conducao).
    """
    legado = normalizar_chave(texto)
    semantico = _normalizar_chave_atividade_semantica(texto)
    if semantico and semantico != legado:
        return [legado, semantico]
    return [legado]


# ──────────────────────────────────────────────
# MISC HELPERS
# ──────────────────────────────────────────────

def _norm_atv(x):
    """Normaliza nome de atividade para cruzamento template x micro (NA-safe, str strip)."""
    import pandas as pd  # local to avoid hard dep at import time

    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except (TypeError, ValueError):
        pass
    return str(x).strip()


def _slug_ficheiro_seguro(s, max_len=48):
    """Nome seguro para ficheiros Windows (sem acentos problematicos)."""
    t = remover_acentos(str(s).strip()) if s else ""
    t = re.sub(r'[<>:"/\\|?*]+', "_", t)
    t = re.sub(r"\s+", "_", t)
    t = re.sub(r"_+", "_", t).strip("_")
    return t[:max_len] if t else "escopo"


def parse_intervalos_escolha(texto, max_n):
    """
    Converte '1,3,5-8' em indices 0-based unicos e ordenados (numeracao 1..max_n).
    Espacos ignorados; intervalos inclusive.
    """
    out = set()
    if not texto or not str(texto).strip() or max_n < 1:
        return []
    for part in str(texto).replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                lo, hi = int(a), int(b)
                if lo > hi:
                    lo, hi = hi, lo
                for k in range(lo, hi + 1):
                    if 1 <= k <= max_n:
                        out.add(k - 1)
            except ValueError:
                continue
        else:
            try:
                k = int(part)
                if 1 <= k <= max_n:
                    out.add(k - 1)
            except ValueError:
                continue
    return sorted(out)


def filtrar_atividades_por_texto(atividades, texto):
    """Nomes cuja versao sem acento contem o filtro (substring)."""
    t = remover_acentos(texto)
    if not t:
        return []
    out = []
    for a in atividades:
        if t in remover_acentos(str(a)):
            out.append(a)
    return out


def atividades_por_filtro(atividades_reais, filtros_texto):
    """Retorna atividades cujo nome contem algum filtro (sem acento)."""
    filtros = [
        remover_acentos(x).strip() for x in (filtros_texto or []) if str(x).strip()
    ]
    out = set()
    for atv in atividades_reais:
        nome = remover_acentos(str(atv))
        if any(f in nome for f in filtros):
            out.add(atv)
    return sorted(out, key=lambda x: str(x))
