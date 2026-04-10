"""
Adaptador opcional para Ollama (LLM local).
Ativado por feature flag; o app funciona 100% sem ele.

Uso recomendado:
  - qwen2.5:3b  -> de_para, conferência de regras, inconsistências pontuais
  - gemma3:4b   -> resumo analítico e explicação de achados

Configuração via variáveis de ambiente:
  SRF_OLLAMA_ENABLED=1
  SRF_OLLAMA_URL=http://localhost:11434
  SRF_OLLAMA_MODEL=qwen2.5:3b
"""
import json
import os
from typing import Any

OLLAMA_ENABLED = os.environ.get("SRF_OLLAMA_ENABLED", "0").strip().lower() in ("1", "true", "yes")
OLLAMA_URL = os.environ.get("SRF_OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("SRF_OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_ANALYSIS_MODEL = os.environ.get("SRF_OLLAMA_ANALYSIS_MODEL", "gemma3:4b")


def is_available() -> bool:
    if not OLLAMA_ENABLED:
        return False
    try:
        import urllib.request
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def _call_ollama(prompt: str, model: str | None = None, max_tokens: int = 1024) -> str | None:
    if not OLLAMA_ENABLED:
        return None
    try:
        import urllib.request
        payload = json.dumps({
            "model": model or OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": 0.3},
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("response", "")
    except Exception as ex:
        return f"[ollama erro: {ex}]"


def suggest_de_para(atividades_micro: list[str], atividades_tarifa: list[str]) -> list[dict]:
    """
    Pede ao modelo leve (qwen2.5:3b) para sugerir mapeamentos de_para
    entre atividades do micro e atividades da tarifa.
    """
    if not OLLAMA_ENABLED or not atividades_micro or not atividades_tarifa:
        return []

    prompt = (
        "Você é um assistente de mapeamento de atividades florestais.\n"
        "Dadas as atividades do microplanejamento e as atividades da tabela de tarifas,\n"
        "sugira o mapeamento mais provável (de_para).\n"
        "Responda APENAS em JSON: [{\"micro\": \"...\", \"tarifa\": \"...\", \"confianca\": 0.0-1.0}]\n\n"
        f"Atividades micro: {json.dumps(atividades_micro[:30], ensure_ascii=False)}\n"
        f"Atividades tarifa: {json.dumps(atividades_tarifa[:50], ensure_ascii=False)}\n"
        "JSON:"
    )
    raw = _call_ollama(prompt, model=OLLAMA_MODEL, max_tokens=2048)
    if not raw:
        return []
    try:
        start = raw.index("[")
        end = raw.rindex("]") + 1
        return json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        return [{"raw_response": raw}]


def analyze_report(parsed_summary: dict, insights: list[dict]) -> str | None:
    """
    Pede ao modelo analítico (gemma3:4b) para sumarizar achados
    em linguagem natural a partir do parsing + regras.
    """
    if not OLLAMA_ENABLED:
        return None

    kpis = {}
    if parsed_summary.get("financeiro"):
        kpis.update(parsed_summary["financeiro"].get("kpis", {}))
    if parsed_summary.get("operacional"):
        kpis.update(parsed_summary["operacional"].get("kpis", {}))

    crono = parsed_summary.get("cronograma", {})
    alerts = [f"[{i['severidade']}] {i['titulo']}: {i['descricao']}" for i in insights[:10]]

    prompt = (
        "Você é um analista de restauração florestal.\n"
        "Com base nos KPIs e alertas abaixo, escreva um parágrafo curto (3-5 frases) "
        "com as conclusões mais importantes e uma recomendação prática.\n\n"
        f"KPIs: {json.dumps(kpis, ensure_ascii=False, default=str)}\n"
        f"Cronograma: {json.dumps({k: crono.get(k) for k in ('dias', 'hh_total', 'n_talhoes', 'n_atividades', 'n_turmas') if crono.get(k)}, ensure_ascii=False)}\n"
        f"Alertas: {json.dumps(alerts, ensure_ascii=False)}\n\n"
        "Conclusão:"
    )
    return _call_ollama(prompt, model=OLLAMA_ANALYSIS_MODEL, max_tokens=512)


def status() -> dict[str, Any]:
    """Retorna estado do adaptador Ollama para diagnóstico."""
    avail = is_available()
    return {
        "enabled": OLLAMA_ENABLED,
        "available": avail,
        "url": OLLAMA_URL,
        "model_fast": OLLAMA_MODEL,
        "model_analysis": OLLAMA_ANALYSIS_MODEL,
    }
