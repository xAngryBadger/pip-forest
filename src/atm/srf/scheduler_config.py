from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TurmaSpec:
    nome: str = "Geral"
    operarios: int = 9
    atividades: list[str] = field(default_factory=lambda: ["todas"])

    def to_dict(self) -> dict:
        return {
            "nome": self.nome,
            "operarios": self.operarios,
            "atividades": self.atividades,
        }


@dataclass
class EquipeSpec:
    nome: str = ""
    prazo_meses: float = 6.0
    jornada: float = 4.6
    executores: int = 9
    turmas: list[TurmaSpec] = field(default_factory=list)
    fazendas: list[str] = field(default_factory=list)
    data_inicio_txt: Optional[str] = None
    data_fim_txt: Optional[str] = None


@dataclass
class SchedulerConfig:
    prazo_meses: float = 6.0
    mes_ref: int = 1
    ano_ref: int = 2026
    dia_ref: int = 1
    data_inicio_txt: Optional[str] = None
    data_fim_txt: Optional[str] = None
    jornada: float = 4.6
    executores: int = 9
    turmas: list[TurmaSpec] = field(default_factory=lambda: [TurmaSpec()])
    modo_seq: str = "implantacao"
    usar_bloqueio_global: bool = True
    usar_reforco_automatico: bool = True
    usar_pool_pos_bloqueio: bool = True
    filtros_bloqueio_global: list[str] = field(default_factory=lambda: ["plantio", "irrig"])
    orcamento_estrito: bool = True
    preencher_orfas: bool = False
    preencher_orfas_equipe: Optional[str] = None
    skip_scope_adjustment: bool = False
    skip_checkpoint: bool = False
    modo_comparativo: bool = False
    substituicoes_comparativo: Optional[dict[str, str]] = None
    ativar_mecanizado: bool = False
    regra_implantacao_mec: str = "substituir"
    equipes: Optional[list[EquipeSpec]] = None
    modo_distribuicao: str = "manual"
    session_hh: dict[str, float] = field(default_factory=dict)
    penalidade: float = 1.0
    show_detailed_hh_hm: bool = False
    reatribuicao_template: dict[str, str] = field(default_factory=dict)
    paralelo_template: dict[str, str] = field(default_factory=dict)
    primaria_template: dict[str, str] = field(default_factory=dict)
    substituicoes_template: dict[str, str] = field(default_factory=dict)

    def to_ctx_dict(self) -> dict:
        result = {
            "prazo_meses": self.prazo_meses,
            "mes_ref": self.mes_ref,
            "ano_ref": self.ano_ref,
            "dia_ref": self.dia_ref,
            "data_inicio_txt": self.data_inicio_txt,
            "data_fim_txt": self.data_fim_txt,
            "jornada": self.jornada,
            "executores": self.executores,
            "turmas": [t.to_dict() for t in self.turmas],
            "modo_seq": self.modo_seq,
            "usar_bloqueio_global": self.usar_bloqueio_global,
            "usar_reforco_automatico": self.usar_reforco_automatico,
            "usar_pool_pos_bloqueio": self.usar_pool_pos_bloqueio,
            "orcamento_estrito": self.orcamento_estrito,
            "preencher_orfas_template": self.preencher_orfas,
            "penalidade": self.penalidade,
            "session_hh": self.session_hh,
            "reatribuicao_template": self.reatribuicao_template,
            "paralelo_template": self.paralelo_template,
            "primaria_template": self.primaria_template,
            "substituicoes_template": self.substituicoes_template,
            "comparativo_cfg": (
                {"modo": self.modo_comparativo, "substituicoes": self.substituicoes_comparativo}
                if self.modo_comparativo
                else None
            ),
        }
        if self.preencher_orfas_equipe:
            result["preencher_orfas_equipe"] = self.preencher_orfas_equipe
        return result


@dataclass
class ScheduleResult:
    success: bool = True
    fazenda: str = ""
    dias_simulado: int = 0
    meses_simulado: float = 0.0
    dias_mecanizado: Optional[int] = None
    ganho_mecanizado_dias: int = 0
    total_hh: float = 0.0
    total_custo: float = 0.0
    total_hm: float = 0.0
    cronograma: list[dict] = field(default_factory=list)
    turmas_snapshot: list[dict] = field(default_factory=list)
    result_files: list[str] = field(default_factory=list)
    error: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    modo_usado: str = ""
    comparativo_mecanizado: Optional[dict] = None

    def to_json(self) -> dict:
        return {
            "success": self.success,
            "fazenda": self.fazenda,
            "dias_simulado": self.dias_simulado,
            "meses_simulado": self.meses_simulado,
            "dias_mecanizado": self.dias_mecanizado,
            "ganho_mecanizado_dias": self.ganho_mecanizado_dias,
            "total_hh": self.total_hh,
            "total_custo": self.total_custo,
            "total_hm": self.total_hm,
            "cronograma": self.cronograma[:50] if self.cronograma else [],
            "cronograma_total_rows": len(self.cronograma),
            "turmas_snapshot": self.turmas_snapshot,
            "result_files": self.result_files,
            "error": self.error,
            "warnings": self.warnings,
            "modo_usado": self.modo_usado,
            "comparativo_mecanizado": self.comparativo_mecanizado,
        }
