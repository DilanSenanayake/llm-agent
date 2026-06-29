# Viewport layout — single-screen shell (colors stay in theme.py).

LAYOUT_CSS = """
<style>
    /* ── Lock page to one viewport ── */
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > section.main {
        height: 100vh;
        overflow: hidden;
    }

    section[data-testid="stSidebar"] {
        height: 100vh;
        overflow-y: auto;
    }

    section[data-testid="stSidebar"] > div {
        padding-top: 0.75rem !important;
        padding-bottom: 0.5rem !important;
    }

    section[data-testid="stSidebar"] .dc-sidebar-label {
        margin: 0.65rem 0 0.35rem 0 !important;
    }

    section[data-testid="stSidebar"] [data-testid="stFileUploader"] section {
        padding: 0.5rem !important;
        min-height: 3rem !important;
    }

    section[data-testid="stSidebar"] [data-testid="stFileUploader"] small,
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stCaptionContainer"],
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
        font-size: 0 !important;
        line-height: 0 !important;
    }

    /* ── Main flex column ── */
    div[data-testid="stAppViewContainer"] > section.main > div.block-container {
        height: 100vh;
        max-height: 100vh;
        overflow: hidden;
        padding: 0.5rem 1.25rem 0.65rem !important;
        margin: 0 auto !important;
        max-width: 44rem !important;
        display: flex;
        flex-direction: column;
    }

    div[data-testid="stAppViewContainer"] > section.main > div.block-container > div {
        flex: 1;
        min-height: 0;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        gap: 0;
    }

    /* Scrollable content block (chat history or home) */
    div[data-testid="stAppViewContainer"] > section.main div.block-container
        > div > [data-testid="stVerticalBlock"]:has([data-testid="stChatMessage"]),
    div[data-testid="stAppViewContainer"] > section.main div.block-container
        > div > [data-testid="stVerticalBlock"]:has(.dc-home-card),
    div[data-testid="stAppViewContainer"] > section.main div.block-container
        > div > [data-testid="stVerticalBlock"]:has(.dc-chip-btn) {
        flex: 1;
        min-height: 0;
        overflow-y: auto;
        overflow-x: hidden;
    }

    /* Input bar stays at bottom of the column */
    div[data-testid="stAppViewContainer"] > section.main form[data-testid="stForm"] {
        flex-shrink: 0;
        margin-top: auto !important;
    }

    div[data-testid="stAppViewContainer"] > section.main form[data-testid="stForm"] [data-testid="stHorizontalBlock"] {
        gap: 0.5rem;
        align-items: end;
    }

    /* ── Home ── */
    .dc-home-card {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 1.5rem 0.5rem 0.5rem;
    }

    .dc-home-icon {
        font-size: 2rem;
        line-height: 1;
        margin-bottom: 0.25rem;
    }

    .dc-home-title {
        font-size: 1.35rem;
        font-weight: 600;
        color: var(--dc-text);
        letter-spacing: -0.02em;
    }

    .dc-home-sub {
        font-size: 0.8rem;
        color: var(--dc-muted);
        max-width: 22rem;
        line-height: 1.45;
        margin-top: 0.25rem;
    }

    .dc-prompts-label {
        font-size: 0.62rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: var(--dc-muted);
        margin: 1rem 0 0;
    }

    div[data-testid="stHorizontalBlock"] .dc-chip-btn button {
        padding: 0.35rem 0.5rem !important;
        font-size: 0.7rem !important;
        line-height: 1.2 !important;
        min-height: 2.1rem !important;
        border-radius: 8px !important;
    }

    .dc-chip-format {
        display: block;
        font-size: 0.55rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--dc-accent);
        margin-bottom: 0.15rem;
    }

    /* ── Chat ── */
    [data-testid="stChatMessage"] {
        padding: 0.2rem 0 !important;
    }

    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p {
        font-size: 0.9rem;
        line-height: 1.5;
    }

    [data-testid="stAlert"] {
        margin-bottom: 0.35rem !important;
        padding: 0.4rem 0.65rem !important;
        font-size: 0.8rem !important;
    }

    /* ── Response loading animation ── */
    .dc-loader {
        display: inline-flex;
        align-items: center;
        gap: 0.6rem;
        padding: 0.35rem 0;
        color: var(--dc-muted);
        font-size: 0.85rem;
    }

    .dc-loader-dots {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
    }

    .dc-loader-dots span {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--dc-accent);
        animation: dcLoaderBounce 1.2s infinite ease-in-out both;
    }

    .dc-loader-dots span:nth-child(1) { animation-delay: 0s; }
    .dc-loader-dots span:nth-child(2) { animation-delay: 0.15s; }
    .dc-loader-dots span:nth-child(3) { animation-delay: 0.3s; }

    @keyframes dcLoaderBounce {
        0%, 80%, 100% {
            transform: translateY(0) scale(0.75);
            opacity: 0.4;
        }
        40% {
            transform: translateY(-5px) scale(1);
            opacity: 1;
        }
    }

    [data-testid="stChatMessage"]:has(.dc-loader) {
        animation: dcFadeIn 0.2s ease;
    }

    @media (max-width: 768px) {
        div[data-testid="stAppViewContainer"] > section.main > div.block-container {
            padding: 0.35rem 0.75rem 0.5rem !important;
            max-width: 100% !important;
        }
        .dc-home-title { font-size: 1.15rem; }
    }
</style>
"""


def inject_layout() -> None:
    import streamlit as st

    st.markdown(LAYOUT_CSS, unsafe_allow_html=True)
