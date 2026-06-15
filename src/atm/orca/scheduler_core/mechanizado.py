"""Optional mechanized mode execution."""

import math
from collections import defaultdict

from ..logging_config import get_logger

logger = get_logger(__name__)

from ..cronograma import (
    construir_cronograma_humano_sem_mecanizadas,
    construir_cronograma_mecanizado,
)
from ..turmas import _cadastrar_recursos_mecanizados_sn
from ..ui import (
    BL, C, DM, G, RS,
    confirmar, console, sub, Table,
)


def _executar_modo_mecanizado_opcional(
    _batch, modo_comparativo, substituicoes_comparativo,
    atividades_reais, cfg, hm_only_list, catalogo_global,
    demandas, fazenda, jornada, cronograma, turmas, executores,
    cronograma_base, cronograma_mec_base, dias_simulado,
):
    recursos_mec = []
    cronograma_mec = []
    cronograma_com_mec = []
    atividades_mec_set = set()
    if _batch:
        sub()
        logger.debug("Modo batch: pulando 'modo mecanizado opcional' (sem prompts interativos).")
    elif modo_comparativo and substituicoes_comparativo:
        sub()
        logger.debug("Comparativo MANUAL vs MECANIZADO ativo: pulando 'modo mecanizado opcional' para evitar duplicidade de cenarios.")
    else:
        sub()
        logger.info("ATIVAR MODO MECANIZADO")
        logger.debug("Cenario opcional: cadastrar recurso extra para adicionar/substituir atividades.")
        if cronograma_mec_base:
            logger.debug("As atividades HM do orcamento ja foram contabilizadas automaticamente no cronograma base.")
            for a in hm_only_list[:5]:
                logger.debug(f"    - {str(a)[:58]}")
            if len(hm_only_list) > 5:
                logger.debug(f"    ... +{len(hm_only_list) - 5}")
        if hm_only_list:
            logger.debug(f"HM-only (HH=0) detectadas: {len(hm_only_list)} atividade(s).")
        if confirmar("  Ativar modo mecanizado opcional?", default=False):
            recursos_mec = _cadastrar_recursos_mecanizados_sn(
                atividades_reais, cfg, atividades_catalogo=catalogo_global,
            )
            for rec in recursos_mec:
                atividades_mec_set.update(rec.get("atividades", set()))
            if recursos_mec and atividades_mec_set:
                cronograma_mec = construir_cronograma_mecanizado(
                    demandas, fazenda, jornada, recursos_mec
                )

            if cronograma_mec and atividades_mec_set:
                regra_implantacao_mec = "substituir_total"
                if confirmar(
                    "Regra de implantacao mecanizado: manter humano em PARALELO nas atividades mecanizadas?",
                    default=False,
                ):
                    regra_implantacao_mec = "paralelo"
                if regra_implantacao_mec == "paralelo":
                    crono_hum_sem_mec = [dict(x) for x in cronograma_base]
                else:
                    crono_hum_sem_mec_h = construir_cronograma_humano_sem_mecanizadas(
                        cronograma, turmas, jornada, executores, atividades_mec_set
                    )
                    crono_hum_sem_mec = sorted(
                        crono_hum_sem_mec_h + cronograma_mec_base,
                        key=lambda r: (int(r.get("Dia", 0)), str(r.get("Turma", ""))),
                    )
                cronograma_com_mec = sorted(
                    crono_hum_sem_mec + cronograma_mec,
                    key=lambda r: (int(r.get("Dia", 0)), str(r.get("Turma", ""))),
                )
                d_hum = max([int(x.get("Dia", 0)) for x in crono_hum_sem_mec], default=0)
                d_mec = max([int(x.get("Dia", 0)) for x in cronograma_mec], default=0)
                d_comb = max(d_hum, d_mec)
                t_mec = Table(title="Comparativo Operacional - Modo Mecanizado")
                t_mec.add_column("Metrica", style="cyan")
                t_mec.add_column("Valor", justify="right")
                t_mec.add_row("Dias baseline (cronograma base)", str(dias_simulado))
                t_mec.add_row("Dias base sem atividades opcionais", str(d_hum))
                t_mec.add_row("Dias recursos mecanizados (filas dedicadas)", str(d_mec))
                t_mec.add_row("Dias cenario combinado (humano || mecanizado)", str(d_comb))
                t_mec.add_row("Ganho de prazo (dias)", f"{int(dias_simulado) - int(d_comb):+d}")
                t_mec.add_row("Regra mecanizada", regra_implantacao_mec)
                for rec in recursos_mec:
                    t_mec.add_row(
                        f"  Recurso: {rec['nome']}", f"{rec['prod_ha_h']} ha/h",
                    )
                    t_mec.add_row(
                        f"  Atividades ({rec['nome']})",
                        str(len(rec.get("atividades", set()))),
                    )
                hm_mec_total = sum(
                    float(x.get("HM", x.get("HH", 0)) or 0) for x in cronograma_mec
                )
                t_mec.add_row("Horas mecanizadas (HM)", f"{hm_mec_total:.1f}")
                console.print(t_mec)

                t_alt = Table(title="Cronograma Alternativo (Humano + Mecanizado)")
                t_alt.add_column("Semana", justify="center", style="cyan")
                t_alt.add_column("Dias", justify="center")
                t_alt.add_column("Acoes", style="green")
                sem_alt = defaultdict(lambda: {"dias": set(), "acoes": set()})
                for c in cronograma_com_mec:
                    s = (int(math.ceil(float(c.get("Dia", 0)) / 5.0)) if c.get("Dia") else 0)
                    if s <= 0:
                        continue
                    sem_alt[s]["dias"].add(int(c["Dia"]))
                    txt = f"[{str(c.get('Talhao', ''))[:18]}] {str(c.get('Atividade', ''))[:18]} ({c.get('Turma', '')})"
                    sem_alt[s]["acoes"].add(txt)
                for s in sorted(sem_alt.keys())[:8]:
                    d = sem_alt[s]
                    dias_str = f"Dia {min(d['dias'])} a {max(d['dias'])}"
                    acoes = ", ".join(list(d["acoes"])[:3])
                    if len(d["acoes"]) > 3:
                        acoes += " (+)"
                    t_alt.add_row(f"Sem {s}", dias_str, acoes)
                console.print(t_alt)
    return recursos_mec, cronograma_mec, cronograma_com_mec, atividades_mec_set
