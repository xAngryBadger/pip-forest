import os
import asyncio
import uuid
from pathlib import Path

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.web.auth import check_password, mark_authenticated, is_authenticated, revoke_authentication
from src.web.session import get_session, list_sessions, remove_session, cleanup_old_sessions
from src.web.bridge import start_session, abort_session
from src.web.step_schema import STEP_TYPES
from src.web import term as term_module
from src.web.api_wizard import router as wizard_router

_BASE_DIR = Path(__file__).parent
_TEMPLATES_DIR = _BASE_DIR / "templates"
_STATIC_DIR = _BASE_DIR / "static"
_DATA_DIR = Path(os.environ.get("SRF_DATA_DIR", "data"))

from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(title="SRF v6.3 Web", docs_url=None, redoc_url=None)
app.add_middleware(SessionMiddleware, secret_key="orca-wizard-secret-dev-only-change-in-production")

_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
    auto_reload=True,
)

_orig_load = _jinja_env._load_template


def _patched_load(name, globals):
    try:
        return _orig_load(name, globals)
    except TypeError:
        template = _jinja_env._parse(name, globals)
        return template


_jinja_env._load_template = _patched_load

app.include_router(wizard_router)

if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


def _render(template_name: str, context: dict, status_code: int = 200) -> HTMLResponse:
    template = _jinja_env.get_template(template_name)
    html = template.render(**context)
    return HTMLResponse(content=html, status_code=status_code)


def _get_session_token(request: Request) -> str | None:
    return request.cookies.get("srf_token")


def _require_auth(request: Request) -> str:
    token = _get_session_token(request)
    if not token or not is_authenticated(token):
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return token


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return _render("login.html", {"request": request, "error": None})


@app.post("/login")
async def login_submit(request: Request, password: str = Form(...)):
    if check_password(password):
        token = str(uuid.uuid4())[:16]
        mark_authenticated(token)
        response = RedirectResponse(url="/app", status_code=303)
        response.set_cookie("srf_token", token, httponly=True, max_age=86400, samesite="lax")
        return response
    return _render("login.html", {"request": request, "error": "Senha incorreta"})


@app.get("/logout")
async def logout(request: Request):
    token = _get_session_token(request)
    if token:
        revoke_authentication(token)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("srf_token")
    return response


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    token = _get_session_token(request)
    if token and is_authenticated(token):
        return RedirectResponse(url="/app", status_code=303)
    return RedirectResponse(url="/login", status_code=303)


@app.get("/app", response_class=HTMLResponse)
async def app_main(request: Request):
    _require_auth(request)
    sessions = list_sessions()
    return _render("screens/app.html", {
        "request": request,
        "sessions": sessions,
        "step_types": list(STEP_TYPES.keys()),
    })


@app.post("/start/{mode}")
async def start_run(request: Request, mode: str):
    _require_auth(request)
    if mode not in ("single", "batch", "multi"):
        raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}")

    form = await request.form()
    params = dict(form)
    session = start_session(mode, params)

    return RedirectResponse(url=f"/session/{session.session_id}", status_code=303)


@app.get("/session/{session_id}", response_class=HTMLResponse)
async def session_view(request: Request, session_id: str):
    _require_auth(request)
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    step = session.get_pending_step()
    return _render("screens/session.html", {
        "request": request,
        "session_id": session_id,
        "step": step,
        "finished": session.finished,
        "error": session.error,
        "result_files": session.result_files,
    })


@app.post("/step/{session_id}", response_class=HTMLResponse)
async def submit_step(request: Request, session_id: str):
    _require_auth(request)
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    form = await request.form()
    value = form.get("value", "")

    step_type = form.get("step_type", "")
    if step_type in ("pedir_float", "pedir_jornada"):
        try:
            raw = str(value).replace(",", ".")
            if ":" in raw:
                parts = raw.split(":")
                value = float(parts[0]) + float(parts[1]) / 60
            else:
                value = float(raw)
        except (ValueError, TypeError):
            value = float(form.get("default", 0))
    elif step_type == "pedir_int":
        try:
            value = int(float(str(value).replace(",", ".")))
        except (ValueError, TypeError):
            try:
                value = int(float(form.get("default", 0)))
            except (ValueError, TypeError):
                value = 0
    elif step_type == "confirmar":
        val_str = str(value).lower()
        if val_str in ("abortar",):
            session.alive = False
        value = val_str in ("sim", "s", "yes", "y", "true", "1", "ok")
    elif step_type == "selecionar_paginado":
        val_str = str(value)
        if val_str in ("+", "-"):
            value = val_str
        else:
            try:
                value = int(val_str)
            except (ValueError, TypeError):
                value = 0

    session.answer(value)

    return _render("components/step.html", {
        "request": request,
        "session_id": session_id,
        "step": None,
        "finished": session.finished,
        "error": session.error,
        "result_files": session.result_files,
    })


@app.get("/step/{session_id}/pending")
async def pending_step(request: Request, session_id: str):
    _require_auth(request)
    session = get_session(session_id)
    if not session:
        return _render("components/step.html", {
            "request": request,
            "session_id": session_id,
            "step": None,
            "finished": True,
            "error": "Sessão não encontrada",
            "result_files": [],
        })
    step = session.get_pending_step()
    if step:
        return _render("components/step.html", {
            "request": request,
            "session_id": session_id,
            "step": step,
            "finished": session.finished,
            "error": session.error,
            "result_files": session.result_files,
        })
    if session.finished:
        return _render("components/step.html", {
            "request": request,
            "session_id": session_id,
            "step": None,
            "finished": True,
            "error": session.error,
            "result_files": session.result_files,
        })
    return _render("components/step.html", {
        "request": request,
        "session_id": session_id,
        "step": None,
        "finished": False,
        "error": None,
        "result_files": [],
    })


@app.get("/download/{session_id}/{filename}")
async def download_file(request: Request, session_id: str, filename: str):
    _require_auth(request)
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404)
    if filename not in session.result_files:
        raise HTTPException(status_code=404, detail="File not in session results")
    from src.atm.orca.config import OUTPUT_DIR
    file_path = Path(OUTPUT_DIR) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(str(file_path), filename=filename)


@app.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    _require_auth(request)
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    dest_dir = _DATA_DIR / "planilhas"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / file.filename

    content = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content)

    return JSONResponse({"status": "ok", "filename": file.filename, "size": len(content)})


@app.post("/term/upload/{session_id}")
async def term_upload_file(request: Request, session_id: str, file: UploadFile = File(...)):
    _require_auth(request)
    ts = term_module.get_session(session_id)
    if not ts:
        raise HTTPException(status_code=404, detail="Session not found")
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    session_dir = ts.data_dir / "planilhas"
    session_dir.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    with open(session_dir / file.filename, "wb") as f:
        f.write(content)

    return JSONResponse({"status": "ok", "filename": file.filename, "size": len(content)})


@app.post("/abort/{session_id}")
async def abort_run(request: Request, session_id: str):
    _require_auth(request)
    if abort_session(session_id):
        return JSONResponse({"status": "aborted"})
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/api/sessions")
async def api_sessions(request: Request):
    _require_auth(request)
    return JSONResponse(list_sessions())


@app.get("/api/debug/{session_id}")
async def debug_session(request: Request, session_id: str):
    _require_auth(request)
    session = get_session(session_id)
    if not session:
        return JSONResponse({"error": "not found"})
    return JSONResponse({
        "session_id": session.session_id,
        "alive": session.alive,
        "finished": session.finished,
        "error": session.error,
        "has_step": session._current_step is not None,
        "step_answered": session._step_answered.is_set(),
        "result_files": session.result_files,
    })


@app.get("/api/step-types")
async def api_step_types(request: Request):
    return JSONResponse(STEP_TYPES)


@app.get("/api/farms")
async def api_farms(request: Request):
    _require_auth(request)
    import contextlib
    from io import StringIO
    from src.atm.orca.io import carregar_planilha_microplanejamento, _find_default_micro_path
    from src.atm.orca.config import carregar_config
    cfg = carregar_config()
    micro_path = _find_default_micro_path(cfg)
    farms = []
    if micro_path:
        try:
            buf = StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                df = carregar_planilha_microplanejamento(cfg, caminho=micro_path, modo_auto=True)
            if df is not None and not df.empty and "fazenda" in df.columns:
                for faz in df["fazenda"].dropna().unique():
                    nome = str(faz).strip()
                    if not nome:
                        continue
                    sub = df[df["fazenda"] == faz]
                    farms.append({
                        "name": nome,
                        "talhoes": int(sub["chave"].nunique()) if "chave" in sub.columns else 0,
                        "area_ha": round(float(sub["area_ha"].sum()), 1) if "area_ha" in sub.columns else 0,
                        "atividades": int(sub["atividade"].nunique()) if "atividade" in sub.columns else 0,
                        "metodologias": sorted(str(m).strip() for m in sub["metodologia"].dropna().unique()) if "metodologia" in sub.columns else [],
                    })
        except Exception:
            pass
    farms.sort(key=lambda f: f["name"])
    return JSONResponse(farms)


@app.get("/term/api/sessions")
async def term_api_sessions(request: Request):
    _require_auth(request)
    return JSONResponse(term_module.list_sessions())


@app.get("/term/api/sessions/{session_id}/files")
async def term_session_files(request: Request, session_id: str):
    _require_auth(request)
    ts = term_module.get_session(session_id)
    if not ts:
        raise HTTPException(status_code=404)
    return JSONResponse({"files": ts.result_files})


@app.get("/term/download/{session_id}/{filename}")
async def term_download_file(request: Request, session_id: str, filename: str):
    _require_auth(request)
    ts = term_module.get_session(session_id)
    if not ts:
        raise HTTPException(status_code=404)
    if filename not in ts.result_files:
        raise HTTPException(status_code=404, detail="File not in session results")
    file_path = ts.data_dir / "dossiês" / filename
    if file_path.exists():
        return FileResponse(str(file_path), filename=filename)
    raise HTTPException(status_code=404, detail="File not found on disk")


@app.get("/term/{session_id}", response_class=HTMLResponse)
async def terminal_page(request: Request, session_id: str):
    _require_auth(request)
    ts = term_module.get_session(session_id)
    if not ts:
        raise HTTPException(status_code=404, detail="Terminal session not found")
    return _render("terminal.html", {"session_id": session_id})


@app.post("/term/start")
async def terminal_start(request: Request):
    token = _require_auth(request)
    ts = term_module.create_session(token)
    await term_module.start_process(ts)
    return RedirectResponse(url=f"/term/{ts.session_id}", status_code=303)


@app.websocket("/ws/term/{session_id}")
async def websocket_terminal(websocket: WebSocket, session_id: str):
    ts = term_module.get_session(session_id)
    if not ts:
        await websocket.close(code=4004)
        return

    await websocket.accept()
    ts.add_ws(websocket)

    if ts._read_task is None and ts.fd is not None:
        ts._read_task = asyncio.ensure_future(term_module.read_loop(ts))

    try:
        while True:
            raw = await websocket.receive()
            if "bytes" in raw:
                data = raw["bytes"]
                try:
                    import json
                    text = data.decode("utf-8", errors="replace")
                    msg = json.loads(text)
                    if msg.get("type") == "resize":
                        await term_module.resize_pty(ts, msg.get("rows", 24), msg.get("cols", 80))
                    continue
                except Exception:
                    pass
                await term_module.write_to_process(ts, data)
            elif "text" in raw:
                text = raw["text"]
                try:
                    import json
                    msg = json.loads(text)
                    if msg.get("type") == "resize":
                        await term_module.resize_pty(ts, msg.get("rows", 24), msg.get("cols", 80))
                        continue
                except Exception:
                    pass
                await term_module.write_to_process(ts, text.encode("utf-8"))
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        ts.remove_ws(websocket)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("SRF_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
