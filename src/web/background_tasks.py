"""Background task runner for wizard jobs."""

import threading
import uuid
import traceback
import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List
from datetime import datetime
from enum import Enum
import queue


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class JobLog:
    timestamp: str
    level: str
    message: str
    step: str = ""
    progress: float = 0.0


@dataclass
class WizardJob:
    job_id: str
    session_id: str
    wizard_state: Any
    status: JobStatus = JobStatus.PENDING
    current_step: str = "initializing"
    progress: float = 0.0
    logs: List[JobLog] = field(default_factory=list)
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    cancel_requested: bool = False
    _ws_connections: List[Any] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def add_log(self, level: str, message: str, step: str = "", progress: float = None):
        log = JobLog(
            timestamp=datetime.now().isoformat(),
            level=level,
            message=message,
            step=step,
            progress=progress if progress is not None else self.progress
        )
        with self._lock:
            self.logs.append(log)
            self._broadcast_log(log)

    def set_progress(self, step: str, progress: float, message: str = ""):
        with self._lock:
            self.current_step = step
            self.progress = progress
            if message:
                self.add_log("info", message, step, progress)

def set_status(self, status: JobStatus):
    with self._lock:
        self.status = status
        if status == JobStatus.RUNNING and not self.started_at:
            self.started_at = datetime.now().isoformat()
        elif status in (JobStatus.COMPLETE, JobStatus.FAILED):
            self.finished_at = datetime.now().isoformat()
    self.broadcast_status()

    def _broadcast_log(self, log: JobLog):
        dead_connections = []
        for ws in self._ws_connections:
            try:
                ws.send_json({
                    "type": "log",
                    "data": {
                        "timestamp": log.timestamp,
                        "level": log.level,
                        "message": log.message,
                        "step": log.step,
                        "progress": log.progress,
                    }
                })
            except Exception:
                dead_connections.append(ws)
        for ws in dead_connections:
            if ws in self._ws_connections:
                self._ws_connections.remove(ws)

    def broadcast_status(self):
        with self._lock:
            status_data = {
                "type": "status",
                "data": {
                    "job_id": self.job_id,
                    "status": self.status.value,
                    "current_step": self.current_step,
                    "progress": self.progress,
                }
            }
        for ws in self._ws_connections:
            try:
                ws.send_json(status_data)
            except Exception:
                pass

    def add_ws(self, ws):
        with self._lock:
            self._ws_connections.append(ws)

    def remove_ws(self, ws):
        with self._lock:
            if ws in self._ws_connections:
                self._ws_connections.remove(ws)

    def to_status_dict(self) -> dict:
        with self._lock:
            return {
                "job_id": self.job_id,
                "status": self.status.value,
                "current_step": self.current_step,
                "progress": self.progress,
                "logs": [
                    {
                        "timestamp": l.timestamp,
                        "level": l.level,
                        "message": l.message,
                        "step": l.step,
                        "progress": l.progress,
                    }
                    for l in self.logs[-100:]
                ],
                "error": self.error,
                "created_at": self.created_at,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
            }

    def to_result_dict(self) -> dict:
        with self._lock:
            result = self.result
            if result is None:
                return {"success": False, "error": "No result available"}
            if hasattr(result, "to_json"):
                return result.to_json()
            if hasattr(result, "__dict__"):
                return result.__dict__
            return result


class JobStore:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._store = {}
        return cls._instance

    def create(self, session_id: str, wizard_state: Any) -> WizardJob:
        job_id = str(uuid.uuid4())[:16]
        job = WizardJob(job_id=job_id, session_id=session_id, wizard_state=wizard_state)
        with self._lock:
            self._store[job_id] = job
        return job

    def get(self, job_id: str) -> Optional[WizardJob]:
        with self._lock:
            return self._store.get(job_id)

    def delete(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._store:
                del self._store[job_id]
                return True
            return False

    def list(self) -> List[WizardJob]:
        with self._lock:
            return list(self._store.values())


job_store = JobStore()


def run_wizard_job(job: WizardJob):
    """Run the wizard scheduling job in background thread."""
    job.set_status(JobStatus.RUNNING)
    job.set_progress("loading_data", 5, "Carregando dados da fazenda...")

    try:
        from src.atm.srf.config import carregar_config
        from src.atm.srf.io import carregar_planilha_microplanejamento, _find_default_micro_path
        from src.atm.srf.context import contexto_sessao
        from src.atm.srf.scheduler_core import calcular_cronograma_inteligente
        from src.atm.srf.app import _aplicar_filtro_regiao, _aplicar_filtro_empresa_e_escopo
        import pandas as pd
        import os

        cfg = carregar_config()
        micro_path = _find_default_micro_path(cfg)

        if not micro_path or not os.path.exists(micro_path):
            job.add_log("error", "Arquivo de microplanejamento nao encontrado")
            job.set_status(JobStatus.FAILED)
            job.error = "Arquivo de microplanejamento nao encontrado"
            return

        job.set_progress("filtering", 10, "Aplicando filtros de regiao e empresa...")
        df = carregar_planilha_microplanejamento(cfg, caminho=micro_path, modo_auto=True)
        if df is None or df.empty:
            job.add_log("error", "Nenhum dado carregado do microplanejamento")
            job.set_status(JobStatus.FAILED)
            job.error = "Nenhum dado carregado"
            return

        df_scope, regiao_info = _aplicar_filtro_regiao(df)
        if df_scope is None or df_scope.empty:
            job.add_log("error", "Nenhum dado apos filtro de regiao")
            job.set_status(JobStatus.FAILED)
            job.error = "Nenhum dado apos filtro de regiao"
            return

        df_scope, empresa_filtro = _aplicar_filtro_empresa_e_escopo(df_scope)
        if df_scope is None or df_scope.empty:
            job.add_log("error", "Nenhum dado apos filtros")
            job.set_status(JobStatus.FAILED)
            job.error = "Nenhum dado apos filtros"
            return

        farm_name = job.wizard_state.step1.farm_name
        faz_norm = farm_name.strip().upper()
        faz_col = df_scope["fazenda"].astype(str).str.strip().str.upper()
        match = df_scope[faz_col == faz_norm]
        if match.empty:
            job.add_log("error", f"Fazenda '{farm_name}' nao encontrada")
            job.set_status(JobStatus.FAILED)
            job.error = f"Fazenda '{farm_name}' nao encontrada"
            return

        fazenda_real = match.iloc[0]["fazenda"]
        df_faz = match.copy()

        job.set_progress("configuring", 20, "Configurando scheduler...")

        ctx = job.wizard_state.to_scheduler_config()
        ctx["penalidade"] = job.wizard_state.step1.penalidade if hasattr(job.wizard_state.step1, 'penalidade') else 1.0

        if job.wizard_state.step1.metodologias_selected:
            metodologias = set(job.wizard_state.step1.metodologias_selected)
            df_faz = df_faz[df_faz["metodologia"].isin(metodologias)]

        if job.wizard_state.step1.talhoes_selected:
            talhoes = set(job.wizard_state.step1.talhoes_selected)
            df_faz = df_faz[df_faz["chave"].isin(talhoes)]

        job.add_log("info", f"Fazenda: {fazenda_real}, Talhoes: {df_faz['chave'].nunique()}, Area: {df_faz['area_ha'].sum():.1f} ha")

        job.set_progress("scheduling", 30, "Executando scheduler inteligente...")

        def progress_callback(step: str, progress: float, message: str = ""):
            job.set_progress(step, 30 + progress * 0.6, message)

        result = calcular_cronograma_inteligente(
            cfg=cfg,
            df_faz=df_faz,
            fazenda=fazenda_real,
            esperar_enter=False,
            ctx=ctx,
            escopo_meta={
                "metodologias": job.wizard_state.step1.metodologias_selected,
                "talhoes": job.wizard_state.step1.talhoes_selected,
            },
        )

        job.set_progress("finalizing", 95, "Finalizando e exportando resultados...")

        if result is None:
            job.add_log("error", "Scheduler retornou resultado nulo")
            job.set_status(JobStatus.FAILED)
            job.error = "Scheduler falhou - resultado nulo"
            return

        if isinstance(result, dict) and result.get("acao") == "orcamento_invalido":
            job.add_log("error", "Validacao de orcamento falhou")
            job.set_status(JobStatus.FAILED)
            job.error = "Validacao de orcamento falhou"
            return

        from src.atm.orca.scheduler_config import ScheduleResult
        schedule_result = ScheduleResult(
            success=True,
            fazenda=fazenda_real,
            dias_simulado=result.get("dias_simulado", 0),
            meses_simulado=result.get("meses_simulado", 0.0),
            total_hh=result.get("total_hh", 0.0),
            total_custo=result.get("total_custo", 0.0),
            total_hm=result.get("total_hm", 0.0),
            cronograma=result.get("cronograma", []),
            turmas_snapshot=result.get("turmas_snapshot", []),
            result_files=result.get("result_files", []),
            modo_usado=result.get("modo_usado", "wizard"),
            comparativo_mecanizado=result.get("comparativo_mecanizado"),
        )

        job.result = schedule_result
        job.add_log("success", f"Scheduler concluido com sucesso - {schedule_result.dias_simulado} dias, {schedule_result.total_hh:.1f} HH")
        job.set_progress("complete", 100, "Concluido")
        job.set_status(JobStatus.COMPLETE)

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        job.add_log("error", f"Erro durante execucao: {error_msg}")
        traceback.print_exc()
        job.set_status(JobStatus.FAILED)
        job.error = error_msg


def start_wizard_job(session_id: str, wizard_state: Any) -> WizardJob:
    """Start a wizard job in background thread."""
    job = job_store.create(session_id, wizard_state)
    thread = threading.Thread(target=run_wizard_job, args=(job,), daemon=True)
    thread.start()
    return job