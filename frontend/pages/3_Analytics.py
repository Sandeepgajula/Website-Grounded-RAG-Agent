import streamlit as st
import requests
import sys, os
import pandas as pd
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from utils import API_BASE_URL

st.markdown("""
<div style="margin-bottom: 1.5rem;">
    <h2 style="color: #1a2b4b; font-size: 1.8rem; font-weight: 700; margin: 0 0 0.25rem 0;">Token Analytics</h2>
    <p style="color: #718096; margin: 0; font-size: 0.95rem;">Observability dashboard for token consumption and API costs</p>
</div>
""", unsafe_allow_html=True)

# Fetch token entries
entries = []
try:
    r = requests.get(f"{API_BASE_URL}/websites/token-log/entries?limit=500", timeout=5)
    if r.status_code == 200:
        data = r.json()
        entries = data.get("entries", [])
except Exception:
    pass

if not entries:
    with st.container(border=True):
        st.markdown("""
        <div style="padding:2.5rem; text-align:center;">
            <div style="font-size:2.8rem; margin-bottom:0.8rem;"></div>
            <h3 style="color:#1a2b4b; margin-bottom:0.4rem;">No Queries Logged Yet</h3>
            <p style="color:#718096; max-width:450px; margin:0 auto; line-height:1.6; font-size:0.95rem;">
                Ask questions in the <b>Assistant</b> to begin tracking live token metrics and cost estimations.
            </p>
        </div>
        """, unsafe_allow_html=True)
else:
    df = pd.DataFrame(entries)

    total_queries = len(df)
    total_prompt_tok = int(df["input_tokens"].sum()) if "input_tokens" in df else 0
    total_comp_tok = int(df["output_tokens"].sum()) if "output_tokens" in df else 0
    total_tokens = total_prompt_tok + total_comp_tok
    total_cost = float(df["cost_usd"].sum()) if "cost_usd" in df else 0.0

    # Metric Cards in Light Aesthetic
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div style="background:white; padding:1.2rem; border-radius:12px; border:1px solid #edf2f7; box-shadow:0 2px 6px rgba(0,0,0,0.02);">
            <p style="margin:0; font-size:0.75rem; color:#718096; font-weight:600; text-transform:uppercase;">Total Queries</p>
            <h2 style="margin:4px 0 0; color:#1a2b4b; font-size:1.8rem; font-weight:700;">{total_queries:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    with m2:
        st.markdown(f"""
        <div style="background:white; padding:1.2rem; border-radius:12px; border:1px solid #edf2f7; box-shadow:0 2px 6px rgba(0,0,0,0.02);">
            <p style="margin:0; font-size:0.75rem; color:#718096; font-weight:600; text-transform:uppercase;">Prompt Tokens</p>
            <h2 style="margin:4px 0 0; color:#5E237F; font-size:1.8rem; font-weight:700;">{total_prompt_tok:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    with m3:
        st.markdown(f"""
        <div style="background:white; padding:1.2rem; border-radius:12px; border:1px solid #edf2f7; box-shadow:0 2px 6px rgba(0,0,0,0.02);">
            <p style="margin:0; font-size:0.75rem; color:#718096; font-weight:600; text-transform:uppercase;">Completion Tokens</p>
            <h2 style="margin:4px 0 0; color:#7b3fa0; font-size:1.8rem; font-weight:700;">{total_comp_tok:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    with m4:
        st.markdown(f"""
        <div style="background:white; padding:1.2rem; border-radius:12px; border:1px solid #edf2f7; box-shadow:0 2px 6px rgba(0,0,0,0.02);">
            <p style="margin:0; font-size:0.75rem; color:#718096; font-weight:600; text-transform:uppercase;">Estimated Spend</p>
            <h2 style="margin:4px 0 0; color:#48bb78; font-size:1.8rem; font-weight:700;">${total_cost:.5f}</h2>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # Charts
    with st.container(border=True):
        st.markdown("<h4 style='color:#1a2b4b; margin:0 0 1rem 0;'>Token Usage Timeline</h4>", unsafe_allow_html=True)
        chart_df = df.copy()
        if "timestamp" in chart_df.columns:
            chart_df["time"] = pd.to_datetime(chart_df["timestamp"]).dt.strftime("%H:%M:%S")
            st.line_chart(chart_df.set_index("time")[["input_tokens", "output_tokens"]])

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # Cost Simulator
    with st.container(border=True):
        st.markdown("<h4 style='color:#1a2b4b; margin:0 0 1rem 0;'>Interactive Cost Simulator</h4>", unsafe_allow_html=True)
        sim_col1, sim_col2 = st.columns(2)
        with sim_col1:
            custom_input_rate = st.number_input("Custom Input Cost per 1K Tokens ($)", value=0.00015, format="%.5f")
        with sim_col2:
            custom_output_rate = st.number_input("Custom Output Cost per 1K Tokens ($)", value=0.00060, format="%.5f")

        sim_total = (total_prompt_tok / 1000.0 * custom_input_rate) + (total_comp_tok / 1000.0 * custom_output_rate)
        st.markdown(f"""
        <p style="color:#2d3748; font-size:0.95rem; margin-top:10px;">
            Projected cost with these rates: <b style="color:#5E237F; font-size:1.15rem;">${sim_total:.4f}</b> for {total_tokens:,} total tokens processed.
        </p>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # Recent Queries Log Table
    with st.container(border=True):
        st.markdown("<h4 style='color:#1a2b4b; margin:0 0 1rem 0;'>Recent Activity Log</h4>", unsafe_allow_html=True)
        cols_to_show = [c for c in ["timestamp", "company_name", "query", "input_tokens", "output_tokens", "cost_usd", "latency_seconds"] if c in df.columns]
        st.dataframe(df[cols_to_show].sort_values(by="timestamp", ascending=False).head(25), use_container_width=True)
