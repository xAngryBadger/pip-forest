"""Multi-factor simulation and scenario rendering."""

from ..logging_config import get_logger

logger = get_logger(__name__)

from ..comparativo_mec import simular_cenarios_multifator
from ..ui import (
    BL, C, DM, G, RS, Y,
    console, confirmar, selecionar, sub, Table,
)


def _render_tabela_cenarios(rows, label):
    if not rows:
        return
    t_sc = Table(title=f"Comparativo de Cenários (Equipe x Jornada) - {label}")
    t_sc.add_column("Equipe", justify="right")
    t_sc.add_column("Jornada", justify="right")
    t_sc.add_column("Dias", justify="right")
    t_sc.add_column("Meses", justify="right")
    t_sc.add_column("Ganho vs Meta", justify="right")
    for r in rows[:40]:
        t_sc.add_row(
            str(r["Equipe"]),
            f"{r['Jornada_h_dia']:.2f}",
            str(r["Dias_Simulados"]),
            f"{r['Meses_Simulados']:.2f}",
            f"{r['Ganho_vs_Meta_dias']:+d}",
        )
    console.print(t_sc)


def _executar_multi_fator_simulation(comparativo_cfg, _batch, recursos_mec, cronograma_com_mec, total_hh, dias_meta, executores, jornada):
    cenarios_rows = []
    if comparativo_cfg is not None and isinstance(comparativo_cfg, dict):
        hh_base_multi = float(total_hh)
        lbl_base_multi = "Sem mecanizado"
        if (not _batch) and recursos_mec and cronograma_com_mec:
            hh_hum_pos_mec = sum(
                float(x.get("HH", 0) or 0)
                for x in cronograma_com_mec
                if not str(x.get("Turma", "")).startswith("MEC_")
            )
            base_opt = selecionar(
                "BASE DO COMPARATIVO MULTI-FATOR",
                ["Sem mecanizado (HH total atual)", "Com mecanizado (HH humano remanescente)"],
            )
            if base_opt and base_opt.startswith("Com mecanizado"):
                hh_base_multi = float(hh_hum_pos_mec)
                lbl_base_multi = "Com mecanizado"
        logger.debug(f"Base selecionada: {lbl_base_multi} | HH={hh_base_multi:.1f}")
        cenarios_rows = simular_cenarios_multifator(
            total_hh=hh_base_multi, dias_meta=dias_meta,
            executores_base=executores, jornada_base=jornada,
            jornadas_in=comparativo_cfg.get("jornadas"),
            equipes_in=comparativo_cfg.get("equipes"),
            interativo=False,
        )
        _render_tabela_cenarios(cenarios_rows, lbl_base_multi)

    if not _batch:
        while confirmar("Recalcular comparativo multi-fator com novos valores agora?", default=False):
            hh_base_multi = float(total_hh)
            lbl_base_multi = "Sem mecanizado"
            if recursos_mec and cronograma_com_mec:
                hh_hum_pos_mec = sum(
                    float(x.get("HH", 0) or 0)
                    for x in cronograma_com_mec
                    if not str(x.get("Turma", "")).startswith("MEC_")
                )
                base_opt = selecionar(
                    "BASE DO COMPARATIVO MULTI-FATOR",
                    ["Sem mecanizado (HH total atual)", "Com mecanizado (HH humano remanescente)"],
                )
                if base_opt and base_opt.startswith("Com mecanizado"):
                    hh_base_multi = float(hh_hum_pos_mec)
                    lbl_base_multi = "Com mecanizado"
        logger.debug(f"Base selecionada: {lbl_base_multi} | HH={hh_base_multi:.1f}")
        cenarios_rows = simular_cenarios_multifator(
            total_hh=hh_base_multi, dias_meta=dias_meta,
            executores_base=executores, jornada_base=jornada,
            jornadas_in=comparativo_cfg.get("jornadas") if isinstance(comparativo_cfg, dict) else None,
            equipes_in=comparativo_cfg.get("equipes") if isinstance(comparativo_cfg, dict) else None,
            interativo=True,
        )
        _render_tabela_cenarios(cenarios_rows, lbl_base_multi)
    return cenarios_rows
