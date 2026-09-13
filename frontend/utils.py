import streamlit as st
import requests
import os
import base64

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8009")

def local_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

    :root {
        --primary: #5E237F;
        --primary-light: #7b3fa0;
        --secondary: #1a2b4b;
        --bg-light: #f8faff;
        --text-main: #2d3748;
        --text-muted: #718096;
        --white: #ffffff;
        --border: #edf2f7;
        --shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }

    /* Global Body styling */
    .stApp {
        background-color: var(--bg-light) !important;
        font-family: 'Outfit', sans-serif !important;
        color: var(--text-main) !important;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: var(--white) !important;
        border-right: 1px solid var(--border) !important;
        box-shadow: 2px 0 10px rgba(0, 0, 0, 0.02) !important;
    }

    /* Navigation item styling */
    [data-testid="stSidebarNav"] {
        padding-top: 2rem !important;
    }

    [data-testid="stSidebarNav"] li a {
        color: var(--text-muted) !important;
        border-radius: 8px !important;
    }

    [data-testid="stSidebarNav"] li a:hover,
    [data-testid="stSidebarNav"] li a[aria-current="page"] {
        background: rgba(94, 35, 127, 0.08) !important;
        color: var(--primary) !important;
        font-weight: 600 !important;
    }

    /* Glassmorphism Card for Headers */
    .custom-header {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(10px);
        padding: 2rem;
        border-radius: 16px;
        border: 1px solid var(--border);
        box-shadow: var(--shadow);
        margin-bottom: 2rem;
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }

    .header-icon {
        font-size: 2.5rem;
        background: linear-gradient(135deg, var(--primary), var(--primary-light));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .header-text h1 {
        margin: 0 !important;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: var(--secondary) !important;
    }

    .header-text p {
        margin: 0 !important;
        color: var(--text-muted) !important;
        font-size: 1rem !important;
    }

    /* Chat Styling */
    .stChatMessage {
        background-color: var(--white) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        box-shadow: var(--shadow) !important;
        margin-bottom: 1rem !important;
        padding: 1.2rem !important;
    }

    .stChatMessage[data-testid*="user"] {
        border-left: 4px solid var(--primary) !important;
    }

    .stChatMessage[data-testid*="assistant"] {
        border-left: 4px solid var(--primary-light) !important;
    }

    /* Button Styling */
    .stButton > button,
    button[data-testid="stBaseButton-secondary"],
    button[data-testid="baseButton-secondary"] {
        background: #ffffff !important;
        color: #1a2b4b !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        padding: 0.75rem 1rem !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04) !important;
        transition: all 0.18s ease !important;
    }

    .stButton > button p,
    button[data-testid="stBaseButton-secondary"] p {
        color: #1a2b4b !important;
        font-weight: 500 !important;
    }

    .stButton > button:hover,
    button[data-testid="stBaseButton-secondary"]:hover {
        border-color: var(--primary) !important;
        color: var(--primary) !important;
        background: #faf5ff !important;
        box-shadow: 0 4px 12px rgba(94, 35, 127, 0.1) !important;
        transform: translateY(-1px) !important;
    }

    .stButton > button:hover p,
    button[data-testid="stBaseButton-secondary"]:hover p {
        color: var(--primary) !important;
    }

    /* Primary buttons (e.g. Start Crawl) keep vibrant gradient */
    .stButton > button[kind="primary"],
    button[data-testid="stBaseButton-primary"],
    button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, var(--primary), var(--primary-light)) !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(94, 35, 127, 0.2) !important;
    }
    .stButton > button[kind="primary"] p,
    button[data-testid="stBaseButton-primary"] p {
        color: white !important;
        font-weight: 600 !important;
    }
    .stButton > button[kind="primary"]:hover,
    button[data-testid="stBaseButton-primary"]:hover {
        color: white !important;
        background: linear-gradient(135deg, var(--primary-light), var(--primary)) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 16px rgba(94, 35, 127, 0.3) !important;
    }

    /* Input Styling */
    .stChatInputContainer {
        border-top: 1px solid var(--border) !important;
        padding-top: 1rem !important;
        padding-bottom: 0.5rem !important;
    }

    /* Cards & Containers */
    .white-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #edf2f7;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
    }

    /* System Status Card in Sidebar */
    .status-card {
        padding: 1rem;
        background: #fdfbff;
        border: 1px solid #e9e4f0;
        border-radius: 12px;
        margin-top: 1rem;
    }

    .status-dot {
        height: 10px;
        width: 10px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
    }

    .dot-online { background-color: #48bb78; box-shadow: 0 0 8px #48bb78; }
    .dot-offline { background-color: #f56565; box-shadow: 0 0 8px #f56565; }

    /* Hide Streamlit default side menu branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Center chat container nicely like ChatGPT */
    .stMainBlockContainer {
        max-width: 900px !important;
        width: 100% !important;
        margin: 0 auto !important;
        padding-top: 2rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* Suggestion card styling */
    .suggestion-btn {
        background: white !important;
        border: 1px solid #edf2f7 !important;
        border-radius: 12px !important;
        padding: 0.8rem 1rem !important;
        text-align: left !important;
        color: #2d3748 !important;
        font-size: 0.88rem !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
    }
    .suggestion-btn:hover {
        border-color: #5E237F !important;
        box-shadow: 0 4px 12px rgba(94, 35, 127, 0.08) !important;
    }
    </style>
    """, unsafe_allow_html=True)


def get_api_info():
    try:
        r = requests.get(f"{API_BASE_URL}/info", timeout=3)
        if r.status_code == 200:
            return r.json()
    except:
        return None


def show_sidebar():
    with st.sidebar:
        st.markdown("<h2 style='color:#5E237F; text-align:center; font-weight:800; letter-spacing:-0.02em;'>WEB RAG</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#718096; margin-top:-10px; font-size:0.9rem;'>Website Knowledge Assistant</p>", unsafe_allow_html=True)

        st.divider()

        # Knowledge Base Selector in Sidebar
        websites = get_websites()
        website_options = [w["company_name"] for w in websites] if websites else []
        if website_options:
            st.markdown("<p style='font-size:0.75rem; color:#718096; font-weight:600; text-transform:uppercase; letter-spacing:0.05em; margin:0.5rem 0 0.35rem;'>Active Knowledge Base</p>", unsafe_allow_html=True)
            if "selected_site" not in st.session_state or st.session_state.selected_site not in website_options:
                st.session_state.selected_site = website_options[0]

            curr_idx = website_options.index(st.session_state.selected_site) if st.session_state.selected_site in website_options else 0
            chosen = st.selectbox(
                "Active Knowledge Base",
                website_options,
                index=curr_idx,
                key="sidebar_kb_selector",
                label_visibility="collapsed",
            )
            st.session_state.selected_site = chosen
        else:
            st.session_state.selected_site = None

        # System status
        info = get_api_info()
        if info:
            total_objects = info.get('total_objects', 0)
            st.markdown(f"""
            <div class="status-card">
                <p style="margin:0; font-size:0.75rem; color:#718096; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;">System Status</p>
                <div style="margin:8px 0; font-weight:700; color:#2d3748; display:flex; align-items:center;">
                    <span class="status-dot dot-online"></span> ONLINE
                </div>
                <div style="border-top:1px solid #edf2f7; padding-top:8px; margin-top:8px;">
                    <p style="margin:0; font-size:0.65rem; color:#718096;">TOTAL CHUNKS</p>
                    <p style="margin:0; font-size:1.1rem; font-weight:700; color:#5E237F;">{total_objects:,}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="status-card">
                <span class="status-dot dot-offline"></span> OFFLINE
                <p style="font-size:0.7rem; color:#f56565; margin-top:5px;">API at port 8009 unreachable</p>
            </div>
            """, unsafe_allow_html=True)

        # Clear chat
        if "messages" in st.session_state and st.session_state.messages:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Clear Chat", use_container_width=True):
                st.session_state.messages = []
                st.rerun()


def show_footer():
    """Footer removed per user request."""
    pass


def custom_header(title, subtitle, icon="🤖"):
    st.markdown(f"""
    <div class="custom-header">
        <div class="header-icon">{icon}</div>
        <div class="header-text">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def api_get(endpoint: str, timeout: int = 10) -> dict | None:
    try:
        r = requests.get(f"{API_BASE_URL}{endpoint}", timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def api_post(endpoint: str, payload: dict, timeout: int = 30) -> dict | None:
    try:
        r = requests.post(f"{API_BASE_URL}{endpoint}", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def api_delete(endpoint: str, timeout: int = 10) -> dict | None:
    try:
        r = requests.delete(f"{API_BASE_URL}{endpoint}", timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def get_websites() -> list:
    """Fetch list of ingested websites."""
    data = api_get("/websites")
    return data if isinstance(data, list) else []