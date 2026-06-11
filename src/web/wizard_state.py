"""Wizard state management for multi-step scheduling wizard."""

from dataclasses import dataclass, field
from typing import Any, Optional
import uuid
import threading


@dataclass
class Step1FarmScope:
    farm_name: str = ""
    farm_id: str = ""
    region_filter: str = ""
    state_filter: str = ""
    municipality_filter: str = ""
    company_filter: str = ""
    methodology_scope: str = "all"
    metodologias_selected: list[str] = field(default_factory=list)
    talhao_scope: str = "all"
    talhoes_selected: list[str] = field(default_factory=list)
    penalidade: float = 1.0

    def validate(self) -> list[str]:
        errors = []
        if not self.farm_name.strip():
            errors.append("Selecione uma fazenda")
        return errors


@dataclass
class Step2TeamsTimeline:
    penalidade: float = 1.0
    modo_seq: str = "implantacao"
    usar_bloqueio_global: bool = True
    usar_reforco_automatico: bool = True
    usar_pool_pos_bloqueio: bool = True
    prazo_meses: float = 6.0
    mes_ref: int = 1
    ano_ref: int = 2026
    dia_ref: int = 1
    data_inicio_txt: str = ""
    data_fim_txt: str = ""
    jornada: float = 4.6
    executores: int = 9
    turmas: list[dict] = field(default_factory=list)

    def validate(self) -> list[str]:
        errors = []
        if self.prazo_meses <= 0:
            errors.append("Prazo deve ser maior que zero")
        if not (1 <= self.mes_ref <= 12):
            errors.append("Mes de referencia invalido (1-12)")
        if self.ano_ref < 2020:
            errors.append("Ano de referencia invalido")
        if not (1 <= self.dia_ref <= 31):
            errors.append("Dia de referencia invalido (1-31)")
        if self.jornada <= 0:
            errors.append("Jornada deve ser maior que zero")
        if self.executores <= 0:
            errors.append("Deve ter pelo menos 1 executor")
        total_workers = sum(t.get("operarios", 0) for t in self.turmas)
        if total_workers != self.executores:
            errors.append(f"Soma de operarios nas turmas ({total_workers}) deve ser igual a executores ({self.executores})")
        if not self.turmas:
            errors.append("Pelo menos uma turma e obrigatoria")
        for i, t in enumerate(self.turmas):
            if not t.get("nome", "").strip():
                errors.append(f"Turma {i+1}: nome e obrigatorio")
            if t.get("operarios", 0) <= 0:
                errors.append(f"Turma {t.get('nome', i+1)}: operarios deve ser > 0")
        return errors


@dataclass
class Step3Activities:
    atividade_vinculos: dict[str, list[str]] = field(default_factory=dict)
    reatribuicao_mode: str = "paralelo"
    reatribuicao_template: dict[str, str] = field(default_factory=dict)
    paralelo_template: dict[str, str] = field(default_factory=dict)
    primaria_template: dict[str, str] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors = []
        if not self.atividade_vinculos:
            errors.append("Vincule pelo menos uma atividade a uma turma")
        return errors


@dataclass
class Step4BudgetComparativo:
    orcamento_estrito: bool = True
    tariff_gaps: list[dict] = field(default_factory=list)
    tariff_gap_resolutions: dict[str, dict] = field(default_factory=dict)
    modo_comparativo: str = "off"
    substituicoes_comparativo: dict[str, str] = field(default_factory=dict)
    comparativo_multifator: bool = False
    external_mecanizado: dict = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors = []
        for gap in self.tariff_gaps:
            gap_key = gap.get("key", "")
            resolution = self.tariff_gap_resolutions.get(gap_key, {})
            if not resolution.get("resolved", False):
                errors.append(f"Lacuna de tarifa nao resolvida: {gap_key}")
        return errors


@dataclass
class Step5Review:
    confirmed: bool = False

    def validate(self) -> list[str]:
        errors = []
        if not self.confirmed:
            errors.append("Confirme a revisao antes de executar")
        return errors


class WizardState:
    def __init__(self, session_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())[:16]
        self.step1 = Step1FarmScope()
        self.step2 = Step2TeamsTimeline()
        self.step3 = Step3Activities()
        self.step4 = Step4BudgetComparativo()
        self.step5 = Step5Review()
        self.current_step = 1
        self.created_at = None
        self.updated_at = None

    def get_step(self, step_num: int) -> Any:
        steps = {
            1: self.step1,
            2: self.step2,
            3: self.step3,
            4: self.step4,
            5: self.step5,
        }
        return steps.get(step_num)

    def update_step(self, step_num: int, data: dict) -> bool:
        step = self.get_step(step_num)
        if not step:
            return False
        for key, value in data.items():
            if hasattr(step, key):
                setattr(step, key, value)
        return True

    def validate_step(self, step_num: int) -> list[str]:
        step = self.get_step(step_num)
        if not step:
            return [f"Passo {step_num} nao existe"]
        return step.validate()

    def validate_all(self) -> dict[int, list[str]]:
        return {i: self.validate_step(i) for i in range(1, 6)}

    def is_valid(self) -> bool:
        return all(not errs for errs in self.validate_all().values())

    def to_scheduler_config(self) -> dict:
        from src.atm.orca.scheduler_config import SchedulerConfig, TurmaSpec

        config = SchedulerConfig()
        config.prazo_meses = self.step2.prazo_meses
        config.mes_ref = self.step2.mes_ref
        config.ano_ref = self.step2.ano_ref
        config.dia_ref = self.step2.dia_ref
        config.data_inicio_txt = self.step2.data_inicio_txt or None
        config.data_fim_txt = self.step2.data_fim_txt or None
        config.jornada = self.step2.jornada
        config.executores = self.step2.executores
        config.turmas = [TurmaSpec(**t) for t in self.step2.turmas]
        config.modo_seq = self.step2.modo_seq
        config.usar_bloqueio_global = self.step2.usar_bloqueio_global
        config.usar_reforco_automatico = self.step2.usar_reforco_automatico
        config.usar_pool_pos_bloqueio = self.step2.usar_pool_pos_bloqueio
        config.orcamento_estrito = self.step4.orcamento_estrito
        config.penalidade = self.step1.penalidade if hasattr(self.step1, 'penalidade') else 1.0
        config.session_hh = {}
        config.reatribuicao_template = self.step3.reatribuicao_template
        config.paralelo_template = self.step3.paralelo_template
        config.primaria_template = self.step3.primaria_template
        config.substituicoes_template = self.step4.substituicoes_comparativo
        config.modo_comparativo = self.step4.modo_comparativo != "off"
        config.substituicoes_comparativo = self.step4.substituicoes_comparativo if config.modo_comparativo else None
        config.ativar_mecanizado = self.step4.modo_comparativo in ("simple", "multi-factor")
        return config.to_ctx_dict()

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "step1": self.step1.__dict__,
            "step2": self.step2.__dict__,
            "step3": self.step3.__dict__,
            "step4": self.step4.__dict__,
            "step5": self.step5.__dict__,
            "current_step": self.current_step,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WizardState":
        ws = cls(data.get("session_id"))
        ws.current_step = data.get("current_step", 1)
        for i in range(1, 6):
            step_data = data.get(f"step{i}", {})
            step = ws.get_step(i)
            if step:
                for key, value in step_data.items():
                    if hasattr(step, key):
                        setattr(step, key, value)
        return ws


class WizardStore:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._store = {}
        return cls._instance

    def get(self, session_id: str) -> Optional[WizardState]:
        with self._lock:
            return self._store.get(session_id)

    def set(self, state: WizardState) -> WizardState:
        with self._lock:
            self._store[state.session_id] = state
        return state

    def delete(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._store:
                del self._store[session_id]
                return True
            return False

    def list(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())


wizard_store = WizardStore()