"""Comparativo mecanizado — substituicao manual/mec, cenarios multi-fator."""

import copy
import math

from .constants import COMPARATIVO_MANUAL_MEC
from .ui import sub, C, BL, DM, RS, aviso, ok, prompt, pedir_float


def _atividades_com_mecanizado_disponivel(atividades_reais):
    """
    Retorna lista de atividades que têm equivalente mecanizado.
    """
    pares = []
    for atv in atividades_reais:
        if atv in COMPARATIVO_MANUAL_MEC:
            mec = COMPARATIVO_MANUAL_MEC[atv]
            pares.append((atv, mec))
    return pares


def _substituir_por_mecanizado(df_faz, substituicoes):
    """
    Substitui atividades manuais pelas mecanizadas equivalentes em um dataframe.

    Args:
        df_faz: DataFrame com as atividades
        substituicoes: dict {atividade_manual: atividade_mecanizada}

    Returns:
        DataFrame modificado com atividades substituídas
    """
    df_mec = df_faz.copy()
    for manual, mecanizada in substituicoes.items():
        if isinstance(mecanizada, dict):
            alvo = str(
                mecanizada.get("atividade_mecanizada")
                or mecanizada.get("nome")
                or mecanizada.get("recurso")
                or ""
            ).strip()
        else:
            alvo = str(mecanizada).strip()
        if not alvo:
            continue
        mask = df_mec["atividade"] == manual
        if mask.any():
            df_mec.loc[mask, "atividade"] = alvo
    return df_mec


def _formatar_substituicao_comparativo(valor):
    if isinstance(valor, dict):
        nome = str(
            valor.get("atividade_mecanizada")
            or valor.get("nome")
            or valor.get("recurso")
            or ""
        ).strip()
        hm = float(valor.get("rendimento_hm", valor.get("hm", 0)) or 0)
        custo = float(valor.get("custo_h", 0) or 0)
        origem = str(valor.get("origem", "custom") or "custom")
        if nome:
            return f"{nome} [HM={hm:.2f}, R$ {custo:.2f}/h, {origem}]"
        return f"[HM={hm:.2f}, R$ {custo:.2f}/h, {origem}]"
    return str(valor)


def _clonar_cfg_comparativo_mecanizado(cfg, substituicoes):
    """Cria uma copia isolada do cfg e injeta recursos mecanizados customizados temporarios."""
    cfg_var = copy.deepcopy(cfg or {})
    tarifas = cfg_var.setdefault("tarifas", {})
    de_para = cfg_var.setdefault("de_para", {})

    for manual, mecanizada in (substituicoes or {}).items():
        if not isinstance(mecanizada, dict):
            continue
        nome = str(
            mecanizada.get("atividade_mecanizada")
            or mecanizada.get("nome")
            or mecanizada.get("recurso")
            or ""
        ).strip()
        if not nome:
            continue

        hm = float(mecanizada.get("rendimento_hm", mecanizada.get("hm", 0)) or 0)
        custo_h = float(mecanizada.get("custo_h", mecanizada.get("custo", 0)) or 0)
        preco_ha = float(
            mecanizada.get("preco_ha", mecanizada.get("preco_unit", 0)) or 0
        )
        tipo = str(mecanizada.get("tipo") or "Mecanizada").strip() or "Mecanizada"

        row = dict(tarifas.get(nome, {}) or {})
        row.update(
            {
                "rendimento_hh": 0.0,
                "rendimento_hm": hm,
                "preco_ha": preco_ha,
                "preco_unit": preco_ha,
                "custo_hora": custo_h,
                "tipo": tipo,
                "recurso": "maquina",
                "origem": "comparativo_custom",
            }
        )
        tarifas[nome] = row
        de_para[manual] = nome

    return cfg_var


def _cadastrar_recurso_mecanizado_externo(manual_sugestao=""):
    """Coleta um recurso mecanizado externo para uso apenas na comparacao."""
    sub()
    print(C + BL + " RECURSO MECANIZADO EXTERNO (comparativo)" + RS)
    nome = prompt(
        "Nome do recurso/modelo externo",
        manual_sugestao or "Navu",
    )
    nome = str(nome).strip()
    if not nome:
        aviso("Nome vazio. Recurso externo cancelado.")
        return None
    hm = pedir_float("HM/ha do recurso externo", 1.0)
    custo_h = pedir_float("Custo R$/h do recurso externo", 0.0, allow_zero=True)
    preco_ha = pedir_float("Preco R$/ha (opcional)", 0.0, allow_zero=True)
    return {
        "atividade_mecanizada": nome,
        "rendimento_hm": float(hm or 0.0),
        "custo_h": float(custo_h or 0.0),
        "preco_ha": float(preco_ha or 0.0),
        "preco_unit": float(preco_ha or 0.0),
        "tipo": "Mecanizada",
        "origem": "externo",
    }


def _parse_lista_numeros(txt, as_int=False):
    out = []
    for p in str(txt).replace(";", ",").split(","):
        s = p.strip()
        if not s:
            continue
        try:
            v = float(s.replace(",", "."))
            if as_int:
                v = int(round(v))
            if v > 0:
                out.append(v)
        except Exception:
            pass
    return sorted(set(out))


def coletar_config_comparativo_multifator(executores_base, jornada_base):
    """Coleta grade de cenarios (jornada/equipe) de forma antecipada e explicita."""
    sub()
    print(C + BL + " [CENARIOS] CONFIGURAR COMPARATIVO MULTI-FATOR" + RS)
    print(DM + " O comparativo sera exportado no Excel (COMPARATIVO_CENARIOS)." + RS)
    print(DM + " Exemplo entradas: jornadas 4.3,5.3,8 | equipes 4,6,8,10" + RS)
    jornadas_txt = prompt(" Jornadas (h/dia) separadas por virgula", f"{jornada_base}")
    equipes_txt = prompt(
        " Equipes (executores) separadas por virgula", f"{executores_base}"
    )
    jornadas = _parse_lista_numeros(jornadas_txt, as_int=False)
    equipes = _parse_lista_numeros(equipes_txt, as_int=True)
    if not jornadas:
        jornadas = [float(jornada_base)]
    if not equipes:
        equipes = [int(executores_base)]
    ok(
        f"Comparativo configurado: {len(jornadas)} jornada(s) x {len(equipes)} equipe(s)."
    )
    return {"jornadas": jornadas, "equipes": equipes}


def simular_cenarios_multifator(
    total_hh,
    dias_meta,
    executores_base,
    jornada_base,
    jornadas_in=None,
    equipes_in=None,
    interativo=True,
):
    """
    Simulador de cenarios em lote (aproximacao operacional):
    dias ~ HH total / (executores * jornada)
    """
    jornadas = sorted(
        set(float(x) for x in (jornadas_in or [] if not interativo else []))
    )
    equipes = sorted(set(int(x) for x in (equipes_in or [] if not interativo else [])))
    if interativo:
        sub()
        print(C + BL + " [CENARIOS] COMPARATIVO MULTI-FATOR" + RS)
        print(DM + " Exemplo entradas: jornadas 4.3,5.3 | equipes 6,8,10" + RS)
        jornadas_txt = prompt(
            " Jornadas (h/dia) separadas por virgula", f"{jornada_base}"
        )
        equipes_txt = prompt(
            " Equipes (executores) separadas por virgula", f"{executores_base}"
        )
        jornadas = _parse_lista_numeros(jornadas_txt, as_int=False)
        equipes = _parse_lista_numeros(equipes_txt, as_int=True)
        if not jornadas:
            jornadas = [float(jornada_base)]
        if not equipes:
            equipes = [int(executores_base)]

    rows = []
    for j in jornadas:
        for e in equipes:
            cap = float(e) * float(j)
            dias = int(math.ceil(float(total_hh) / cap)) if cap > 0.01 else 0
            meses = dias / 22.0 if dias > 0 else 0.0
            ganho = int(dias_meta) - int(dias)
            rows.append(
                {
                    "Equipe": int(e),
                    "Jornada_h_dia": float(j),
                    "Dias_Simulados": int(dias),
                    "Meses_Simulados": round(meses, 2),
                    "Ganho_vs_Meta_dias": int(ganho),
                    "HH_Total": round(float(total_hh), 2),
                }
            )
    rows = sorted(
        rows, key=lambda r: (r["Dias_Simulados"], -r["Equipe"], -r["Jornada_h_dia"])
    )
    return rows
