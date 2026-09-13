import streamlit as st
import requests
import time
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from utils import API_BASE_URL

st.markdown("""
<div style="margin-bottom: 1.5rem;">
    <h2 style="color: #1a2b4b; font-size: 1.8rem; font-weight: 700; margin: 0 0 0.25rem 0;">Data Ingestion</h2>
    <p style="color: #718096; margin: 0; font-size: 0.95rem;">Crawl any public website and build a searchable knowledge base</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CRAWL FORM
# ─────────────────────────────────────────────
with st.container(border=True):
    st.markdown("<h4 style='color:#1a2b4b; margin:0 0 0.35rem 0;'>Crawl & Index a Website</h4>", unsafe_allow_html=True)
    st.markdown("<p style='color:#718096; font-size:0.9rem; margin-bottom:1.25rem;'>Enter a public website URL. The crawler will discover internal pages, clean the content, and store it in a searchable vector database.</p>", unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        site_url = st.text_input("Website URL", placeholder="https://docs.python.org/3/")
        kb_name  = st.text_input("Knowledge Base Name", placeholder="e.g. python_docs")
    with col2:
        max_pages   = st.number_input("Max Pages", min_value=5, max_value=300, value=30, step=5)
        auto_ingest = st.checkbox("Auto-embed after crawl", value=True)

    if st.button("Start Crawl", type="primary", use_container_width=True):
        if not site_url or not kb_name:
            st.warning("Please provide both a URL and a knowledge base name.")
        else:
            try:
                with st.spinner("Starting crawler…"):
                    r = requests.post(
                        f"{API_BASE_URL}/crawl",
                        json={"url": site_url, "company_name": kb_name, "max_pages": int(max_pages)},
                        timeout=15,
                    )

                if r.status_code != 200:
                    st.error(f"Failed to start crawl: {r.text}")
                else:
                    task_id  = r.json().get("task_id")
                    prog_bar = st.progress(0)
                    status_box = st.empty()
                    st.info(f"Crawl job started (task `{task_id}`). Monitoring…")

                    for _ in range(200):
                        time.sleep(1.5)
                        try:
                            poll = requests.get(f"{API_BASE_URL}/crawl/status/{task_id}", timeout=5)
                            if poll.status_code != 200:
                                continue
                        except requests.exceptions.RequestException:
                            # Ignore temporary timeouts during polling
                            continue

                        s       = poll.json()
                        status  = s.get("status")
                        crawled = s.get("pages_crawled", 0)
                        prog_bar.progress(min(1.0, crawled / max_pages))
                        status_box.markdown(f"**{s.get('message', status)}** — {crawled} pages crawled")

                        if status == "done":
                            st.success(f"Crawl complete! Saved **{s.get('pages_saved')}** pages.")
                            if auto_ingest:
                                with st.spinner("Embedding into ChromaDB vector store…"):
                                    ir = requests.post(
                                        f"{API_BASE_URL}/ingest",
                                        json={"company_name": kb_name, "chunk_size": 1000, "chunk_overlap": 150},
                                        timeout=300,
                                    )
                                if ir.status_code == 200:
                                    res = ir.json()
                                    st.success(f"Embedded **{res.get('chunks_created')}** chunks from **{res.get('pages_ingested')}** pages into ChromaDB.")
                                    st.rerun()
                                else:
                                    st.error(f"Embedding error: {ir.text}")
                            break
                        elif status == "failed":
                            st.error(f"Crawl failed: {s.get('message')}")
                            break

            except requests.exceptions.ConnectionError:
                st.error("Cannot reach backend. Is the server running on port 8009?")
            except Exception as e:
                st.error(f"Error: {e}")

st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# EXISTING KNOWLEDGE BASES
# ─────────────────────────────────────────────
st.markdown("<h4 style='color:#1a2b4b; margin:0 0 0.8rem 0;'>Existing Knowledge Bases</h4>", unsafe_allow_html=True)

try:
    kb_resp = requests.get(f"{API_BASE_URL}/websites", timeout=5)
    kbs = kb_resp.json() if kb_resp.status_code == 200 else []
except Exception:
    kbs = []

if not kbs:
    with st.container(border=True):
        st.markdown("""
        <div style="padding:1.5rem; text-align:center; color:#718096;">
            No knowledge bases found. Crawl a website above to get started.
        </div>
        """, unsafe_allow_html=True)
else:
    for kb in kbs:
        name  = kb.get("company_name", "unknown")
        count = kb.get("chunk_count", 0)
        with st.container(border=True):
            col_a, col_b, col_c = st.columns([4, 2, 1])
            with col_a:
                st.markdown(f"""
                <div style="padding:0.4rem 0;">
                    <span style="font-weight:700; color:#1a2b4b; font-size:1.05rem;">{name}</span>
                </div>
                """, unsafe_allow_html=True)
            with col_b:
                st.markdown(f"""
                <div style="padding:0.2rem 0; text-align:center;">
                    <span style="font-size:0.75rem; color:#718096; text-transform:uppercase; font-weight:600; display:block;">Chunks</span>
                    <span style="font-size:1.2rem; font-weight:700; color:#5E237F;">{count:,}</span>
                </div>
                """, unsafe_allow_html=True)
            with col_c:
                if st.button("Delete", key=f"del_{name}", use_container_width=True):
                    try:
                        dr = requests.delete(f"{API_BASE_URL}/ingest/{name}", timeout=10)
                        if dr.status_code == 200:
                            st.success(f"Deleted '{name}' from vector store.")
                            st.rerun()
                        else:
                            st.error(f"Delete failed: {dr.text}")
                    except Exception as e:
                        st.error(f"Error: {e}")
