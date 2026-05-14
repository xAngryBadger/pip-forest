"""Cronograma builders — humano, mecanizado."""

from collections import defaultdict

from .text_utils import normalizar_chave, _slug_ficheiro_seguro


def construir_cronograma_mecanizado(demandas, fazenda, jornada, recursos_mec):
    """
    Fila dedicada para cada recurso mecanizado.
    recursos_mec: [{"nome", "prod_ha_h", "custo_h", "atividades": set}]
    """
    todas_filas = []
    for rec in recursos_mec:
        nome_rec = rec["nome"]
        prod = float(rec.get("prod_ha_h") or 0.18)
        tarefas = []
        for talhao, ls in demandas.items():
            for t in ls:
                atv = str(t.get("atividade", ""))
                if atv not in rec.get("atividades", set()):
                    continue
                area = float(t.get("area", 0) or 0)
                if area <= 0.0001:
                    continue
                tarefas.append({"Talhao": talhao, "Atividade": atv, "Area_ha": area})
        if not tarefas:
            continue
        cap_area_dia = max(0.0001, prod * float(jornada))
        dia = 1
        saldo = cap_area_dia
        for t in tarefas:
            rest = float(t["Area_ha"])
            while rest > 0.0001:
                if saldo <= 0.0001:
                    dia += 1
                    saldo = cap_area_dia
                exe = min(rest, saldo)
                rest -= exe
                saldo -= exe
                hh = exe / prod if prod > 0 else 0.0
                todas_filas.append(
                    {
                        "Dia": int(dia),
                        "Fazenda": fazenda,
                        "Talhao": t["Talhao"],
                        "Atividade": t["Atividade"],
                        "Turma": f"MEC_{nome_rec}",
                        "Operarios": 1,
                        "HH": round(hh, 2),
                        "HM": round(hh, 2),
                        "Modo": "Mecanizado",
                        "Origem_Mec": "Cadastro",
                        "Area_ha": round(exe, 4),
                    }
                )
    return sorted(
        todas_filas, key=lambda r: (int(r.get("Dia", 0)), str(r.get("Turma", "")))
    )


def construir_cronograma_mecanizado_auto_hm_tarifa(
    demandas, fazenda, jornada, cfg, tarifas, atividades_alvo=None
):
    """
    Gera cronograma mecanizado automaticamente a partir de HM/ha da tarifa.
    Cada atividade com HM vira uma fila dedicada (paralela), sem cadastro manual de recurso.
    """
    atividades_alvo = set(atividades_alvo or [])
    filas_por_atividade = defaultdict(list)
    for talhao, ls in demandas.items():
        for t in ls:
            atv = str(t.get("atividade", ""))
            if atividades_alvo and atv not in atividades_alvo:
                continue
            area = float(t.get("area", 0) or 0)
            hm_ha = float(t.get("hm_ha", 0) or 0)
            hm_total = float(t.get("hm_total", area * hm_ha) or 0)
            if area <= 0.0001 or hm_ha <= 0 or hm_total <= 0.0001:
                continue
            filas_por_atividade[atv].append(
                {
                    "Talhao": talhao,
                    "Atividade": atv,
                    "Area_ha": area,
                    "HM_ha": hm_ha,
                    "HM_total": hm_total,
                }
            )

    if not filas_por_atividade:
        return [], []

    cronograma = []
    recursos_auto = []
    for atv in sorted(filas_por_atividade.keys(), key=str):
        itens = filas_por_atividade[atv]

        area_total = sum(float(x.get("Area_ha", 0) or 0) for x in itens)
        hm_total_atv = sum(float(x.get("HM_total", 0) or 0) for x in itens)
        hm_ha_medio = (hm_total_atv / area_total) if area_total > 0.0001 else 0.0
        prod_ha_h = (1.0 / hm_ha_medio) if hm_ha_medio > 0.0001 else 0.0
        recursos_auto.append(
            {
                "nome": f"AutoHM_{_slug_ficheiro_seguro(atv, max_len=22)}",
                "prod_ha_h": round(prod_ha_h, 4) if prod_ha_h > 0 else 0.0,
                "atividades": {atv},
            }
        )

        cap_hm_dia = max(0.0001, float(jornada))
        dia = 1
        saldo_hm_dia = cap_hm_dia
        turma_nome = f"MEC_AUTO_{_slug_ficheiro_seguro(atv, max_len=16)}"

        for item in itens:
            hm_rest = float(item.get("HM_total", 0) or 0)
            hm_ha_item = float(item.get("HM_ha", 0) or 0)
            while hm_rest > 0.0001:
                if saldo_hm_dia <= 0.0001:
                    dia += 1
                    saldo_hm_dia = cap_hm_dia
                hm_exec = min(hm_rest, saldo_hm_dia)
                hm_rest -= hm_exec
                saldo_hm_dia -= hm_exec
                area_exec = (hm_exec / hm_ha_item) if hm_ha_item > 0.0001 else 0.0
                cronograma.append(
                    {
                        "Dia": int(dia),
                        "Fazenda": fazenda,
                        "Talhao": item["Talhao"],
                        "Atividade": item["Atividade"],
                        "Turma": turma_nome,
                        "Operarios": 1,
                        "HH": round(hm_exec, 2),
                        "HM": round(hm_exec, 2),
                        "Modo": "MecanizadoAutoHM",
                        "Origem_Mec": "HM_Tarifa",
                        "Area_ha": round(area_exec, 4),
                    }
                )

    cronograma = sorted(
        cronograma, key=lambda r: (int(r.get("Dia", 0)), str(r.get("Turma", "")))
    )
    return cronograma, recursos_auto


def construir_cronograma_humano_sem_mecanizadas(
    cronograma_base, turmas, jornada, executores, atividades_mec
):
    """Remove atividades assumidas por mecanizados do cronograma humano e recompoe dias."""
    turmas_ops = {t["nome"]: int(t["operarios"]) for t in turmas}
    por_turma = defaultdict(list)
    for c in cronograma_base:
        atv = str(c.get("Atividade", ""))
        if atv in atividades_mec:
            continue
        por_turma[str(c.get("Turma", ""))].append(dict(c))
    novo = []
    for nm_turma, itens in por_turma.items():
        if not itens:
            continue
        n_ops = (
            int(executores)
            if nm_turma == "Pelotao_Unificado"
            else int(turmas_ops.get(nm_turma, 1))
        )
        cap_dia = max(0.01, float(n_ops) * float(jornada))
        dia = 1
        saldo = cap_dia
        for it in itens:
            hh_rest = float(it.get("HH", 0) or 0)
            if hh_rest <= 0.01:
                continue
            while hh_rest > 0.01:
                if saldo <= 0.01:
                    dia += 1
                    saldo = cap_dia
                cons = min(hh_rest, saldo)
                hh_rest -= cons
                saldo -= cons
                row = dict(it)
                row["Dia"] = dia
                row["HH"] = round(cons, 2)
                c_old = float(it.get("Custo_MO", 0) or 0)
                hh_old = float(it.get("HH", 0) or 0)
                row["Custo_MO"] = (
                    round((cons / hh_old) * c_old, 2) if hh_old > 0.01 else 0.0
                )
                novo.append(row)
    return sorted(novo, key=lambda r: (int(r.get("Dia", 0)), str(r.get("Turma", ""))))
