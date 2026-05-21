#!/usr/bin/env python3
"""
Monitor CLI read-only: le estado_sessao_<pid>.json gerado pelo atm_v5.py.
Visual alinhado ao atm_v5 (ASCII, cores, Rich).

Uso:
  python srf_monitor.py --feed meta --pid <PID>
  python srf_monitor.py --feed rendimentos --pid <PID>
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
import time
from typing import Any

from orca_monitor_state import default_state_path, ler_estado
from rich.console import Console
from rich.table import Table

try:
    import colorama

    colorama.init()
    G = "\033[92m"
    Y = "\033[93m"
    R = "\033[91m"
    C = "\033[96m"
    DM = "\033[2m"
    BL = "\033[1m"
    RS = "\033[0m"
except ImportError:
    G = Y = R = C = DM = BL = RS = ""

W = 66
console = Console()

ASCII_ART = r"""
        ,@@@@@@@,
    ,,,.   ,@@@@@@/@@,  .oo8888o.
 ,&%%&%&&%,@@@@@/@@@@@@,8888\88/8o
,%&\%&&%&&%,@@@\@@@/@@@88\88888/88'
%&&%&%&/%&&%@@\@@/ /@@@88888\88888'
%&&%/ %&%%&&@@\ V /@@' `88\8 `/88'
`&%\ ` /%&'    |.|        \ '|8'
    |o|        | |         | |
    |.|        | |         | |
 \\/ ._\//_/__/  ,\_//__\\/.  \_//__/_
"""


def linha(ch="="):
    print(G + ch * W + RS)


def sub(ch="-"):
    print(DM + ch * W + RS)


def _resolver_pid_explicito(pid: int | None) -> int | None:
    if pid is not None:
        return pid
    raw = os.environ.get("ORCA_MONITOR_PID", "").strip()
    if raw.isdigit():
        return int(raw)
    return None


def _resolver_pid_auto() -> int | None:
    pattern = os.path.join(os.path.dirname(os.path.abspath(__file__)), "estado_sessao_*.json")
    cands = glob.glob(pattern)
    if len(cands) != 1:
        return None
    base = os.path.basename(cands[0])
    try:
        part = base.replace("estado_sessao_", "").replace(".json", "")
        return int(part)
    except ValueError:
        return None


def _cabecalho_monitor(feed_label: str, pid: int, path: str):
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")
    print(G + ASCII_ART + RS)
    linha()
    print(G + BL + f"  [ SRF MONITOR ]  {feed_label}".center(W) + RS)
    print(DM + f"  PID {pid}  |  {os.path.basename(path)}".center(W) + RS)
    linha()
    sub()


def _render_meta(d: dict[str, Any]):
    op = d.get("operacao") or {}
    lo = d.get("lote") or {}
    t = Table(title="Operacao / meta", show_header=True, header_style="bold cyan")
    t.add_column("Campo", style="dim")
    t.add_column("Valor", style="white")
    t.add_row("timestamp", str(d.get("timestamp_iso", "?")))
    t.add_row("fazenda_atual", str(op.get("fazenda_atual", "?")))
    t.add_row("modo", str(op.get("modo", "?")))
    t.add_row("micro", str(op.get("micro_basename", "?")))
    t.add_row("status", str(op.get("status_geral", "?")))
    t.add_row("equipe_atual", str(op.get("equipe_atual", "-")))
    t.add_row("mensagem", str(op.get("mensagem_curta", "-")))
    console.print(t)
    t2 = Table(title="Lote (continuo / multi)", show_header=True, header_style="bold cyan")
    t2.add_column("Campo", style="dim")
    t2.add_column("Valor", style="white")
    t2.add_row("dias_meta", str(lo.get("dias_meta", "?")))
    t2.add_row("dias_consumidos", str(lo.get("dias_consumidos", "?")))
    t2.add_row("saldo_dias", str(lo.get("saldo_dias", "?")))
    t2.add_row("fazenda_indice", f"{lo.get('fazenda_indice', '?')}/{lo.get('n_fazendas', '?')}")
    t2.add_row("status_meta_continuo", str(lo.get("status_meta_continuo", "-")))
    t2.add_row("prazo_absoluto", str(lo.get("prazo_absoluto", "-")))
    console.print(t2)


def _render_rendimentos(d: dict[str, Any]):
    rows = d.get("rendimentos_sessao") or []
    t = Table(
        title="Rendimentos (agregado por atividade)",
        show_header=True,
        header_style="bold cyan",
    )
    t.add_column("Atividade", max_width=48, overflow="ellipsis")
    t.add_column("hh_ha", justify="right")
    t.add_column("origem", max_width=12)
    t.add_column("tarifa", max_width=22, overflow="ellipsis")
    if not rows:
        console.print(DM + "  (vazio — antes das demandas ou sessao sem dados)" + RS)
        return
    for r in rows:
        t.add_row(
            str(r.get("atividade", "")),
            f"{float(r.get('hh_ha', 0) or 0):.2f}",
            str(r.get("origem", ""))[:12],
            str(r.get("chave_tarifa", ""))[:22],
        )
    console.print(t)


def _render_relatorios(d: dict[str, Any]):
    buf = d.get("buffer_relatorios") or []
    if not buf:
        console.print(DM + "  (sem entradas no buffer)" + RS)
        return
    for b in buf[-12:]:
        console.print(Y + f"--- {b.get('titulo', '')} ---" + RS)
        console.print(DM + str(b.get("texto", ""))[:6000] + RS)
        console.print()


def _render_custo(d: dict[str, Any]):
    """Renderiza feed de custos acumulados"""
    custos = d.get("custos_acumulados") or {}

    if not custos:
        console.print(DM + " (custos ainda não calculados)" + RS)
        return

    t = Table(title="💰 Custos Acumulados", show_header=True, header_style="bold yellow")
    t.add_column("Categoria", style="cyan", width=25)
    t.add_column("Valor (R$)", justify="right", style="white")
    t.add_column("Itens", style="dim", width=15)

    categorias = [
        ("total_geral", "TOTAL GERAL"),
        ("materiais", "Materiais"),
        ("mao_de_obra", "Mão de Obra"),
        ("equipamentos", "Equipamentos"),
        ("frentes", "Frentes/Equipes"),
    ]

    for key, label in categorias:
        if key in custos:
            val = custos[key]
            itens = len(custos.get(f"{key}_detalhes", []))
            t.add_row(label, f"R$ {float(val):,.2f}", f"{itens} itens")

    console.print(t)

    # Detalhes por fazenda
    detalhes_fazendas = custos.get("detalhes_por_fazenda", [])
    if detalhes_fazendas:
        t2 = Table(title="Custos por Fazenda", show_header=True, header_style="bold cyan")
        t2.add_column("Fazenda", style="green", max_width=30)
        t2.add_column("Custo Total", justify="right", style="white")
        t2.add_column("Custo/ha", justify="right", style="yellow")
        t2.add_column("Status", max_width=15)

        # Mostra top 10
        for faz in detalhes_fazendas[:10]:
            t2.add_row(
                str(faz.get('nome', '?'))[:28],
                f"R$ {float(faz.get('custo_total', 0)):,.2f}",
                f"R$ {float(faz.get('custo_ha', 0)):,.2f}",
                str(faz.get('status', '-'))
            )

        if len(detalhes_fazendas) > 10:
            t2.add_row(
                DM + f"... +{len(detalhes_fazendas)-10} fazenda(s)",
                "-", "-", "-"
            )

        console.print(t2)


def _render_territorio(d: dict[str, Any]):
    """Renderiza feed de distribuição geográfica por território"""
    territorio = d.get("distribuicao_territorio") or {}

    if not territorio:
        console.print(DM + " (distribuição territorial não carregada)" + RS)
        return

    t = Table(title="🗺️ Distribuição Territorial", show_header=True, header_style="bold cyan")
    t.add_column("Cidade/Região", style="green", width=20)
    t.add_column("Fazendas", justify="center", style="white")
    t.add_column("Equipe Sugerida", style="yellow", width=15)
    t.add_column("Área Total (ha)", justify="right", style="magenta")

    # Agrupa por cidade
    distrib_por_cidade = {}
    for faz, info in territorio.items():
        cidade = info.get('cidade', 'Desconhecida')
        equipe = info.get('equipe_sugerida', '?')
        area = info.get('area_ha', 0)

        if cidade not in distrib_por_cidade:
            distrib_por_cidade[cidade] = {
                'fazendas': [],
                'equipes': [],
                'area_total': 0
            }

    distrib_por_cidade[cidade]['fazendas'].append(faz)
    if equipe not in distrib_por_cidade[cidade]['equipes']:
        distrib_por_cidade[cidade]['equipes'].append(equipe)
    distrib_por_cidade[cidade]['area_total'] += area

    # Ordena por área total (decrescente)
    sorted_cidades = sorted(
        distrib_por_cidade.items(),
        key=lambda x: x[1]['area_total'],
        reverse=True
    )

    for cidade, info in sorted_cidades[:20]:  # Top 20
        t.add_row(
            str(cidade).title(),
            str(len(info['fazendas'])),
            ", ".join(list(info['equipes'])[:2]),  # Mostra até 2 equipes
            f"{info['area_total']:,.1f}"
        )

    console.print(t)

    # Resumo por equipe
    resumo_equipe = {}
    for faz, info in territorio.items():
        equipe = info.get('equipe_sugerida', '?')
        if equipe not in resumo_equipe:
            resumo_equipe[equipe] = {'fazendas': 0, 'area': 0}
        resumo_equipe[equipe]['fazendas'] += 1
        resumo_equipe[equipe]['area'] += info.get('area_ha', 0)

    if resumo_equipe:
        t2 = Table(title="Resumo por Equipe", show_header=True, header_style="bold yellow")
        t2.add_column("Equipe", style="cyan", width=12)
        t2.add_column("Fazendas", justify="center")
        t2.add_column("Área Total (ha)", justify="right", style="green")
        t2.add_column("% Distribuição", justify="right")

        area_total = sum(v['area'] for v in resumo_equipe.values())
        for equipe, info in sorted(resumo_equipe.items(), key=lambda x: x[1]['area'], reverse=True):
            perc = (info['area'] / area_total * 100) if area_total > 0 else 0
            t2.add_row(
                str(equipe).upper(),
                str(info['fazendas']),
                f"{info['area']:,.1f}",
                f"{perc:.1f}%"
            )

        console.print(t2)


def main():
    ap = argparse.ArgumentParser(description="Monitor read-only do estado SRF v7")
    ap.add_argument("--feed", choices=("meta", "rendimentos", "relatorios", "custo", "territorio"), required=True)
    ap.add_argument("--pid", type=int, default=None)
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()

    pid = _resolver_pid_explicito(args.pid)
    if pid is None:
        pid = _resolver_pid_auto()
    if pid is None:
        print(
            "Indique o PID do atm_v5.py principal:\n"
            "  python srf_monitor.py --feed meta --pid <PID>\n"
            "ou ORCA_MONITOR_PID, ou um unico estado_sessao_*.json na pasta do projeto.",
            file=sys.stderr,
        )
        sys.exit(2)

    path = default_state_path(pid)
    labels = {
        "meta": "📊 Feed META (Operação + Lote)",
        "rendimentos": "⏱️ Feed RENDIMENTOS (HH/ha)",
        "relatorios": "📋 Feed RELATÓRIOS (Buffer)",
        "custo": "💰 Feed CUSTOS (Acumulado)",
        "territorio": "🗺️ Feed TERRITÓRIO (Distribuição)",
    }
    label = labels[args.feed]
    render_func_map = {
        "meta": _render_meta,
        "rendimentos": _render_rendimentos,
        "relatorios": _render_relatorios,
        "custo": _render_custo,
        "territorio": _render_territorio,
    }
    render = render_func_map.get(args.feed, _render_meta)

    while True:
        _cabecalho_monitor(label, pid, path)
        data = ler_estado(path)
        if not data:
            print(
                Y
                + f"  A aguardar estado em:\n  {path}\n"
                + "  (corra o atm_v5.py com ORCA_MONITOR=1 e execute o Smart Scheduler.)"
                + RS
            )
        else:
            try:
                render(data)
            except Exception as ex:
                print(R + f"  Erro ao renderizar: {ex}" + RS, file=sys.stderr)
        if args.once:
            break
        time.sleep(max(0.3, float(args.interval)))


if __name__ == "__main__":
    main()
