"""Generate FORMOSA stats for CONTAS_EXEMPLO_FORMOSA.md."""
import csv, os, sys
import pandas as pd
import json

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import atm_v5 as srf

cfg = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
tarifas = cfg["tarifas"]
de_para = {k: v for k, v in cfg.get("de_para", {}).items() if not str(k).startswith("_")}

df = pd.read_excel(os.path.join(ROOT, "exame.xlsx"), sheet_name="MICROPLANEJAMENTO_ABRIL_JUNHO")
cols = df.columns.tolist()
d = df[
    [
        srf.encontrar_coluna(cols, "fazenda"),
        srf.encontrar_coluna(cols, "chave"),
        srf.encontrar_coluna(cols, "area"),
        srf.encontrar_coluna(cols, "atividade"),
    ]
].copy()
d.columns = ["fazenda", "chave", "area_ha", "atividade"]
d = d.dropna(subset=["fazenda", "atividade", "area_ha"])
d["area_ha"] = pd.to_numeric(d["area_ha"], errors="coerce").fillna(0)
d = d[d["area_ha"] > 0]

f = d[d["fazenda"].astype(str).str.strip() == "FORMOSA"].copy().sort_values(["chave", "atividade"])
rows = []
total_hh = 0.0
total_rec = 0.0
for _, row in f.iterrows():
    atv = str(row["atividade"]).strip()
    th = str(row["chave"]).strip()
    area = float(row["area_ha"])
    ch = de_para.get(atv, atv)
    tr = tarifas.get(ch, {})
    rh = float(tr.get("rendimento_hh", 0) or 0)
    pr = float(tr.get("preco_ha", 0) or 0)
    hh = area * rh
    rec = area * pr
    total_hh += hh
    total_rec += rec
    rows.append([th, atv, area, ch, rh, pr, hh, rec])

out = os.path.join(ROOT, "_formosa_detail.csv")
with open(out, "w", newline="", encoding="utf-8") as fp:
    w = csv.writer(fp, delimiter=";")
    w.writerow(
        ["talhao", "atividade_micro", "area_ha", "chave_CT", "hh_ha", "preco_ha", "HH_linha", "receita_linha"]
    )
    w.writerows(rows)

execs = 9
j = 4.3
cap = execs * j
dias_min = total_hh / cap if cap else 0
meses_min = dias_min / 22.0

print("FORMOSA lines:", len(rows))
print("total_HH:", round(total_hh, 2))
print("total_receita:", round(total_rec, 2))
print("9 exec x 4.3h cap/dia:", round(cap, 2))
print("dias_min_paralelo:", round(dias_min, 2))
print("meses_22du:", round(meses_min, 3))

# --- Headless scheduler (same logic as atm_v5 loop): FORMOSA, 9 exec, 5+4, j=4.3
from collections import OrderedDict, defaultdict

cfg2 = {"tarifas": tarifas, "de_para": de_para, "filtros_bloqueio_global": ["plantio", "irrig"]}
acts = sorted(f["atividade"].dropna().unique().tolist())
th_ord = sorted(f["chave"].dropna().unique().tolist())
strict = True
demandas = OrderedDict()
for talhao in th_ord:
    tarefas = []
    for _, row in f[f["chave"] == talhao].iterrows():
        atv = row["atividade"]
        area = float(row["area_ha"])
        t_nome = de_para.get(atv, atv)
        rb = srf.resolver_rendimento_hh(cfg2, tarifas, t_nome, strict=strict)
        horas = area * float(rb)
        tarefas.append({"atividade": atv, "hh_total": horas})
    demandas[talhao] = tarefas

executores = 9
jornada = 4.3
turmas = [
    {"nome": "Roca", "operarios": 5, "atividades": []},
    {"nome": "Outra", "operarios": 4, "atividades": []},
]

def is_roca(a):
    x = srf.remover_acentos(str(a)).lower()
    return any(k in x for k in ["rocada", "limpeza", "preparo", "coveamento", "nucleacao", "conducao"])

for atv in acts:
    if is_roca(atv):
        turmas[0]["atividades"].append(atv)
    else:
        turmas[1]["atividades"].append(atv)
all_v = set()
for t in turmas:
    all_v.update(t["atividades"])
for atv in acts:
    if atv not in all_v:
        turmas[1]["atividades"].append(atv)

reatribuicao, paralelo, primaria = {}, {}, {}
demanda_global = {}
for talhao, tarefas in demandas.items():
    for t in tarefas:
        demanda_global[(talhao, t["atividade"])] = t["hh_total"]

bloq = set(srf.atividades_por_filtro(acts, cfg2["filtros_bloqueio_global"]))
use_bloq = use_ref = use_pool = True

turma_filas = {}
for turma in turmas:
    fila = []
    for talhao in th_ord:
        for tarefa in demandas.get(talhao, []):
            atv = tarefa["atividade"]
            if tarefa["hh_total"] > 0.01 and turma["nome"] in srf.turmas_que_executam(
                atv, turmas, reatribuicao, paralelo, primaria
            ):
                fila.append({"talhao": talhao, "atividade": atv})
    turma_filas[turma["nome"]] = fila

dia = 0
MAX_D = 50000
while dia < MAX_D:
    if not any(v > 0.01 for v in demanda_global.values()):
        break
    dia += 1
    pool_only = use_bloq and use_pool and srf._somente_bloqueado_restante(demanda_global, bloq)
    if pool_only:
        cap_pool = float(executores) * float(jornada)
        while cap_pool > 0.01:
            fez = False
            for talhao in th_ord:
                for t in demandas.get(talhao, []):
                    atv = t["atividade"]
                    if atv not in bloq:
                        continue
                    key = (talhao, atv)
                    rest = demanda_global.get(key, 0.0)
                    if rest <= 0.01:
                        continue
                    c = min(rest, cap_pool)
                    demanda_global[key] -= c
                    cap_pool -= c
                    fez = True
                    if cap_pool <= 0.01:
                        break
                if cap_pool <= 0.01:
                    break
            if not fez:
                break
        for turma in turmas:
            fila = turma_filas[turma["nome"]]
            while fila and demanda_global.get((fila[0]["talhao"], fila[0]["atividade"]), 0) < 0.01:
                fila.pop(0)
        continue

    for turma in turmas:
        fila = turma_filas[turma["nome"]]
        n_ops = turma["operarios"]
        cap_dia = n_ops * jornada
        idx = 0
        while cap_dia > 0.01 and idx < len(fila):
            item = fila[idx]
            key = (item["talhao"], item["atividade"])
            rest = demanda_global.get(key, 0)
            if rest < 0.01:
                idx += 1
                continue
            if use_bloq and item["atividade"] in bloq:
                if srf._ha_trabalho_nao_bloqueado(demanda_global, bloq):
                    idx += 1
                    continue
            c = min(rest, cap_dia)
            demanda_global[key] -= c
            cap_dia -= c
            if demanda_global[key] < 0.01:
                idx += 1
        while fila and demanda_global.get((fila[0]["talhao"], fila[0]["atividade"]), 0) < 0.01:
            fila.pop(0)
        if use_ref and cap_dia > 0.01:
            for talhao in th_ord:
                if cap_dia <= 0.01:
                    break
                for t in demandas.get(talhao, []):
                    atv = t["atividade"]
                    kr = (talhao, atv)
                    rr = demanda_global.get(kr, 0.0)
                    if rr <= 0.01:
                        continue
                    if use_bloq and atv in bloq:
                        continue
                    cr = min(rr, cap_dia)
                    demanda_global[kr] -= cr
                    cap_dia -= cr

print("dias_simulado_9exec:", dia)
print("meses_sim_app:", round(dia / 22.0, 2))

