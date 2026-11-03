"""
Interface Streamlit — Atendente Virtual Marina | Empório da Música
Desafio Técnico AI Engineer — Artefact
"""
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from datetime import datetime

import streamlit as st

# Log de latência da Marina no console do Streamlit:
#   streamlit run app.py  ->  mostra "gemini: ok modelo=... ttft=... total=..."
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

# Configuração da página e SEO
st.set_page_config(
    page_title="Empório da Música — Marina Atendente Virtual",
    page_icon="🎸",
    layout="wide",
    initial_sidebar_state="expanded",
)

from agent import DEFAULT_PROVIDER, PROVIDERS, run_agent_turn_stream
from core.logger import log_turn
from core.persistence import list_sessions, load_session, new_session_id, save_message
from core.rate_limiter import check_rate_limit, get_rate_limit_metrics

# Quantas mensagens do histórico vão para a IA. Manter o recorte evita que a
# latência cresça a cada turno (contexto inteiro era reenviado sempre) e que a
# saudação longa fique ocupando tokens para sempre.
HISTORY_WINDOW = 12


@st.cache_resource(show_spinner=False)
def _prewarm_data() -> None:
    """Carrega CSVs + PDF uma vez por processo, em background.

    Sem isso a primeira pergunta do usuário pagava ~1,7 s só de I/O (pandas +
    pdfplumber) dentro do spinner — agora esse custo some durante o carregamento
    da página.
    """
    import threading

    from core.loader import get_data

    threading.Thread(target=get_data, daemon=True).start()


_prewarm_data()

# Injeta CSS refinado para visual profissional
st.markdown("""
<style>
    /* Estilos do cabeçalho */
    .store-header {
        background: linear-gradient(135deg, #2b1d0c 0%, #4a2e12 50%, #7c4a1e 100%);
        color: #ffffff;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.15);
    }
    .store-title {
        font-size: 2.1rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .store-subtitle {
        font-size: 1.05rem;
        color: #f3d9b1;
        margin-bottom: 0.5rem;
    }
    .store-badge {
        display: inline-block;
        background: rgba(255, 255, 255, 0.18);
        border: 1px solid rgba(255, 255, 255, 0.3);
        padding: 0.2rem 0.75rem;
        border-radius: 20px;
        font-size: 0.82rem;
        color: #fff;
    }
    /* Estilos para o pensamento ReAct no chat */
    .react-box {
        background-color: #fbf8f2;
        border-left: 4px solid #b87333;
        padding: 0.8rem 1rem;
        border-radius: 6px;
        margin-bottom: 0.8rem;
        font-size: 0.88rem;
        color: #3d312a;
    }
    .footer-text {
        text-align: center;
        padding: 2rem 0 1rem 0;
        font-size: 0.88rem;
        color: #7d7268;
        border-top: 1px solid #e8e2d8;
        margin-top: 3rem;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?auto=format&fit=crop&w=400&q=80", use_container_width=True)
    st.title("⚙️ Painel do Avaliador")
    st.caption("Controle técnico para teste do agente")

    _provider_keys = list(PROVIDERS.keys())
    selected_provider = st.selectbox(
        "Provedor / Modelo",
        _provider_keys,
        index=_provider_keys.index(DEFAULT_PROVIDER),
    )
    pcfg = PROVIDERS[selected_provider]
    st.markdown(f"**Modelo:** ⚡ {selected_provider}")

    try:
        active_key = st.secrets.get(pcfg["env_key"], os.getenv(pcfg["env_key"], ""))
    except Exception:
        active_key = os.getenv(pcfg["env_key"], "")

    debug_mode = st.toggle("🔍 Modo Debug (Raciocínio ReAct)", value=True, help="Exibe ferramentas chamadas e dados consultados em tempo real.")

    if debug_mode:
        with st.expander("📊 Métricas de Rate Limit", expanded=False):
            metrics = get_rate_limit_metrics()
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Requisições Total", metrics["total_requests"])
                st.metric("Taxa de Rejeição", f"{metrics['rejection_rate']*100:.1f}%")
            with col2:
                st.metric(f"Último Min: {metrics['requests_last_minute']}/{metrics['limit_per_minute']}",
                         f"{metrics['requests_last_minute']}/{metrics['limit_per_minute']}")
                st.metric(f"Última Hora: {metrics['requests_last_hour']}/{metrics['limit_per_hour']}",
                         f"{metrics['requests_last_hour']}/{metrics['limit_per_hour']}")

    st.markdown("---")
    if st.button("🔄 Reiniciar Atendimento / Nova Conversa", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = new_session_id()
        st.rerun()

    st.markdown("---")
    st.markdown("### 💾 Histórico de Conversas")

    @st.cache_data(ttl=30)
    def _cached_sessions():
        return list_sessions(limit=5)

    saved_sessions = _cached_sessions()
    if saved_sessions:
        for s in saved_sessions:
            label = f"📝 {s['started'][:16]} ({s['messages']} msgs)"
            if st.button(label, key=f"load_{s['session_id']}", use_container_width=True):
                st.session_state.session_id = s["session_id"]
                st.session_state.messages = load_session(s["session_id"])
                st.rerun()
    else:
        st.caption("Nenhuma conversa salva ainda.")

    st.markdown("---")
    st.markdown("### 📌 Ferramentas Ativas")
    st.markdown("""
    - `search_products`: Catálogo de 65 produtos
    - `get_order_status`: 20 pedidos com rastreio
    - `check_promotions`: Promoções vigentes
    - `search_policies`: Políticas oficiais em PDF
    """)

# ----------------- CABEÇALHO -----------------
st.markdown("""
<div class="store-header">
    <div class="store-title">🎸 Empório da Música</div>
    <div class="store-subtitle">Sua loja de instrumentos musicais em Campo Grande/MS</div>
    <span class="store-badge">Atendimento Inteligente com Marina</span>
    &nbsp;
    <span class="store-badge">Arquitetura ReAct + Function Calling</span>
</div>
""", unsafe_allow_html=True)

# ----------------- ESTADO DA SESSÃO -----------------
WELCOME_MESSAGE = (
    "Olá! Sou a **Marina**, assistente virtual da **Empório da Música**! 🎸🎶\n\n"
    "Estou aqui para te ajudar a escolher o instrumento ideal, conferir disponibilidade e preços "
    "do nosso catálogo de Campo Grande/MS, rastrear seus pedidos ou tirar dúvidas sobre nossas "
    "políticas de troca, frete e garantia.\n\n"
    "💡 **Para os avaliadores técnicos:**\n"
    "- Vocês podem ver meu raciocínio ativando o **Modo Debug** na barra lateral.\n"
    "- Escolha o modelo na barra lateral (MiMo Flash ou Groq).\n"
    "- Para testar rapidamente, basta clicar em um dos botões de exemplo logo abaixo!"
)

if "session_id" not in st.session_state:
    st.session_state.session_id = new_session_id()

if "messages" not in st.session_state or len(st.session_state.messages) == 0:
    st.session_state.messages = [
        {"role": "assistant", "content": WELCOME_MESSAGE, "thoughts": []}
    ]

# ----------------- HISTÓRICO DE CHAT -----------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        # Se houver pensamentos gravados e debug estiver ligado
        if debug_mode and msg.get("thoughts"):
            with st.expander("🧠 Raciocínio do Agente (ReAct & Tool Calls)", expanded=False):
                for t in msg["thoughts"]:
                    st.markdown(f"**Etapa {t['step']} — Ferramenta:** `{t['tool']}`")
                    st.json({"Argumentos": t["args"], "Retorno": t["observation"]})
        st.markdown(msg["content"])

# ----------------- ENTRADA DO USUÁRIO -----------------
user_input = st.chat_input("Digite sua dúvida sobre instrumentos, pedidos ou políticas...")

# ----------------- SUGESTÕES RÁPIDAS (fixas no rodapé) -----------------
prompt_to_send = None
bcol1, bcol2, bcol3, bcol4 = st.bottom.columns(4)
if bcol1.button("🎸 Violões até R$1.000", use_container_width=True):
    prompt_to_send = "Olá! Quais violões vocês têm disponíveis por até R$ 1.000?"
if bcol2.button("📦 Rastrear Pedido #1", use_container_width=True):
    prompt_to_send = "Gostaria de saber o status e rastreamento do pedido 1."
if bcol3.button("🏷️ Promoções Ativas", use_container_width=True):
    prompt_to_send = "Quais produtos estão em promoção ativa hoje?"
if bcol4.button("🔄 Política de Devolução", use_container_width=True):
    prompt_to_send = "Como funciona a política de devolução e prazo de arrependimento da loja?"

final_prompt = prompt_to_send or user_input

if final_prompt:
    # Rate limiting check
    if not check_rate_limit():
        st.error(
            "⏳ **Limite de requisições atingido!**\n\n"
            "Aguarde um momento antes de enviar outra mensagem. "
            "Limite: 10 mensagens por minuto, 100 por hora."
        )
        st.stop()

    # Exibe a mensagem do usuário imediatamente
    st.session_state.messages.append({"role": "user", "content": final_prompt})
    save_message(st.session_state.session_id, "user", final_prompt)
    with st.chat_message("user"):
        st.markdown(final_prompt)

    # Histórico recortado: só as últimas N mensagens vão para a IA
    agent_msgs = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
    ][-HISTORY_WINDOW:]

    # Estado do turno — o gerador preenche enquanto o texto aparece na tela.
    turn = {"response": "", "streamed": "", "thoughts": [], "timing": {},
            "text_yielded": False}

    def _ui_stream(stream):
        for event in stream:
            if event["type"] == "text":
                turn["text_yielded"] = True
                turn["streamed"] += event["text"]
                yield event["text"]
            elif event["type"] == "done":
                turn["response"] = event["response"]
                turn["thoughts"] = event["thoughts"]
                turn["timing"] = event["timing"]

    # Processa resposta da Marina (streaming: o texto sai token a token)
    with st.chat_message("assistant"):
        with st.spinner("🎸 Marina está consultando as informações da loja..."):
            try:
                st.write_stream(
                    _ui_stream(
                        run_agent_turn_stream(
                            messages=agent_msgs,
                            api_key=active_key,
                            provider=selected_provider,
                        )
                    )
                )
            except Exception as e:
                if turn["text_yielded"]:
                    turn["response"] = (
                        (turn["response"] or turn["streamed"])
                        + "\n\n_(conexão instável no meio da resposta — "
                        "se faltar algo, mande de novo que eu completo)_"
                    )
                else:
                    turn["response"] = (
                        f"Ops! Tivemos uma instabilidade ao conectar com a IA: {e}\n\n"
                        "Por favor, confira se sua chave de API está preenchida "
                        "corretamente na barra lateral."
                    )
                turn["thoughts"] = []

        # O que foi para a tela é o que vai para o histórico: se o evento final
        # não chegou (gerador interrompido), guarda o que já foi streamado.
        if not turn["response"]:
            turn["response"] = turn["streamed"]

        # Caminhos de erro entregam só o evento final, sem pedaços de texto:
        # nesses casos renderizamos a resposta aqui.
        if not turn["text_yielded"]:
            st.markdown(turn["response"])

        thoughts = turn["thoughts"]
        if debug_mode and thoughts:
            with st.expander("🧠 Raciocínio do Agente (ReAct & Tool Calls)", expanded=False):
                for t in thoughts:
                    st.markdown(f"**Etapa {t['step']} — Ferramenta:** `{t['tool']}`")
                    st.json({"Argumentos": t["args"], "Retorno": t["observation"]})

        if debug_mode and turn["timing"]:
            tm = turn["timing"]
            token_info = ""
            if tm.get("total_tokens"):
                token_info = f" · tokens: {tm.get('prompt_tokens', 0)}↑ + {tm.get('completion_tokens', 0)}↓ = {tm['total_tokens']}"
            st.caption(
                f"⏱️ 1º token: {tm.get('ttft_ms') or '—'} ms · "
                f"turno total: {tm.get('total_ms') or '—'} ms · "
                f"modelo: {tm.get('modelo') or '—'} · "
                f"rodadas de ferramenta: {tm.get('rodadas_de_ferramenta')}"
                f"{token_info}"
            )

    assistant_response = turn["response"]
    st.session_state.messages.append({
        "role": "assistant",
        "content": assistant_response,
        "thoughts": thoughts,
    })
    save_message(st.session_state.session_id, "assistant", assistant_response, thoughts)
    log_turn(st.session_state.session_id, final_prompt, thoughts, turn["timing"], assistant_response)

# ----------------- RODAPÉ OBRIGATÓRIO -----------------
current_year = datetime.now().year
st.markdown(f"""
<div class="footer-text">
    Gustavo Chiposche Pedro. Todos os direitos reservados © {current_year}
</div>
""", unsafe_allow_html=True)
