"""
📊 Painel de Analytics — Empório da Música
Lê os logs estruturados (JSONL) e exibe métricas de uso do agente.
"""
import json
from collections import Counter
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Analytics — Empório da Música", page_icon="📊", layout="wide")

LOG_PATH = Path(__file__).parent.parent / "logs" / "agent.jsonl"


@st.cache_data(ttl=10)
def load_logs() -> pd.DataFrame:
    if not LOG_PATH.exists():
        return pd.DataFrame()
    rows = []
    for line in LOG_PATH.read_text(encoding="utf-8").strip().splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


st.title("📊 Analytics do Agente Marina")
st.caption("Dados extraídos de `logs/agent.jsonl` — atualiza automaticamente a cada 10s")

df = load_logs()

if df.empty:
    st.info("Nenhum log encontrado ainda. Converse com a Marina no chat principal para gerar dados!")
    st.stop()

# --------------- MÉTRICAS GERAIS ---------------
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

col1.metric("Total de turnos", len(df))

avg_total = df["total_ms"].dropna().mean()
col2.metric("Latência média", f"{avg_total:.0f} ms" if pd.notna(avg_total) else "—")

avg_ttft = df["ttft_ms"].dropna().mean()
col3.metric("TTFT médio", f"{avg_ttft:.0f} ms" if pd.notna(avg_ttft) else "—")

unique_sessions = df["session_id"].nunique()
col4.metric("Sessões únicas", unique_sessions)

# --------------- TOOLS MAIS CHAMADAS ---------------
st.markdown("---")
left, right = st.columns(2)

with left:
    st.subheader("🔧 Ferramentas mais chamadas")
    tool_counts = Counter()
    for tools_list in df["tools_called"]:
        if isinstance(tools_list, list):
            for t in tools_list:
                if isinstance(t, dict) and "name" in t:
                    tool_counts[t["name"]] += 1

    if tool_counts:
        tool_df = pd.DataFrame(
            tool_counts.most_common(),
            columns=["Ferramenta", "Chamadas"],
        )
        chart = alt.Chart(tool_df).mark_bar(orient="horizontal").encode(
            x="Chamadas:Q",
            y=alt.Y("Ferramenta:N", sort="-x"),
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.caption("Nenhuma ferramenta chamada ainda.")

with right:
    st.subheader("🤖 Providers utilizados")
    if "provider" in df.columns:
        provider_df = df["provider"].value_counts().reset_index()
        provider_df.columns = ["Provider", "Contagem"]
        chart = alt.Chart(provider_df).mark_bar(orient="horizontal").encode(
            x="Contagem:Q",
            y=alt.Y("Provider:N", sort="-x"),
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.caption("Sem dados de provider.")

# --------------- LATÊNCIA AO LONGO DO TEMPO ---------------
st.markdown("---")
st.subheader("⏱️ Latência ao longo do tempo")

time_df = df[["timestamp", "total_ms", "ttft_ms"]].dropna(subset=["total_ms"]).set_index("timestamp")
if not time_df.empty:
    time_df.columns = ["Total (ms)", "TTFT (ms)"]
    st.line_chart(time_df)
else:
    st.caption("Sem dados de latência.")

# --------------- LOGS RECENTES ---------------
st.markdown("---")
st.subheader("📋 Logs recentes")

display_cols = ["timestamp", "session_id", "user_message", "provider", "ttft_ms", "total_ms", "response_length"]
available_cols = [c for c in display_cols if c in df.columns]
st.dataframe(
    df[available_cols].sort_values("timestamp", ascending=False).head(20),
    use_container_width=True,
    hide_index=True,
)
