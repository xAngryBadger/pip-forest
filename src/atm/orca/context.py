"""
Orca session context — ContextoSessao class and dashboard display.

The ContextoSessao singleton stores all important session choices
for display in the dashboard. It is the main shared mutable state
of the application.

Dependencies: orca.monitor (for init_monitor injection)
External: rich (Console, Table), datetime
"""

import datetime

try:
    from rich.console import Console
    from rich.table import Table
except ImportError:
    Console = None
    Table = None


class ContextoSessao:
    """Armazena todas as escolhas importantes durante a sessao para exibicao no dashboard."""

    def __init__(self):
        self.fazenda_selecionada = None
        self.equipe_selecionada = None
        self.talhoes_selecionados = []
        self.total_talhoes_fazenda = 0
        self.area_total_fazenda = 0.0
        self.data_inicio = None
        self.data_termino = None
        self.atividades_distribuidas = 0
        self.total_atividades = 0
        self.modo_atual = None
        self.orcamento_estrito = True
        self.tarifas_carregadas = 0
        self.timestamp_atualizacao = None
        self._console = Console() if Console else None

    def atualizar_fazenda(self, nome_fazenda, df_fazenda=None):
        """Atualiza informacoes da fazenda selecionada."""
        self.fazenda_selecionada = nome_fazenda
        if df_fazenda is not None:
            self.total_talhoes_fazenda = (
                df_fazenda["chave"].nunique() if "chave" in df_fazenda.columns else 0
            )
            if "area" in df_fazenda.columns:
                self.area_total_fazenda = df_fazenda["area"].sum()
            elif "area_ha" in df_fazenda.columns:
                self.area_total_fazenda = df_fazenda["area_ha"].sum()
            else:
                self.area_total_fazenda = 0.0
        else:
            self.total_talhoes_fazenda = 0
            self.area_total_fazenda = 0.0
        self.timestamp_atualizacao = datetime.datetime.now()

    def atualizar_equipe(self, nome_equipe):
        """Atualiza equipe selecionada."""
        self.equipe_selecionada = nome_equipe
        self.timestamp_atualizacao = datetime.datetime.now()

    def definir_escopo_talhoes(self, talhoes_selecionados, todos_talhoes):
        """Define os talhoes selecionados e atualiza metadados."""
        self.talhoes_selecionados = (
            list(set(talhoes_selecionados))
            if isinstance(talhoes_selecionados, list)
            else []
        )
        self.total_talhoes_fazenda = (
            len(set(todos_talhoes)) if isinstance(todos_talhoes, list) else 0
        )
        self.timestamp_atualizacao = datetime.datetime.now()

    def atualizar_atividades(self, distribuidas, total):
        """Atualiza contagem de atividades distribuidas vs total."""
        self.atividades_distribuidas = distribuidas
        self.total_atividades = total
        self.timestamp_atualizacao = datetime.datetime.now()

    def definir_datas(self, inicio, termino):
        """Define datas de inicio e termino da operacao."""
        self.data_inicio = inicio
        self.data_termino = termino
        self.timestamp_atualizacao = datetime.datetime.now()

    def atualizar_modo(self, modo):
        """Atualiza o modo atual (single, lote, multi_equipe)."""
        self.modo_atual = modo
        self.timestamp_atualizacao = datetime.datetime.now()

    def atualizar_configuracoes(self, cfg):
        """Atualiza configuracoes importantes do sistema."""
        self.orcamento_estrito = (
            cfg.get("orcamento_estrito", True) if isinstance(cfg, dict) else True
        )
        self.tarifas_carregadas = (
            len(cfg.get("tarifas", {})) if isinstance(cfg, dict) else 0
        )
        self.timestamp_atualizacao = datetime.datetime.now()

    def limpar_contexto(self):
        """Limpa o contexto para iniciar nova sessao."""
        self.__init__()

    def _criar_tabela_dashboard(self):
        """Cria a tabela Rich formatada com informacoes do contexto."""
        if Table is None:
            return None
        table = Table(
            title="[bold cyan]Dashboard de Contexto[/bold cyan]",
            show_header=True,
            header_style="bold cyan",
            border_style="bright_blue",
            padding=(0, 1),
        )

        table.add_column("Fazenda", style="bold green", width=30, justify="left")
        table.add_column("Equipe", style="bold yellow", width=20, justify="left")
        table.add_column("Talhoes", style="bold blue", width=15, justify="center")
        table.add_column(
            "Atividades", style="bold magenta", width=15, justify="center"
        )
        table.add_column("Datas", style="bold red", width=25, justify="left")

        # Preparar dados de cada coluna
        fazenda_info = "[dim]Nao selecionada[/dim]"
        if self.fazenda_selecionada:
            fazenda_info = f"[bold green]{self.fazenda_selecionada}[/bold green]"
            meta_parts = []
            if self.total_talhoes_fazenda > 0:
                qtd_talhoes = (
                    len(self.talhoes_selecionados)
                    if self.talhoes_selecionados
                    else self.total_talhoes_fazenda
                )
                meta_parts.append(f"{qtd_talhoes}/{self.total_talhoes_fazenda} talhoes")
            if self.area_total_fazenda > 0:
                meta_parts.append(f"{self.area_total_fazenda:,.1f}ha")
            if meta_parts:
                fazenda_info += f"\n[dim]{' | '.join(meta_parts)}[/dim]"

        equipe_info = self.equipe_selecionada or "[dim]Nao selecionada[/dim]"

        talhoes_info = "[dim]0/0[/dim]"
        if self.total_talhoes_fazenda > 0:
            qtd = (
                len(self.talhoes_selecionados)
                if self.talhoes_selecionados
                else self.total_talhoes_fazenda
            )
            talhoes_info = f"[bold]{qtd}/{self.total_talhoes_fazenda}[/bold]"

        atividades_info = "[dim]0/0[/dim]"
        if self.total_atividades > 0:
            atividades_info = (
                f"[bold]{self.atividades_distribuidas}/{self.total_atividades}[/bold]"
            )

        datas_info = "[dim]Nao definidas[/dim]"
        if self.data_inicio or self.data_termino:
            datas_parts = []
            if self.data_inicio:
                datas_parts.append(f"Inicio: {self.data_inicio}")
            if self.data_termino:
                datas_parts.append(f"Termino: {self.data_termino}")
            datas_info = "\n".join(datas_parts)

        # Adicionar linha principal
        table.add_row(
            fazenda_info, equipe_info, talhoes_info, atividades_info, datas_info
        )

        # Segunda linha com informacoes adicionais (se houver)
        info_adicional = []
        if self.modo_atual:
            info_adicional.append(
                f"[cyan]Modo:[/cyan] [white]{self.modo_atual}[/white]"
            )
        if self.tarifas_carregadas > 0:
            info_adicional.append(
                f"[cyan]Tarifas:[/cyan] [white]{self.tarifas_carregadas}[/white]"
            )
        if not self.orcamento_estrito:
            info_adicional.append("[cyan]Orcamento:[/cyan] [white]Flexivel[/white]")

        if info_adicional:
            table.add_row(
                "\n" + "\n".join(info_adicional), "", "", "", "", end_section=True
            )

        return table

    def exibir(self, console_inst=None, mostrar_sempre=True):
        """Exibe o dashboard formatado no console."""
        if not mostrar_sempre and not self.fazenda_selecionada:
            return

        c = console_inst or self._console
        if c is None:
            return
        table = self._criar_tabela_dashboard()
        if table:
            c.print("\n", table, "\n")


# ──────────────────────────────────────────────
# GLOBAL SINGLETON
# ──────────────────────────────────────────────
contexto_sessao = ContextoSessao()


def dashboard_header(console_inst=None, mostrar_sempre=True):
    """Wrapper para exibir o dashboard (mantem compatibilidade com chamadas existentes)."""
    contexto_sessao.exibir(console_inst, mostrar_sempre)
