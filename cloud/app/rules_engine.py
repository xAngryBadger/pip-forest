"""
Motor de regras determinísticas para insights automáticos.
Analisa dados estruturados do report_parser e produz recomendações.
"""
from typing import Any


def _safe(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def analyze(parsed: dict) -> list[dict]:
    """
    Recebe saída do report_parser.parse_dossier() e devolve lista de insights.
    Cada insight: {tipo, severidade, titulo, descricao, metrica, valor}
    severidade: "info" | "aviso" | "alerta" | "critico"
    """
    insights: list[dict] = []

    fin = parsed.get("financeiro") or {}
    ops = parsed.get("operacional") or {}
    crono = parsed.get("cronograma") or {}
    custos = parsed.get("custo_atividade") or {}
    ocup = parsed.get("ocupacao") or {}

    kpis = fin.get("kpis", {}) or ops.get("kpis", {})

    receita = _safe(kpis.get("receita_bruta"))
    custo = _safe(kpis.get("custo_mo_total"))
    lucro = _safe(kpis.get("lucro"))
    dias = _safe(kpis.get("dias_simulados"))
    executores = _safe(kpis.get("executores"))

    if receita > 0 and custo > 0:
        margem = (lucro / receita) * 100 if receita > 0 else 0
        if margem < 10:
            insights.append({
                "tipo": "financeiro",
                "severidade": "critico",
                "titulo": "Margem muito baixa",
                "descricao": f"Margem de {margem:.1f}% sobre receita de R$ {receita:,.0f}. Risco de prejuízo operacional.",
                "metrica": "margem_pct",
                "valor": round(margem, 1),
            })
        elif margem < 25:
            insights.append({
                "tipo": "financeiro",
                "severidade": "aviso",
                "titulo": "Margem abaixo do ideal",
                "descricao": f"Margem de {margem:.1f}%. Considerar otimizar HH ou renegociar tarifas.",
                "metrica": "margem_pct",
                "valor": round(margem, 1),
            })
        else:
            insights.append({
                "tipo": "financeiro",
                "severidade": "info",
                "titulo": "Margem saudável",
                "descricao": f"Margem de {margem:.1f}% indica boa relação receita/custo.",
                "metrica": "margem_pct",
                "valor": round(margem, 1),
            })

    if custo > 0 and receita > 0:
        ratio = custo / receita * 100
        if ratio > 80:
            insights.append({
                "tipo": "financeiro",
                "severidade": "alerta",
                "titulo": "Custo MO consome mais de 80% da receita",
                "descricao": f"Custo MO representa {ratio:.0f}% da receita bruta.",
                "metrica": "custo_receita_pct",
                "valor": round(ratio, 1),
            })

    hh_total = _safe(crono.get("hh_total"))
    n_turmas = _safe(crono.get("n_turmas"))
    n_atividades = _safe(crono.get("n_atividades"))

    if dias > 0 and executores > 0:
        hh_dia = hh_total / dias if dias > 0 else 0
        cap_dia = executores * _safe(kpis.get("jornada_h", 5))
        if cap_dia > 0:
            uso_medio = (hh_dia / cap_dia) * 100
            if uso_medio > 95:
                insights.append({
                    "tipo": "operacional",
                    "severidade": "alerta",
                    "titulo": "Equipe no limite da capacidade",
                    "descricao": f"Uso médio de {uso_medio:.0f}% — risco de atrasos se houver imprevistos.",
                    "metrica": "uso_medio_pct",
                    "valor": round(uso_medio, 1),
                })
            elif uso_medio < 50:
                insights.append({
                    "tipo": "operacional",
                    "severidade": "aviso",
                    "titulo": "Equipe subutilizada",
                    "descricao": f"Uso médio de {uso_medio:.0f}% — possível reduzir equipe ou prazo.",
                    "metrica": "uso_medio_pct",
                    "valor": round(uso_medio, 1),
                })

    turma_resumo = ocup.get("resumo_turmas", [])
    for tr in turma_resumo:
        uso = _safe(tr.get("uso_medio_pct"))
        nome = tr.get("turma", "")
        if uso < 30:
            insights.append({
                "tipo": "operacional",
                "severidade": "aviso",
                "titulo": f"Turma '{nome}' com baixa ocupação",
                "descricao": f"Uso médio de {uso:.0f}% — realocar ou redistribuir demanda.",
                "metrica": f"uso_{nome}",
                "valor": uso,
            })
        elif uso > 95:
            insights.append({
                "tipo": "operacional",
                "severidade": "alerta",
                "titulo": f"Turma '{nome}' sobrecarregada",
                "descricao": f"Uso médio de {uso:.0f}% — risco de gargalo.",
                "metrica": f"uso_{nome}",
                "valor": uso,
            })

    por_atv = crono.get("por_atividade", [])
    if len(por_atv) >= 2:
        top = por_atv[0]
        total_hh = sum(_safe(a.get("hh")) for a in por_atv)
        if total_hh > 0:
            top_pct = _safe(top.get("hh")) / total_hh * 100
            if top_pct > 40:
                insights.append({
                    "tipo": "cronograma",
                    "severidade": "info",
                    "titulo": f"Atividade dominante: {top.get('atividade', '?')}",
                    "descricao": f"Concentra {top_pct:.0f}% do HH total — priorizar na alocação.",
                    "metrica": "concentracao_atividade",
                    "valor": round(top_pct, 1),
                })

    custo_items = custos.get("items", [])
    for item in custo_items:
        m = _safe(item.get("margem_pct"))
        if m < 0:
            insights.append({
                "tipo": "financeiro",
                "severidade": "critico",
                "titulo": f"Prejuízo em '{item.get('atividade', '?')}'",
                "descricao": f"Margem de {m:.1f}% — custo MO excede receita.",
                "metrica": f"margem_{item.get('atividade', '')}",
                "valor": m,
            })

    uso_diario = ocup.get("uso_total_diario", [])
    if uso_diario:
        dias_ociosos = sum(1 for u in uso_diario if u < 20)
        if dias_ociosos > 3:
            insights.append({
                "tipo": "cronograma",
                "severidade": "aviso",
                "titulo": f"{dias_ociosos} dias com equipe quase ociosa",
                "descricao": "Dias com uso total abaixo de 20% — verificar sequenciamento.",
                "metrica": "dias_ociosos",
                "valor": dias_ociosos,
            })

    if not insights:
        insights.append({
            "tipo": "info",
            "severidade": "info",
            "titulo": "Análise sem alertas",
            "descricao": "Nenhuma anomalia detectada nas regras atuais.",
            "metrica": "ok",
            "valor": 0,
        })

    sev_order = {"critico": 0, "alerta": 1, "aviso": 2, "info": 3}
    insights.sort(key=lambda x: sev_order.get(x.get("severidade", "info"), 9))

    return insights
