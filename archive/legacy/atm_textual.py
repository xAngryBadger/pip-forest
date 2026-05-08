#!/usr/bin/env python3
"""
SRF Textual v6.1
Interface EXATA do ATM 6.1 - Fluxo Linear
"""

import os
import sys
from datetime import datetime

DIR = os.path.dirname(os.path.abspath(__file__))
if DIR not in sys.path:
    sys.path.insert(0, DIR)

# Import do ATM 6.1
try:
    from atm_v6_1 import (
        carregar_config,
        salvar_config,
        carregar_planilha_microplanejamento,
        calcular_cronograma_inteligente,
        buscar_arquivos_excel,
        selecionar_arquivo,
        avaliar_terreno,
        normalizar_chave,
        parse_intervalos_escolha,
        ContextoSessao,
    )
    ATM_AVAILABLE = True
except ImportError as e:
    ATM_AVAILABLE = False
    print(f"Erro ao importar ATM: {e}")

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Select,
    Static,
)


# Estado global
class Estado:
    cfg = None
    df = None
    df_scope = None
    empresa_filtro = None
    fazenda = None
    talhoes_selecionados = []
    meta_escopo = None
    turmas = []
    atividades_reais = []
    atividades_catalogo = []
    config_calc = {}


def get_cfg():
    if Estado.cfg is None and ATM_AVAILABLE:
        Estado.cfg = carregar_config()
    return Estado.cfg or {}


def carregar_micro_default():
    """Carrega micro do config se existir."""
    cfg = get_cfg()
    micro_path = cfg.get("arquivo_micro")
    if micro_path and os.path.exists(micro_path) and ATM_AVAILABLE:
        try:
            Estado.df = carregar_planilha_microplanejamento(cfg, micro_path, modo_auto=True)
            return True
        except:
            pass
    return False


# ============= TELA INICIAL =============
class TelaInicial(Screen):
    """Tela inicial - carrega micro ou solicita."""
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container():
            yield Label("SRF - Sistema de Restauracao Florestal v6.1", classes="titulo")
            yield Label("")
            
            if not ATM_AVAILABLE:
                yield Static("ERRO: ATM 6.1 nao disponivel", classes="erro")
                yield Button("Sair", id="btn-sair", variant="error")
            else:
                yield Static("Carregando configuracoes...", id="status")
                yield Label("")
                yield Button("Iniciar", id="btn-iniciar", variant="success")
                yield Button("Trocar Micro", id="btn-trocar")
        yield Footer()
    
    def on_mount(self) -> None:
        carregar_micro_default()
        cfg = get_cfg()
        micro = cfg.get("arquivo_micro", "Nenhum")
        self.query_one("#status", Static).update(f"Micro atual: {os.path.basename(micro)}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-iniciar":
            if Estado.df is None:
                self.app.push_screen(TelaSelecionarMicro())
            else:
                self.app.push_screen(TelaFiltroEmpresa())
        elif event.button.id == "btn-trocar":
            self.app.push_screen(TelaSelecionarMicro())
        elif event.button.id == "btn-sair":
            self.app.exit()


# ============= TELA 1: SELECIONAR MICRO =============
class TelaSelecionarMicro(Screen):
    """Seleciona arquivo de microplanejamento."""
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container():
            yield Label("Selecionar Microplanejamento", classes="titulo")
            yield Label("")
            yield Label("Arquivos Excel encontrados:")
            
            with ListView(id="lista-arquivos"):
                if ATM_AVAILABLE:
                    try:
                        arquivos = buscar_arquivos_excel()
                        for i, arq in enumerate(arquivos[:20]):
                            nome = os.path.basename(arq)
                            yield ListItem(Label(nome), id=f"arq-{i}")
                            Estado.config_temp = getattr(Estado, 'config_temp', {})
                            Estado.config_temp[f"arq-{i}"] = arq
                    except:
                        yield ListItem(Label("Nenhum arquivo encontrado"))
                else:
                    yield ListItem(Label("ATM nao disponivel"))
            
            yield Label("")
            yield Label("Ou digite o caminho:")
            yield Input(placeholder="/caminho/micro.xlsx", id="input-caminho")
            
            with Horizontal():
                yield Button("Voltar", id="btn-voltar")
                yield Button("Carregar", id="btn-carregar", variant="success")
        yield Footer()
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id
        if item_id and item_id.startswith("arq-"):
            path = Estado.config_temp.get(item_id, "")
            if path:
                self._carregar(path)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-voltar":
            self.app.pop_screen()
        elif event.button.id == "btn-carregar":
            path = self.query_one("#input-caminho", Input).value
            if path:
                self._carregar(path)
    
    def _carregar(self, path: str):
        if not ATM_AVAILABLE:
            self.notify("ATM nao disponivel", severity="error")
            return
        
        try:
            cfg = get_cfg()
            Estado.df = carregar_planilha_microplanejamento(cfg, path, modo_auto=True)
            cfg["arquivo_micro"] = path
            salvar_config(cfg)
            self.notify(f"Carregado: {os.path.basename(path)}")
            self.app.push_screen(TelaFiltroEmpresa())
        except Exception as e:
            self.notify(f"Erro: {e}", severity="error")


# ============= TELA 2: FILTRO EMPRESA/EQUIPE =============
class TelaFiltroEmpresa(Screen):
    """Filtra por empresa/equipe."""
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container():
            yield Label("Filtro por Empresa/Equipe", classes="titulo")
            yield Label("")
            
            if Estado.df is None or "equipe" not in Estado.df.columns:
                yield Static("Nenhuma equipe encontrada. Prosseguindo com todos os dados.")
                Estado.empresa_filtro = "TODAS"
                Estado.df_scope = Estado.df
                with Horizontal():
                    yield Button("Continuar", id="btn-continuar", variant="success")
                return
            
            equipes = sorted(Estado.df["equipe"].dropna().unique().tolist())
            num_equipes = len(equipes)
            
            yield Static(f"Encontradas {num_equipes} empresas/equipes:")
            yield Label("")
            
            with ListView(id="lista-equipes"):
                yield ListItem(Label("[TODAS]"), id="eq-todas")
                for i, eq in enumerate(equipes):
                    yield ListItem(Label(str(eq)), id=f"eq-{i}")
            
            with Horizontal():
                yield Button("Voltar", id="btn-voltar")
        yield Footer()
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id
        
        if item_id == "eq-todas":
            Estado.empresa_filtro = "TODAS"
            Estado.df_scope = Estado.df
        elif item_id and item_id.startswith("eq-"):
            idx = int(item_id.split("-")[1])
            equipes = sorted(Estado.df["equipe"].dropna().unique().tolist())
            Estado.empresa_filtro = equipes[idx]
            Estado.df_scope = Estado.df[Estado.df["equipe"] == Estado.empresa_filtro].copy()
        
        self.app.push_screen(TelaSelecionarFazenda())
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-voltar":
            self.app.pop_screen()


# ============= TELA 3: SELECIONAR FAZENDA =============
class TelaSelecionarFazenda(Screen):
    """Seleciona fazenda ou modo (todas/multi-equipes)."""
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container():
            yield Label("Selecione a Fazenda ou Modo", classes="titulo")
            yield Label("")
            
            if Estado.df_scope is None or Estado.df_scope.empty:
                yield Static("ERRO: Nenhum dado disponivel")
                yield Button("Voltar", id="btn-voltar")
                return
            
            fazendas = sorted(Estado.df_scope["fazenda"].unique().tolist())
            num_fazendas = len(fazendas)
            
            yield Static(f"Encontradas {num_fazendas} fazendas:")
            yield Label("")
            
            with ListView(id="lista-fazendas"):
                yield ListItem(Label("[TODAS AS FAZENDAS (equipe unica)]"), id="faz-todas")
                yield ListItem(Label("[MULTI-EQUIPES (carteiras separadas)]"), id="faz-multi")
                for i, faz in enumerate(fazendas):
                    yield ListItem(Label(str(faz)), id=f"faz-{i}")
            
            with Horizontal():
                yield Button("Voltar", id="btn-voltar")
        yield Footer()
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id
        
        if item_id == "faz-todas":
            self.notify("Modo: Todas as Fazendas (nao implementado)")
            return
        elif item_id == "faz-multi":
            self.notify("Modo: Multi-Equipes (nao implementado)")
            return
        elif item_id and item_id.startswith("faz-"):
            idx = int(item_id.split("-")[1])
            fazendas = sorted(Estado.df_scope["fazenda"].unique().tolist())
            Estado.fazenda = fazendas[idx]
            Estado.df_faz = Estado.df_scope[Estado.df_scope["fazenda"] == Estado.fazenda].copy()
            
            # Extrai atividades reais
            Estado.atividades_reais = sorted(
                str(x).strip() 
                for x in Estado.df_faz["atividade"].dropna().unique() 
                if str(x).strip()
            )
            
            self.app.push_screen(TelaSelecionarTalhoes())
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-voltar":
            self.app.pop_screen()


# ============= TELA 4: SELECIONAR TALHOES =============
class TelaSelecionarTalhoes(Screen):
    """Seleciona escopo de talhoes."""
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container():
            yield Label("Escopo dos Talhoes", classes="titulo")
            yield Static(f"Fazenda: {Estado.fazenda}")
            yield Label("")
            
            talhoes = sorted(str(x).strip() for x in Estado.df_faz["chave"].dropna().unique())
            num_talhoes = len(talhoes)
            
            if num_talhoes == 1:
                # Apenas um talhao, seleciona automaticamente
                Estado.talhoes_selecionados = talhoes
                Estado.meta_escopo = {
                    "fazenda": Estado.fazenda,
                    "modo_talhao": "unico",
                    "talhoes": talhoes
                }
                self.app.push_screen(TelaConfiguracao())
                return
            
            yield Static(f"Encontrados {num_talhoes} talhoes:")
            yield Label("")
            
            with ListView(id="lista-opcoes"):
                yield ListItem(Label("[TODOS OS TALHOES]"), id="opt-todos")
                yield ListItem(Label("[SELECIONAR TALHOES POR LISTA]"), id="opt-lista")
                yield ListItem(Label("[FILTRAR TALHOES POR TEXTO]"), id="opt-filtro")
            
            with Horizontal():
                yield Button("Voltar", id="btn-voltar")
        yield Footer()
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id
        
        if item_id == "opt-todos":
            talhoes = sorted(str(x).strip() for x in Estado.df_faz["chave"].dropna().unique())
            Estado.talhoes_selecionados = talhoes
            Estado.meta_escopo = {
                "fazenda": Estado.fazenda,
                "modo_talhao": "todos",
                "talhoes": talhoes
            }
            self.app.push_screen(TelaConfiguracao())
        
        elif item_id == "opt-lista":
            self.app.push_screen(TelaListaTalhoes())
        
        elif item_id == "opt-filtro":
            self.app.push_screen(TelaFiltrarTalhoes())
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-voltar":
            self.app.pop_screen()


# ============= TELA 4A: LISTA DE TALHOES =============
class TelaListaTalhoes(Screen):
    """Mostra lista numerada de talhoes para selecao."""
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container():
            yield Label("Selecionar Talhoes por Lista", classes="titulo")
            yield Static(f"Fazenda: {Estado.fazenda}")
            yield Label("")
            
            talhoes = sorted(str(x).strip() for x in Estado.df_faz["chave"].dropna().unique())
            
            yield Static("Talhoes disponiveis:")
            with ListView(id="lista-talhoes"):
                for i, tal in enumerate(talhoes, 1):
                    yield ListItem(Label(f"{i}. {tal}"), id=f"tal-{i}")
            
            yield Label("")
            yield Label("Digite os numeros dos talhoes (ex: 1,3,5-8):")
            yield Input(placeholder="1,3,5-8", id="input-escolha")
            
            with Horizontal():
                yield Button("Voltar", id="btn-voltar")
                yield Button("Confirmar", id="btn-ok", variant="success")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-voltar":
            self.app.pop_screen()
        elif event.button.id == "btn-ok":
            escolha = self.query_one("#input-escolha", Input).value
            if not escolha:
                self.notify("Digite os talhoes", severity="error")
                return
            
            talhoes = sorted(str(x).strip() for x in Estado.df_faz["chave"].dropna().unique())
            
            try:
                indices = parse_intervalos_escolha(escolha, len(talhoes))
                selecionados = [talhoes[i-1] for i in indices if 1 <= i <= len(talhoes)]
                
                if not selecionados:
                    self.notify("Nenhum talhao selecionado", severity="error")
                    return
                
                Estado.talhoes_selecionados = selecionados
                Estado.meta_escopo = {
                    "fazenda": Estado.fazenda,
                    "modo_talhao": "parcial",
                    "talhoes": selecionados
                }
                
                # Filtra df_faz pelos talhoes selecionados
                Estado.df_faz = Estado.df_faz[Estado.df_faz["chave"].isin(selecionados)].copy()
                
                self.app.push_screen(TelaConfiguracao())
            except Exception as e:
                self.notify(f"Erro: {e}", severity="error")


# ============= TELA 4B: FILTRAR TALHOES =============
class TelaFiltrarTalhoes(Screen):
    """Filtra talhoes por texto."""
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container():
            yield Label("Filtrar Talhoes por Texto", classes="titulo")
            yield Static(f"Fazenda: {Estado.fazenda}")
            yield Label("")
            
            yield Label("Texto para filtrar:")
            yield Input(placeholder="ex: T01, Lote, etc", id="input-filtro")
            
            with Horizontal():
                yield Button("Voltar", id="btn-voltar")
                yield Button("Filtrar", id="btn-filtrar", variant="success")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-voltar":
            self.app.pop_screen()
        elif event.button.id == "btn-filtrar":
            filtro = self.query_one("#input-filtro", Input).value.lower()
            if not filtro:
                self.notify("Digite um filtro", severity="error")
                return
            
            talhoes = sorted(str(x).strip() for x in Estado.df_faz["chave"].dropna().unique())
            selecionados = [t for t in talhoes if filtro in normalizar_chave(t)]
            
            if not selecionados:
                self.notify("Nenhum talhao encontrado", severity="error")
                return
            
            Estado.talhoes_selecionados = selecionados
            Estado.meta_escopo = {
                "fazenda": Estado.fazenda,
                "modo_talhao": "filtro",
                "talhoes": selecionados
            }
            
            Estado.df_faz = Estado.df_faz[Estado.df_faz["chave"].isin(selecionados)].copy()
            
            self.notify(f"Selecionados {len(selecionados)} talhoes")
            self.app.push_screen(TelaConfiguracao())


# ============= TELA 5: CONFIGURACAO =============
class TelaConfiguracao(Screen):
    """Configuracoes do calculo."""
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container():
            yield Label("Configuracao do Smart Scheduler", classes="titulo")
            yield Static(f"Fazenda: {Estado.fazenda}")
            yield Static(f"Talhoes: {len(Estado.talhoes_selecionados)}")
            yield Label("")
            
            # Prazo
            yield Label("Prazo META para conclusao (meses):")
            yield Input(value="6.0", id="input-prazo")
            
            # Data inicio
            hoje = datetime.now()
            yield Label("")
            yield Label("Mes inicial (1-12):")
            yield Input(value=str(hoje.month), id="input-mes")
            yield Label("Ano inicial:")
            yield Input(value=str(hoje.year), id="input-ano")
            yield Label("Dia inicial:")
            yield Input(value=str(hoje.day), id="input-dia")
            
            # Equipe
            yield Label("")
            yield Label("Tamanho TOTAL da equipe HOJE:")
            yield Input(value="10", id="input-total")
            yield Label("Quantos LIDERES (nao executam):")
            yield Input(value="1", id="input-lideres")
            yield Label("Jornada efetiva diaria (horas):")
            cfg = get_cfg()
            jornada_padrao = cfg.get("jornada_horas", 4.6)
            yield Input(value=str(jornada_padrao), id="input-jornada")
            
            # Opcoes
            yield Label("")
            yield Checkbox("Aplicar BLOQUEIO GLOBAL (plantio/irrigacao so apos resto zerar)", value=True, id="chk-bloqueio")
            yield Checkbox("Ativar REFORCO AUTOMATICO", value=True, id="chk-reforco")
            
            with Horizontal():
                yield Button("Voltar", id="btn-voltar")
                yield Button("Continuar", id="btn-continuar", variant="success")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-voltar":
            self.app.pop_screen()
        elif event.button.id == "btn-continuar":
            try:
                Estado.config_calc = {
                    "prazo_meses": float(self.query_one("#input-prazo", Input).value or 6.0),
                    "mes_ref": int(self.query_one("#input-mes", Input).value or 1),
                    "ano_ref": int(self.query_one("#input-ano", Input).value or 2026),
                    "dia_ref": int(self.query_one("#input-dia", Input).value or 1),
                    "total_operarios": int(self.query_one("#input-total", Input).value or 10),
                    "lideres": int(self.query_one("#input-lideres", Input).value or 1),
                    "jornada": float(self.query_one("#input-jornada", Input).value or 4.6),
                    "bloqueio_global": self.query_one("#chk-bloqueio", Checkbox).value,
                    "reforco_automatico": self.query_one("#chk-reforco", Checkbox).value,
                }
                self.app.push_screen(TelaCriarTurmas())
            except ValueError as e:
                self.notify(f"Valor invalido: {e}", severity="error")


# ============= TELA 6: CRIAR TURMAS =============
class TelaCriarTurmas(Screen):
    """Cria turmas/equipes."""
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container():
            yield Label("Criar Turmas", classes="titulo")
            
            total = Estado.config_calc.get("total_operarios", 10)
            lideres = Estado.config_calc.get("lideres", 1)
            executores = total - lideres
            
            yield Static(f"Operarios disponiveis: {executores}")
            yield Label("")
            
            yield Label("Turmas existentes:")
            with ListView(id="lista-turmas"):
                if not Estado.turmas:
                    yield ListItem(Label("Nenhuma turma criada"))
                else:
                    for i, turma in enumerate(Estado.turmas):
                        yield ListItem(Label(f"{turma['nome']}: {turma['operarios']} operarios"))
            
            yield Label("")
            yield Label("Nova turma:")
            yield Label("Nome:")
            yield Input(value=f"Turma {len(Estado.turmas) + 1}", id="input-nome")
            yield Label("Quantos operarios:")
            yield Input(value=str(executores // 2 or 1), id="input-qtd")
            
            with Horizontal():
                yield Button("Voltar", id="btn-voltar")
                yield Button("Adicionar Turma", id="btn-add")
                yield Button("Continuar", id="btn-continuar", variant="success")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-voltar":
            self.app.pop_screen()
        elif event.button.id == "btn-add":
            nome = self.query_one("#input-nome", Input).value
            qtd = int(self.query_one("#input-qtd", Input).value or 1)
            Estado.turmas.append({"nome": nome, "operarios": qtd, "atividades": []})
            self.notify(f"Turma {nome} adicionada")
            self.refresh()
        elif event.button.id == "btn-continuar":
            if not Estado.turmas:
                self.notify("Crie pelo menos uma turma", severity="error")
                return
            self.app.push_screen(TelaVincularAtividades())


# ============= TELA 7: VINCULAR ATIVIDADES =============
class TelaVincularAtividades(Screen):
    """Vincula atividades as turmas."""
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container():
            yield Label("Vincular Atividades as Turmas", classes="titulo")
            yield Static(f"Atividades reais na fazenda: {len(Estado.atividades_reais)}")
            yield Label("")
            
            # Lista atividades
            yield Label("Atividades encontradas:")
            with ListView(id="lista-atividades"):
                for atv in Estado.atividades_reais:
                    yield ListItem(Label(atv))
            
            yield Label("")
            yield Static("Selecione a turma para cada atividade:")
            
            # Para cada atividade, select de turma
            for i, atv in enumerate(Estado.atividades_reais[:10]):  # Limita a 10
                with Horizontal():
                    yield Label(f"{atv[:30]}:", classes="atv-label")
                    options = [(t["nome"], t["nome"]) for t in Estado.turmas]
                    yield Select(options, prompt="Turma...", id=f"sel-atv-{i}")
            
            with Horizontal():
                yield Button("Voltar", id="btn-voltar")
                yield Button("Executar", id="btn-executar", variant="success")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-voltar":
            self.app.pop_screen()
        elif event.button.id == "btn-executar":
            self._executar()
    
    def _executar(self):
        """Executa o calculo."""
        if not ATM_AVAILABLE:
            self.notify("ATM nao disponivel", severity="error")
            return
        
        try:
            cfg = get_cfg()
            
            # Prepara escopo
            escopo_meta = Estado.meta_escopo or {}
            
            # Chama o scheduler
            resultado = calcular_cronograma_inteligente(
                cfg,
                Estado.df_faz,
                Estado.fazenda,
                escopo_meta=escopo_meta,
                atividades_catalogo=Estado.atividades_reais,
            )
            
            self.notify("Calculo concluido!")
            self.app.push_screen(TelaResultado(resultado))
        except Exception as e:
            self.notify(f"Erro: {e}", severity="error")


# ============= TELA 8: RESULTADO =============
class TelaResultado(Screen):
    """Mostra resultado do calculo."""
    
    def __init__(self, resultado, **kwargs):
        super().__init__(**kwargs)
        self.resultado = resultado
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container():
            yield Label("Resultado do Smart Scheduler", classes="titulo")
            yield Static(f"Fazenda: {Estado.fazenda}")
            yield Static(f"Talhoes: {len(Estado.talhoes_selecionados)}")
            yield Label("")
            
            # Aqui mostraria o resultado real
            yield Static("Calculo concluido com sucesso.")
            yield Static("Exporte o resultado para Excel usando a opcao no menu.")
            
            with Horizontal():
                yield Button("Voltar ao Inicio", id="btn-inicio", variant="success")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        # Limpa estado e volta ao inicio
        Estado.fazenda = None
        Estado.talhoes_selecionados = []
        Estado.turmas = []
        Estado.meta_escopo = None
        Estado.config_calc = {}
        
        self.app.pop_screen_until(TelaInicial)


# ============= APP PRINCIPAL =============
class SRFTextual(App):
    """App principal."""
    
    CSS = """
Screen {
    align: center middle;
    background: black;
    color: white;
}
Header {
    background: #222;
    color: white;
}
Footer {
    background: #222;
    color: #888;
}
.titulo {
    text-align: center;
    text-style: bold;
    color: white;
}
.erro {
    color: red;
}
Button {
    margin: 0 1;
}
Input {
    margin: 1 0;
}
ListView {
    height: auto;
    max-height: 15;
    border: solid #444;
}
DataTable {
    height: 10;
    border: solid #444;
}
.atv-label {
    width: 30;
}
"""
    
    BINDINGS = [
        Binding("q", "quit", "Sair", show=True),
    ]
    
    def on_mount(self) -> None:
        self.title = "SRF v6.1"
        self.push_screen(TelaInicial())
    
    def action_quit(self) -> None:
        self.exit()


if __name__ == "__main__":
    app = SRFTextual()
    app.run()
