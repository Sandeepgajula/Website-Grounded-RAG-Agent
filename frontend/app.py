import streamlit as st
import requests
import json
import sys
import os
from datetime import datetime

# Add root to sys.path so utils is importable
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from utils import local_css, show_sidebar, API_BASE_URL, get_websites

# ─────────────────────────────────────────────
# Page Config (must be first Streamlit call)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Website RAG Assistant",
    layout="wide",
)

local_css()

# ─────────────────────────────────────────────
# Assistant Page
# ─────────────────────────────────────────────
def assistant_page():
    selected_site = st.session_state.get("selected_site")
    if not selected_site:
        websites = get_websites()
        if websites:
            selected_site = websites[0]["company_name"]
            st.session_state.selected_site = selected_site
        else:
            st.warning("No knowledge bases found. Go to **Ingestion** to crawl a website first.")
            st.stop()

    # Session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Container for empty state greeting
    empty_state_container = st.empty()

    # ── Chat History ──
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    pending_prompt = None

    # ── Empty state (shown only when chat has no messages) ──
    if not st.session_state.messages:
        hour = datetime.now().hour
        if 5 <= hour < 12:
            time_greeting = "good morning!"
        elif 12 <= hour < 17:
            time_greeting = "good afternoon!"
        else:
            time_greeting = "good evening!"

        with empty_state_container.container():
            st.markdown(f"""
            <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; padding: 2.5rem 1rem 1.5rem; text-align:center;">
                <h2 style="color:#1a2b4b; font-size:2rem; font-weight:700; margin:0 0 0.25rem 0; letter-spacing:-0.02em;">
                    Hi there, {time_greeting}
                </h2>
                <h3 style="color:#4a5568; font-size:1.15rem; font-weight:500; margin:0 0 0.6rem 0;">
                    How can I help you today?
                </h3>
                <p style="color:#718096; max-width:440px; line-height:1.55; font-size:0.92rem; margin:0 auto 1.8rem auto;">
                    Ask me anything about the documentation, architecture, APIs, or key concepts.
                </p>
            </div>
            """, unsafe_allow_html=True)

            if selected_site:
                s_col1, s_col2 = st.columns(2)
                with s_col1:
                    if st.button("Summarize Website Overview", use_container_width=True):
                        pending_prompt = f"Can you give me a high-level summary and overview of {selected_site}?"
                    if st.button("Getting Started & Setup Guide", use_container_width=True):
                        pending_prompt = f"How do I get started with {selected_site}? What are the setup steps and prerequisites?"
                with s_col2:
                    if st.button("Architecture & Core Concepts", use_container_width=True):
                        pending_prompt = f"Explain the core architecture and main components documented in {selected_site}."
                    if st.button("Frequently Asked Questions", use_container_width=True):
                        pending_prompt = f"What are the most common use cases, questions, or patterns for {selected_site}?"

    # Chat input
    if not selected_site:
        st.stop()

    prompt = st.chat_input("Ask a question about the website…")
    if not prompt and pending_prompt:
        prompt = pending_prompt

    if prompt:
        # Immediately clear the empty state greeting so it never persists alongside messages
        empty_state_container.empty()

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""
            citations = []

            payload = {
                "company_name": selected_site,
                "query": prompt,
                "history": st.session_state.messages[:-1],
                "stream": True,
            }

            try:
                with requests.post(f"{API_BASE_URL}/rag", json=payload, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    for line in r.iter_lines(decode_unicode=True):
                        if not line:
                            continue
                        line = line.strip()
                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                            if not data_str:
                                continue
                            try:
                                event = json.loads(data_str)
                            except Exception:
                                continue

                            ev_type = event.get("type")
                            if ev_type == "chunk":
                                delta = event.get("content", "")
                                if delta:
                                    full_response += delta
                                    placeholder.markdown(full_response + "▌")
                            elif ev_type == "citations":
                                citations = event.get("citations", [])
                            elif ev_type == "done":
                                break

                # Clean and append citations if present and not already listed
                if citations:
                    seen = set()
                    clean_cits = []
                    for c in citations:
                        raw_u = c.get("url", "").strip()
                        if raw_u.startswith("[") and "](" in raw_u:
                            raw_u = raw_u.split("](")[1].rstrip(")")
                        raw_u = raw_u.strip().strip("<>").strip('"').strip("'")
                        title = (c.get("title") or raw_u).strip()
                        if raw_u and raw_u not in seen:
                            seen.add(raw_u)
                            clean_cits.append((title, raw_u))
                    
                    rejection_phrases = [
                        "does not contain information", 
                        "don't have enough information", 
                        "sources\nnone", 
                        "sources:\nnone",
                        "does not provide information"
                    ]
                    is_rejected = any(p in full_response.lower() for p in rejection_phrases)

                    if clean_cits and not is_rejected and "**Sources:**" not in full_response:
                        full_response += "\n\n**Sources:**\n" + "\n".join(f"- [{t}]({u})" for t, u in clean_cits)

                placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except requests.exceptions.ConnectionError:
                placeholder.error("Cannot reach backend. Is the server running on port 8009?")
            except Exception as e:
                placeholder.error(f"Error: {e}")

        if pending_prompt:
            st.rerun()


# ─────────────────────────────────────────────
# Navigation
# ─────────────────────────────────────────────
pages = [
    st.Page(assistant_page,               title="Assistant",  default=True),
    st.Page("pages/2_Ingestion.py",       title="Ingestion"),
    st.Page("pages/3_Analytics.py",       title="Analytics"),
]

pg = st.navigation(pages)

show_sidebar()
pg.run()