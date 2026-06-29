# DocuChat dark theme — ChatGPT / Gemini inspired.

DOCUCHAT_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --dc-bg: #0F172A;
        --dc-sidebar: #111827;
        --dc-card: #1E293B;
        --dc-accent: #10A37F;
        --dc-accent-hover: #0d8c6d;
        --dc-text: #F8FAFC;
        --dc-muted: #94A3B8;
        --dc-border: #334155;
    }

    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif !important;
        background-color: var(--dc-bg) !important;
        color: var(--dc-text) !important;
    }

    #MainMenu, footer, header[data-testid="stHeader"] {
        visibility: hidden;
        height: 0;
        min-height: 0;
    }

    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] {
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
    }

    section[data-testid="stSidebar"] {
        width: 280px !important;
        min-width: 280px !important;
        max-width: 280px !important;
        transform: none !important;
        margin-left: 0 !important;
        background-color: var(--dc-sidebar) !important;
        border-right: 1px solid var(--dc-border) !important;
    }

    section[data-testid="stSidebar"] > div {
        background-color: var(--dc-sidebar) !important;
        padding-top: 1rem !important;
    }

    div[data-testid="stAppViewContainer"] > section.main {
        background-color: var(--dc-bg) !important;
    }

    div[data-testid="stAppViewContainer"] > section.main > div.block-container {
        max-width: 52rem !important;
        padding-top: 1rem !important;
        padding-bottom: 8rem !important;
        margin: 0 auto !important;
    }

    .dc-logo {
        font-size: 1.35rem;
        font-weight: 700;
        color: var(--dc-text);
        letter-spacing: -0.02em;
        margin-bottom: 0.25rem;
    }
    .dc-logo span { color: var(--dc-accent); }

    .dc-sidebar-label {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--dc-muted);
        margin: 1rem 0 0.5rem 0;
    }

    .dc-doc-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background: var(--dc-card);
        border: 1px solid var(--dc-border);
        border-radius: 999px;
        padding: 0.25rem 0.75rem;
        font-size: 0.78rem;
        color: var(--dc-text);
        margin: 0.15rem 0.25rem 0.15rem 0;
    }

    .dc-empty-wrap {
        text-align: center;
        padding: 3rem 1rem 2rem;
        animation: dcFadeIn 0.4s ease;
    }
    .dc-empty-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        opacity: 0.9;
    }
    .dc-empty-title {
        font-size: 1.75rem;
        font-weight: 600;
        color: var(--dc-text);
        margin-bottom: 0.5rem;
    }
    .dc-empty-sub {
        color: var(--dc-muted);
        font-size: 1rem;
        margin-bottom: 2rem;
        max-width: 28rem;
        margin-left: auto;
        margin-right: auto;
    }

    div[data-testid="stHorizontalBlock"] .dc-prompt-btn {
        position: relative;
        padding-top: 0.35rem;
    }
    .dc-prompt-format {
        display: block;
        font-size: 0.65rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--dc-accent);
        margin-bottom: 0.35rem;
        padding-left: 0.15rem;
    }
    div[data-testid="stHorizontalBlock"] .dc-prompt-btn button,
    div[data-testid="stHorizontalBlock"] .dc-chip-btn button {
        background: var(--dc-card) !important;
        border: 1px solid var(--dc-border) !important;
        color: var(--dc-text) !important;
        border-radius: 12px !important;
        padding: 0.85rem 1rem !important;
        font-size: 0.875rem !important;
        text-align: left !important;
        transition: all 0.15s ease !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2) !important;
    }
    div[data-testid="stHorizontalBlock"] .dc-prompt-btn button:hover,
    div[data-testid="stHorizontalBlock"] .dc-chip-btn button:hover {
        border-color: var(--dc-accent) !important;
        background: #243044 !important;
    }

    [data-testid="stChatMessage"] {
        background: transparent !important;
        padding: 0.5rem 0 !important;
        animation: dcFadeIn 0.25s ease;
    }
    [data-testid="stChatMessage"]:has([data-testid="chat-avatar-user"]) {
        background: transparent !important;
    }

    .dc-input-dock {
        position: fixed;
        bottom: 0;
        left: 280px;
        right: 0;
        z-index: 999;
        background: linear-gradient(transparent, var(--dc-bg) 24%);
        padding: 0 1.5rem 1.25rem;
        pointer-events: none;
    }
    .dc-input-dock > div {
        max-width: 52rem;
        margin: 0 auto;
        pointer-events: auto;
    }
    .dc-input-shell,
    div[data-testid="stAppViewContainer"] > section.main form[data-testid="stForm"] {
        background: var(--dc-card);
        border: 1px solid var(--dc-border);
        border-radius: 16px;
        padding: 0.5rem 0.75rem;
        box-shadow: 0 4px 24px rgba(0,0,0,0.35);
    }
    .dc-input-shell textarea,
    .dc-input-shell input,
    div[data-testid="stAppViewContainer"] > section.main form[data-testid="stForm"] input {
        background: transparent !important;
        color: var(--dc-text) !important;
        border: none !important;
        font-size: 0.95rem !important;
    }
    .dc-input-shell [data-testid="stSelectbox"] > div > div,
    div[data-testid="stAppViewContainer"] > section.main form[data-testid="stForm"] [data-testid="stSelectbox"] > div > div {
        background: var(--dc-bg) !important;
        border-color: var(--dc-border) !important;
        color: var(--dc-text) !important;
        min-height: 2.5rem !important;
        border-radius: 10px !important;
    }

    /* Hide empty markdown wrappers left from legacy HTML injections */
    div[data-testid="stAppViewContainer"] > section.main
        [data-testid="stMarkdownContainer"]:empty {
        display: none !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    div[data-testid="stSidebar"] button[kind="primary"],
    div[data-testid="stSidebar"] .stButton > button {
        border-radius: 10px !important;
        font-weight: 500 !important;
    }
    div[data-testid="stSidebar"] button[kind="primary"] {
        background: var(--dc-accent) !important;
        border-color: var(--dc-accent) !important;
    }
    div[data-testid="stSidebar"] button[kind="primary"]:hover {
        background: var(--dc-accent-hover) !important;
    }

    .dc-chat-item button {
        background: transparent !important;
        border: none !important;
        color: var(--dc-muted) !important;
        text-align: left !important;
        font-size: 0.85rem !important;
        padding: 0.45rem 0.65rem !important;
        border-radius: 8px !important;
        width: 100% !important;
    }
    .dc-chat-item button:hover {
        background: var(--dc-card) !important;
        color: var(--dc-text) !important;
    }
    .dc-chat-item-active button {
        background: var(--dc-card) !important;
        color: var(--dc-text) !important;
    }

    @keyframes dcFadeIn {
        from { opacity: 0; transform: translateY(6px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @media (max-width: 768px) {
        section[data-testid="stSidebar"] {
            width: 100% !important;
            min-width: 100% !important;
        }
    }
</style>
"""


def inject_theme() -> None:
    import streamlit as st

    st.markdown(DOCUCHAT_CSS, unsafe_allow_html=True)
