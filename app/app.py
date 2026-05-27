"""
Interface Streamlit do BluaDiagnostics.

Para rodar:
    streamlit run app/app.py

A interface mostra:
- Chat principal estilo ChatGPT
- Sidebar com seletor de paciente
- Visualização em tempo real do agente ativo
- Documentos RAG recuperados
- Tools chamadas
- Alerta visual de red flag
"""

import sys
import os
from pathlib import Path

# Garante que o Python encontre o módulo src/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from src.graph.graph import app_graph


# ─── Configuração da página ───────────────────────────────────

st.set_page_config(
    page_title="BluaDiagnostics — Care Plus",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─── CSS customizado (visual mais limpo) ──────────────────────

st.markdown("""
<style>
.red-flag-banner {
    background-color: #ffebee;
    border-left: 4px solid #c62828;
    padding: 12px;
    border-radius: 4px;
    margin: 8px 0;
}
.agent-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 12px;
    font-weight: 600;
    font-size: 14px;
}
.badge-triagem { background-color: #e3f2fd; color: #1565c0; }
.badge-prescricao { background-color: #f3e5f5; color: #6a1b9a; }
.badge-escalada { background-color: #ffebee; color: #c62828; }
.rag-card {
    background-color: #f5f5f5;
    padding: 8px 12px;
    border-radius: 6px;
    margin: 4px 0;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)


# ─── Header ───────────────────────────────────────────────────

st.title("🏥 BluaDiagnostics")
st.caption("Assistente virtual de check-up digital — Care Plus / Blua")


# ─── Inicializa estado da sessão ──────────────────────────────

if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

if "ultimo_resultado" not in st.session_state:
    st.session_state.ultimo_resultado = None


# ─── Sidebar: configurações e visualização ────────────────────

with st.sidebar:
    st.header("⚙️ Sessão")

    paciente_id = st.selectbox(
        "Beneficiário",
        ["BEN-MARIA", "BEN-DEMO"],
        help="ID do beneficiário Care Plus para esta sessão",
    )

    st.markdown(f"**Paciente:** {paciente_id}")

    if st.button("🔄 Limpar conversa", use_container_width=True):
        st.session_state.mensagens = []
        st.session_state.ultimo_resultado = None
        st.rerun()

    st.divider()

    # Painel de observabilidade
    st.header("🔍 Observabilidade")

    if st.session_state.ultimo_resultado:
        r = st.session_state.ultimo_resultado

        # Agente ativo
        agente = r.get("agente_atual", "—")
        badge_class = f"badge-{agente}" if agente in ["triagem", "prescricao", "escalada"] else ""
        st.markdown("**Agente que respondeu:**")
        st.markdown(
            f'<span class="agent-badge {badge_class}">{agente.upper()}</span>',
            unsafe_allow_html=True,
        )

        # Red flag
        if r.get("red_flag"):
            st.markdown(
                '<div class="red-flag-banner">🚨 <b>RED FLAG detectada</b><br>'
                'Protocolo de emergência acionado</div>',
                unsafe_allow_html=True,
            )

        # Tools chamadas
        st.markdown("**🔧 Tools chamadas:**")
        tools = r.get("tools_log", [])
        if tools:
            for t in tools:
                st.code(t["tool"], language=None)
        else:
            st.caption("Nenhuma tool chamada")

        # Documentos RAG
        st.markdown("**📄 Documentos RAG:**")
        docs = r.get("contexto_rag", [])
        if docs:
            for d in docs:
                st.markdown(
                    f'<div class="rag-card"><b>{d["fonte"]}</b><br>'
                    f'<small>score: {d["score"]:.3f}</small><br>'
                    f'{d["conteudo"][:150]}...</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Nenhum documento recuperado")
    else:
        st.caption("Aguardando primeira interação...")


# ─── Chat principal ───────────────────────────────────────────

# Exibe histórico de mensagens
for msg in st.session_state.mensagens:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ─── Input do usuário ─────────────────────────────────────────

if prompt := st.chat_input("Digite sua mensagem..."):
    # Adiciona mensagem do usuário
    st.session_state.mensagens.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # Invoca o grafo
    with st.chat_message("assistant"):
        with st.spinner("BluaCheck está pensando..."):
            estado_inicial = {
                "mensagens": [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.mensagens
                ],
                "paciente_id": paciente_id,
                "contexto_rag": [],
                "tools_log": [],
                "red_flag": False,
                "agente_atual": "",
                "resposta_final": "",
            }

            try:
                resultado = app_graph.invoke(estado_inicial)
                resposta = resultado["resposta_final"]
                st.session_state.ultimo_resultado = resultado
            except Exception as e:
                resposta = f"⚠️ Erro ao processar: {e}"
                st.session_state.ultimo_resultado = None

        st.markdown(resposta)

        # Banner de emergência no chat (se for red flag)
        if st.session_state.ultimo_resultado and st.session_state.ultimo_resultado.get("red_flag"):
            st.error("🚨 EMERGÊNCIA DETECTADA — Acione SAMU 192 imediatamente")

    # Salva a resposta no histórico
    st.session_state.mensagens.append({"role": "assistant", "content": resposta})

    # Recarrega a sidebar
    st.rerun()