"""Wizard API endpoints for multi-step scheduling wizard."""

import pandas as pd
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import json
import asyncio
import threading
from datetime import datetime

from src.web.wizard_state import wizard_store, WizardState
from src.web.background_tasks import job_store, start_wizard_job, WizardJob, JobStatus
from src.web.auth import is_authenticated

router = APIRouter(prefix="/api/schedule/wizard", tags=["wizard"])

templates = Jinja2Templates(directory="src/web/templates")


class WizardStep1Payload(BaseModel):
    farm_name: str = ""
    farm_id: str = ""
    region_filter: str = ""
    state_filter: str = ""
    municipality_filter: str = ""
    company_filter: str = ""
    methodology_scope: str = "all"
    metodologias_selected: List[str] = Field(default_factory=list)
    talhao_scope: str = "all"
    talhoes_selected: List[str] = Field(default_factory=list)
    penalidade: float = 1.0


class WizardStep2Payload(BaseModel):
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
    turmas: List[Dict[str, Any]] = Field(default_factory=list)


class WizardStep3Payload(BaseModel):
    atividade_vinculos: Dict[str, List[str]] = Field(default_factory=dict)
    reatribuicao_mode: str = "paralelo"
    reatribuicao_template: Dict[str, str] = Field(default_factory=dict)
    paralelo_template: Dict[str, str] = Field(default_factory=dict)
    primaria_template: Dict[str, str] = Field(default_factory=dict)


class WizardStep4Payload(BaseModel):
    orcamento_estrito: bool = True
    tariff_gaps: List[Dict[str, Any]] = Field(default_factory=list)
    tariff_gap_resolutions: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    modo_comparativo: str = "off"
    substituicoes_comparativo: Dict[str, str] = Field(default_factory=dict)
    comparativo_multifator: bool = False
    external_mecanizado: Dict[str, Any] = Field(default_factory=dict)


class WizardStep5Payload(BaseModel):
    confirmed: bool = False


class WizardStartPayload(BaseModel):
    step1: WizardStep1Payload
    step2: WizardStep2Payload
    step3: WizardStep3Payload
    step4: WizardStep4Payload
    step5: WizardStep5Payload


def get_session_id(request: Request) -> str:
    session_id = request.session.get("wizard_session_id")
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())[:16]
        request.session["wizard_session_id"] = session_id
    return session_id


def get_wizard_state(session_id: str) -> WizardState:
    state = wizard_store.get(session_id)
    if not state:
        state = WizardState(session_id)
        wizard_store.set(state)
    return state


@router.get("/session")
async def get_or_create_session(request: Request):
    session_id = get_session_id(request)
    state = get_wizard_state(session_id)
    return {"session_id": session_id, "current_step": state.current_step, "data": state.to_dict()}


@router.post("/session/{session_id}/step/{step_num}")
async def update_step(session_id: str, step_num: int, request: Request):
    state = wizard_store.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        data = await request.json()
    except Exception:
        form_data = await request.form()
        data = dict(form_data)
    state.update_step(step_num, data)
    state.current_step = max(state.current_step, step_num)
    wizard_store.set(state)
    
    errors = state.validate_step(step_num)
    return {"success": len(errors) == 0, "errors": errors, "current_step": state.current_step}


@router.get("/session/{session_id}/validate")
async def validate_all(session_id: str):
    state = wizard_store.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    
    validation = state.validate_all()
    all_valid = all(not errs for errs in validation.values())
    return {"valid": all_valid, "validation": validation}


@router.post("/start")
async def start_wizard(request: Request):
    session_id = get_session_id(request)
    state = get_wizard_state(session_id)

    try:
        data = await request.json()
    except Exception:
        form_data = await request.form()
        data = dict(form_data)

    for step_key in ["step1", "step2", "step3", "step4", "step5"]:
        if step_key in data:
            val = data[step_key]
            if isinstance(val, str):
                try:
                    val = json.loads(val)
                except Exception:
                    pass
            if isinstance(val, dict):
                setattr(state, step_key, val)
    state.current_step = 5
    wizard_store.set(state)

    job = start_wizard_job(session_id, state)

    return {"job_id": job.job_id, "session_id": session_id, "status": "started"}


@router.get("/{job_id}/status")
async def get_job_status(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_status_dict()


@router.get("/{job_id}/result")
async def get_job_result(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.COMPLETE:
        raise HTTPException(status_code=400, detail="Job not complete")
    return job.to_result_dict()


@router.websocket("/ws/{job_id}")
async def wizard_websocket(websocket: WebSocket, job_id: str):
    await websocket.accept()
    job = job_store.get(job_id)
    if not job:
        await websocket.send_json({"type": "error", "data": {"message": "Job not found"}})
        await websocket.close()
        return
    
    job.add_ws(websocket)
    try:
        await websocket.send_json(job.to_status_dict())
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        job.remove_ws(websocket)
    except Exception:
        job.remove_ws(websocket)


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.cancel_requested = True
    job.set_status(JobStatus.FAILED)
    job.error = "Cancelled by user"
    job.add_log("warning", "Execução cancelada pelo usuário")
    return {"success": True, "status": "cancelled"}

@router.post("/session/{session_id}/reset")
async def reset_session(session_id: str):
    wizard_store.delete(session_id)
    return {"success": True}


@router.get("/estados")
async def get_estados():
    try:
        from src.atm.orca.config import carregar_config
        from src.atm.orca.io import carregar_planilha_microplanejamento, _find_default_micro_path
        cfg = carregar_config()
        micro_path = _find_default_micro_path(cfg)
        if not micro_path:
            return {"estados": []}
        df = carregar_planilha_microplanejamento(cfg, caminho=micro_path, modo_auto=True)
        if df is None or df.empty:
            return {"estados": []}
        estados = sorted(df["estado"].dropna().unique().tolist())
        return {"estados": [str(e) for e in estados if str(e).strip()]}
    except Exception:
        return {"estados": []}

@router.get("/municipios")
async def get_municipios(estado: str = ""):
    try:
        from src.atm.orca.config import carregar_config
        from src.atm.orca.io import carregar_planilha_microplanejamento, _find_default_micro_path
        cfg = carregar_config()
        micro_path = _find_default_micro_path(cfg)
        if not micro_path:
            return {"municipios": []}
        df = carregar_planilha_microplanejamento(cfg, caminho=micro_path, modo_auto=True)
        if df is None or df.empty:
            return {"municipios": []}
        if estado:
            match = df[df["estado"].astype(str).str.strip().str.upper() == estado.strip().upper()]
            municipios = sorted(match["municipio"].dropna().unique().tolist())
            return {"municipios": [str(m) for m in municipios if str(m).strip()]}
        return {"municipios": []}
    except Exception:
        return {"municipios": []}

@router.get("/empresas")
async def get_empresas():
    try:
        from src.atm.orca.config import carregar_config
        from src.atm.orca.io import carregar_planilha_microplanejamento, _find_default_micro_path
        cfg = carregar_config()
        micro_path = _find_default_micro_path(cfg)
        if not micro_path:
            return {"empresas": []}
        df = carregar_planilha_microplanejamento(cfg, caminho=micro_path, modo_auto=True)
        if df is None or df.empty:
            return {"empresas": []}
        empresas = sorted(df["empresa"].dropna().unique().tolist()) if "empresa" in df.columns else []
        return {"empresas": [str(e) for e in empresas if str(e).strip()]}
    except Exception:
        return {"empresas": []}

@router.get("/tarifas/gaps")
async def get_tarifas_gaps(farm: str = ""):
    return {"gaps": []}

@router.get("/farms")
async def list_farms():
    try:
        from src.atm.orca.config import carregar_config
        from src.atm.orca.io import carregar_planilha_microplanejamento, _find_default_micro_path
        
        cfg = carregar_config()
        micro_path = _find_default_micro_path(cfg)
        if not micro_path:
            return {"farms": []}
        
        df = carregar_planilha_microplanejamento(cfg, caminho=micro_path, modo_auto=True)
        if df is None or df.empty:
            return {"farms": []}
        
        farms = df["fazenda"].dropna().unique().tolist()
        farms = [str(f) for f in farms if str(f).strip()]
        return {"farms": sorted(farms)}
    except Exception as e:
        return {"farms": [], "error": str(e)}


@router.get("/methodologies/{farm_name}")
async def get_farm_methodologies(farm_name: str):
    try:
        from src.atm.orca.config import carregar_config
        from src.atm.orca.io import carregar_planilha_microplanejamento, _find_default_micro_path
        
        cfg = carregar_config()
        micro_path = _find_default_micro_path(cfg)
        if not micro_path:
            return {"methodologies": []}
        
        df = carregar_planilha_microplanejamento(cfg, caminho=micro_path, modo_auto=True)
        if df is None or df.empty:
            return {"methodologies": []}
        
        faz_norm = farm_name.strip().upper()
        faz_col = df["fazenda"].astype(str).str.strip().str.upper()
        match = df[faz_col == faz_norm]
        if match.empty:
            return {"methodologies": []}
        
        metodologias = match["metodologia"].dropna().unique().tolist()
        return {"methodologies": sorted([str(m) for m in metodologias if str(m).strip()])}
    except Exception as e:
        return {"methodologies": [], "error": str(e)}


@router.get("/talhoes/{farm_name}")
async def get_farm_talhoes(farm_name: str):
    try:
        from src.atm.orca.config import carregar_config
        from src.atm.orca.io import carregar_planilha_microplanejamento, _find_default_micro_path
        
        cfg = carregar_config()
        micro_path = _find_default_micro_path(cfg)
        if not micro_path:
            return {"talhoes": []}
        
        df = carregar_planilha_microplanejamento(cfg, caminho=micro_path, modo_auto=True)
        if df is None or df.empty:
            return {"talhoes": []}
        
        faz_norm = farm_name.strip().upper()
        faz_col = df["fazenda"].astype(str).str.strip().str.upper()
        match = df[faz_col == faz_norm]
        if match.empty:
            return {"talhoes": []}
        
        talhoes = match["chave"].dropna().unique().tolist()
        return {"talhoes": sorted([str(t) for t in talhoes if str(t).strip()])}
    except Exception as e:
        return {"talhoes": [], "error": str(e)}


@router.get("/activities/{farm_name}")
async def get_farm_activities(farm_name: str):
    try:
        from src.atm.orca.config import carregar_config
        from src.atm.orca.io import carregar_planilha_microplanejamento, _find_default_micro_path
        
        cfg = carregar_config()
        micro_path = _find_default_micro_path(cfg)
        if not micro_path:
            return {"activities": []}
        
        df = carregar_planilha_microplanejamento(cfg, caminho=micro_path, modo_auto=True)
        if df is None or df.empty:
            return {"activities": []}
        
        faz_norm = farm_name.strip().upper()
        faz_col = df["fazenda"].astype(str).str.strip().str.upper()
        match = df[faz_col == faz_norm]
        if match.empty:
            return {"activities": []}
        
        activities = match.groupby("atividade").agg({
            "area_ha": "sum",
            "chave": "nunique"
        }).reset_index()
        
        activities_list = []
        for _, row in activities.iterrows():
            activities_list.append({
                "atividade": str(row["atividade"]),
                "area_ha": float(row["area_ha"]),
                "talhoes": int(row["chave"])
            })
        
        return {"activities": activities_list}
    except Exception as e:
        return {"activities": [], "error": str(e)}


@router.get("/tarifas/search")
async def search_tarifas(q: str = "", limit: int = 20):
    try:
        from src.atm.orca.config import carregar_config
        from src.atm.orca.tarifas import modulo_mapeamentos_de_para
        
        cfg = carregar_config()
        tarifas = modulo_mapeamentos_de_para(cfg)
        
        if not q:
            items = list(tarifas.items())[:limit]
        else:
            q_lower = q.lower()
            items = [(k, v) for k, v in tarifas.items() if q_lower in k.lower()][:limit]
        
        results = [{"key": k, "value": v} for k, v in items]
        return {"tarifas": results}
    except Exception as e:
        return {"tarifas": [], "error": str(e)}