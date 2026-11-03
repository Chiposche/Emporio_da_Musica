"""
Mecanismo ReAct com Function Calling via APIs OpenAI-compatíveis (multi-provedor).
Streaming + raciocínio passo-a-passo (Thought/Action/Observation).

Desenho de latência:
  * stream=True — o primeiro token chega à UI antes da resposta terminar;
  * cliente HTTP cacheado por chave — nenhum handshake TCP/TLS por mensagem;
  * histórico recortado (ver HISTORY_WINDOW no app) — o contexto não cresce à toa;
  * instrumentação — tempo por chamada, TTFT e modelo usado saem no log e no Debug.
  * retry automático — timeouts/rate limits são recuperados sem falhar imediatamente.
"""
import json
import logging
import os
import time
from functools import lru_cache
from typing import Any, Generator, Optional

from core.errors import categorize_error, get_recovery_strategy, ErrorRecovery
from persona import SYSTEM_PROMPT
from tools.order_lookup import get_order_status
from tools.policy_search import search_policies
from tools.product_search import search_products
from tools.promotion_check import check_promotions

log = logging.getLogger("emporio.agent")

TOOL_MAP = {
    "search_products": search_products,
    "get_order_status": get_order_status,
    "check_promotions": check_promotions,
    "search_policies": search_policies,
}

PROVIDERS = {
    "MiMo V2.6 Flash (OpenRouter)": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "xiaomi/mimo-v2.6-flash",
        "env_key": "OPENROUTER_API_KEY",
        "key_help": "https://openrouter.ai/keys",
        "placeholder": "sk-or-...",
    },
    "Groq Qwen 3.8 27B": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "qwen/qwen3.8-27b",
        "env_key": "GROQ_API_KEY",
        "key_help": "https://console.groq.com",
        "placeholder": "gsk_...",
    },
    "OpenRouter Free (Gratuito)": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openrouter/free",
        "env_key": "OPENROUTER_API_KEY",
        "key_help": "https://openrouter.ai/keys",
        "placeholder": "sk-or-...",
    },
}

DEFAULT_PROVIDER = "MiMo V2.6 Flash (OpenRouter)"
REQUEST_TIMEOUT_MS = 30_000

# Configuração de retry automático
MAX_RETRIES = 3
RETRY_BACKOFF_MS = [300, 600, 1200]  # Backoff exponencial: 300ms → 600ms → 1200ms
GLOBAL_TIMEOUT_MS = 45_000  # Timeout total (todas as tentativas)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Busca produtos no catálogo da loja por termo/nome, preço máximo, categoria e disponibilidade de estoque.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Termo de busca, nome do instrumento ou marca (ex: violão, yamaha, fender, teclado)",
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Preço máximo em reais (BRL)",
                    },
                    "category": {
                        "type": "string",
                        "description": "Nome da categoria (ex: Cordas, Teclas, Percussão, Áudio)",
                    },
                    "in_stock_only": {
                        "type": "boolean",
                        "description": "Se verdadeiro, filtra apenas produtos com estoque > 0",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Consulta status de pedido, código de rastreio, previsão de entrega e itens comprados por ID de pedido ou nome do cliente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "integer",
                        "description": "Número/ID do pedido",
                    },
                    "customer_name": {
                        "type": "string",
                        "description": "Nome completo ou parcial do cliente",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_promotions",
            "description": "Verifica promoções vigentes e ativas para um produto específico ou lista as promoções ativas gerais.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "ID do produto",
                    },
                    "product_name": {
                        "type": "string",
                        "description": "Nome ou termo do produto",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_policies",
            "description": "Consulta trechos oficiais das políticas da loja (horários de atendimento, trocas, devoluções, frete, garantia, pagamento).",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Assunto a consultar (ex: devolução, horário, frete, garantia, formas de pagamento)",
                    },
                },
                "required": ["topic"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def run_agent_turn(
    messages: list[dict],
    api_key: Optional[str] = None,
    max_steps: int = 10,
    provider: str = DEFAULT_PROVIDER,
) -> dict:
    response: str = ""
    thoughts: list[dict] = []
    timing: dict[str, Any] = {}

    for event in run_agent_turn_stream(messages, api_key, max_steps, provider):
        if event["type"] == "done":
            response = event["response"]
            thoughts = event["thoughts"]
            timing = event["timing"]
        elif event["type"] == "thought":
            thoughts.append(event["thought"])
        elif event["type"] == "timing":
            timing = event["timing"]

    return {"response": response, "thoughts": thoughts, "timing": timing}


def _retry_with_backoff(
    messages: list[dict],
    api_key: Optional[str],
    max_steps: int,
    cfg: dict,
) -> Generator[dict, None, None]:
    """
    Executa _stream_llm com retry automático usando backoff exponencial.

    Reage a erros recuperáveis (timeout, rate limit) com retry automático.
    Erros não-recuperáveis falham imediatamente.
    """
    t_global_start = time.perf_counter()

    for attempt_num in range(1, MAX_RETRIES + 1):
        try:
            # Verificar timeout global
            elapsed_ms = (time.perf_counter() - t_global_start) * 1000
            if elapsed_ms > GLOBAL_TIMEOUT_MS:
                log.warning(
                    "Global timeout (%dms) reached, giving up after %d attempts",
                    GLOBAL_TIMEOUT_MS, attempt_num - 1
                )
                break

            # Executar stream_llm
            yield from _stream_llm(messages, api_key, max_steps, cfg)
            return  # Sucesso, sair

        except Exception as e:
            error_type = categorize_error(e)
            strategy = get_recovery_strategy(error_type)
            elapsed_ms = (time.perf_counter() - t_global_start) * 1000

            log.warning(
                "Attempt %d/%d failed: %s (error_type=%s, strategy=%s, elapsed=%dms)",
                attempt_num, MAX_RETRIES, e, error_type.value, strategy.value, elapsed_ms
            )

            if strategy == ErrorRecovery.FAIL or attempt_num >= MAX_RETRIES:
                # Não há mais retries, ou erro não é recuperável
                log.error(
                    "Error not recoverable or max retries exceeded: %s (error_type=%s)",
                    e, error_type.value
                )
                raise

            # Backoff exponencial antes do próximo retry
            if attempt_num < MAX_RETRIES:
                backoff_ms = RETRY_BACKOFF_MS[attempt_num - 1]
                backoff_s = backoff_ms / 1000
                log.info("Backoff %dms before retry attempt %d", backoff_ms, attempt_num + 1)
                time.sleep(backoff_s)


def run_agent_turn_stream(
    messages: list[dict],
    api_key: Optional[str] = None,
    max_steps: int = 10,
    provider: str = DEFAULT_PROVIDER,
) -> Generator[dict, None, None]:
    """
    Gerador de eventos dict para streaming.

    Tipos de evento:
      {"type": "text",    "text": str}
      {"type": "thought", "thought": dict}
      {"type": "timing",  "timing": dict}
      {"type": "done",    ...}

    Implementa retry automático com backoff exponencial para erros recuperáveis.
    """
    provider_cfg = PROVIDERS.get(provider, PROVIDERS[DEFAULT_PROVIDER])
    try:
        # Tenta com retry automático para este provider
        yield from _retry_with_backoff(messages, api_key, max_steps, provider_cfg)
    except Exception as e:
        log.warning("provider %s falhou após retries: %s — tentando fallback", provider, e)
        fallback_cfg = next(
            (cfg for name, cfg in PROVIDERS.items() if cfg != provider_cfg),
            None,
        )
        if fallback_cfg:
            fb_key = os.getenv(fallback_cfg["env_key"], "")
            if fb_key:
                try:
                    yield {"type": "text", "text": f"_(alternando para {fallback_cfg['model']}…)_\n\n"}
                    # Tenta fallback provider também com retry
                    yield from _retry_with_backoff(messages, fb_key, max_steps, fallback_cfg)
                    return
                except Exception as e2:
                    log.exception("fallback também falhou após retries: %s", e2)
        yield _event_done(
            f"Ops! Tivemos uma instabilidade ao conectar com a IA ({type(e).__name__}): {e}\n\n"
            "Por favor, confira se sua chave de API está preenchida corretamente na barra lateral.",
            [], {},
        )


# ---------------------------------------------------------------------------
# Infra
# ---------------------------------------------------------------------------

def _run_tool(fn_name: str, fn_args: dict) -> Any:
    tool_fn = TOOL_MAP.get(fn_name)
    if not tool_fn:
        return {"error": f"Ferramenta {fn_name} não encontrada."}
    try:
        result = tool_fn(**fn_args)
    except Exception as e:
        return {"error": str(e)}
    return json.loads(json.dumps(result, ensure_ascii=False, default=str))


@lru_cache(maxsize=8)
def _get_client(api_key: str, base_url: str):
    import openai
    return openai.OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=REQUEST_TIMEOUT_MS / 1000,
    )


def _thought(step: int, tool: str, args: dict, observation: Any) -> dict:
    return {"step": step, "tool": tool, "args": args, "observation": observation}


def _timing(
    model_name: str,
    rounds: int,
    ttft_ms: Optional[float],
    t_start: float,
    errors: list[str],
) -> dict:
    return {
        "modelo": model_name,
        "rodadas_de_ferramenta": rounds,
        "ttft_ms": round(ttft_ms) if ttft_ms else None,
        "total_ms": round((time.perf_counter() - t_start) * 1000),
        "fallbacks": errors,
    }


def _event_done(response: str, thoughts: list[dict], timing: dict) -> dict:
    return {"type": "done", "response": response, "thoughts": thoughts, "timing": timing}


# ---------------------------------------------------------------------------
# Streaming genérico — chat.completions (API OpenAI-compatível)
# ---------------------------------------------------------------------------

def _stream_llm(
    messages: list[dict],
    api_key: Optional[str],
    max_steps: int,
    cfg: dict,
) -> Generator[dict, None, None]:
    model = cfg["model"]
    key = api_key or os.getenv(cfg["env_key"])
    if not key:
        yield _event_done(
            f"Por favor, configure sua chave {cfg['env_key']} na barra lateral para conversar comigo!\n\n"
            f"Pegue sua chave em: {cfg['key_help']}",
            [], {},
        )
        return

    client = _get_client(key, cfg["base_url"])
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in messages:
        api_messages.append({"role": m["role"], "content": m["content"]})

    thoughts: list[dict] = []
    parts: list[str] = []
    streamed = False
    t_start = time.perf_counter()
    ttft_ms: Optional[float] = None
    usage_tokens: dict[str, int] = {}

    try:
        for step in range(1, max_steps + 1):
            stream = client.chat.completions.create(
                model=model,
                messages=api_messages,
                tools=TOOLS,
                tool_choice="auto",
                stream=True,
            )

            tool_acc: dict[int, dict] = {}

            for chunk in stream:
                if hasattr(chunk, "usage") and chunk.usage:
                    u = chunk.usage
                    usage_tokens["prompt_tokens"] = getattr(u, "prompt_tokens", 0) or 0
                    usage_tokens["completion_tokens"] = getattr(u, "completion_tokens", 0) or 0
                    usage_tokens["total_tokens"] = getattr(u, "total_tokens", 0) or 0
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    if ttft_ms is None:
                        ttft_ms = (time.perf_counter() - t_start) * 1000
                    streamed = True
                    parts.append(delta.content)
                    yield {"type": "text", "text": delta.content}
                for tc in (delta.tool_calls or []):
                    acc = tool_acc.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                    if tc.id:
                        acc["id"] = tc.id
                    if tc.function and tc.function.name:
                        acc["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        acc["arguments"] += tc.function.arguments

            if not tool_acc:
                response = "".join(parts).strip()
                timing = _timing(model, step, ttft_ms, t_start, [])
                timing.update(usage_tokens)
                thoughts.append(_thought(0, "_timing", {"modelo": model}, timing))
                log.info(
                    "%s: ok rodadas=%s ttft=%s total=%.0fms",
                    model,
                    step,
                    f"{ttft_ms:.0f}ms" if ttft_ms else "n/a",
                    (time.perf_counter() - t_start) * 1000,
                )
                yield _event_done(response, thoughts, timing)
                return

            api_messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": acc["id"] or f"call_{idx}",
                        "type": "function",
                        "function": {
                            "name": acc["name"],
                            "arguments": acc["arguments"] or "{}",
                        },
                    }
                    for idx, acc in sorted(tool_acc.items())
                ],
            })

            for idx, acc in sorted(tool_acc.items()):
                try:
                    fn_args = json.loads(acc["arguments"] or "{}")
                except Exception:
                    fn_args = {}
                tool_result = _run_tool(acc["name"], fn_args)
                thoughts.append(_thought(step, acc["name"], fn_args, tool_result))
                api_messages.append({
                    "role": "tool",
                    "tool_call_id": acc["id"] or f"call_{idx}",
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })

    except Exception as e:
        error_type = categorize_error(e)
        elapsed_ms = int((time.perf_counter() - t_start) * 1000)
        log.warning(
            "%s: falha após %s ms: %s (error_type=%s)",
            model, elapsed_ms, e, error_type.value
        )
        if streamed:
            yield _event_done(
                "".join(parts) + "\n\n_(conexão instável no meio da resposta — "
                "se faltar algo, mande de novo que eu completo)_",
                thoughts, _timing(model, 0, ttft_ms, t_start, [f"{error_type.value}: {str(e)}"]),
            )
            return
        yield _event_done(
            f"Ops! Tivemos uma instabilidade ao conectar com a IA ({type(e).__name__}): {e}\n\n"
            "Por favor, confira se sua chave de API está preenchida corretamente na barra lateral.",
            thoughts, _timing(model, 0, ttft_ms, t_start, [f"{error_type.value}: {str(e)}"]),
        )
        return

    yield _event_done(
        "Não consegui concluir a consulta dentro do limite de "
        f"iterações ({max_steps}). Tente reformular a pergunta.",
        thoughts, _timing(model, max_steps, ttft_ms, t_start, []),
    )
