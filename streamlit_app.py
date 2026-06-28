import base64
import os
import sys
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
INDEX_PATH = ROOT_DIR / "index" / "faiss.index"
CHUNKS_PATH = ROOT_DIR / "index" / "chunks.json"
ENV_PATH = ROOT_DIR / ".env"
HERO_IMAGE_PATH = ROOT_DIR / "assets" / "aurelia-hero.png"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from history_store import (  # noqa: E402
    add_handoff_customer_message,
    add_turn,
    create_conversation,
    delete_conversation,
    get_conversation,
    get_recent_turns,
    init_db,
    list_conversations,
    rename_conversation,
)
from model_config import (  # noqa: E402
    DEFAULT_DASHSCOPE_CHAT_MODEL,
    DEFAULT_DASHSCOPE_EMBEDDING_MODEL,
    configured_model_name,
    is_configured,
)
from reliable_answer import generate_reliable_answer  # noqa: E402


@st.cache_data(show_spinner=False)
def get_asset_data_uri(asset_path: str) -> str:
    """Return a browser-ready data URI for a local image asset."""
    path = Path(asset_path)
    if not path.exists():
        return ""

    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def apply_theme() -> None:
    """Apply the Aurelia Airways premium concierge visual system."""
    hero_image_uri = get_asset_data_uri(str(HERO_IMAGE_PATH))
    hero_image_layer = (
        f"url('{hero_image_uri}')"
        if hero_image_uri
        else "linear-gradient(135deg, #071629 0%, #153a5f 100%)"
    )

    css = """
        <style>
        :root {
            --aurelia-ink: #0b1628;
            --aurelia-ink-soft: #26384f;
            --aurelia-muted: #66758a;
            --aurelia-navy: #071629;
            --aurelia-navy-2: #0f2946;
            --aurelia-blue: #2e78a8;
            --aurelia-sky: #8cc4df;
            --aurelia-gold: #d4a762;
            --aurelia-gold-deep: #a8792f;
            --aurelia-ivory: #fbf7ee;
            --aurelia-cream: #f4ecdc;
            --aurelia-panel: rgba(255, 255, 255, 0.94);
            --aurelia-panel-solid: #ffffff;
            --aurelia-line: rgba(16, 41, 70, 0.14);
            --aurelia-line-strong: rgba(16, 41, 70, 0.24);
            --aurelia-success: #0f6b5e;
            --aurelia-warn: #94621d;
            --aurelia-danger: #a74444;
            --aurelia-radius: 8px;
            --aurelia-shadow: 0 24px 70px rgba(7, 22, 41, 0.12);
            --aurelia-shadow-soft: 0 12px 36px rgba(7, 22, 41, 0.08);
        }

        .stApp {
            background:
                linear-gradient(180deg, rgba(251, 247, 238, 0.98) 0, rgba(244, 236, 220, 0.76) 19rem, #f8fafc 100%),
                radial-gradient(circle at 82% 10%, rgba(212, 167, 98, 0.18), transparent 24rem),
                radial-gradient(circle at 8% 4%, rgba(140, 196, 223, 0.24), transparent 23rem);
            color: var(--aurelia-ink);
        }

        .stApp, .stApp p, .stApp span, .stApp div, .stApp label {
            color: var(--aurelia-ink);
            letter-spacing: 0;
        }

        header[data-testid="stHeader"] {
            background: transparent;
            height: 3.25rem;
            pointer-events: none;
        }

        header[data-testid="stHeader"] button,
        button[data-testid="stExpandSidebarButton"] {
            pointer-events: auto;
        }

        button[data-testid="stExpandSidebarButton"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            position: fixed;
            top: 0.65rem;
            left: 0.65rem;
            z-index: 1000000;
            width: 2.5rem;
            height: 2.5rem;
            min-height: 2.5rem;
            padding: 0;
            border: 1px solid var(--aurelia-line-strong);
            border-radius: var(--aurelia-radius);
            background: rgba(255, 255, 255, 0.96);
            color: var(--aurelia-ink);
            box-shadow: 0 8px 24px rgba(7, 22, 41, 0.12);
        }

        div[data-testid="stToolbar"],
        div[data-testid="stDecoration"],
        div[data-testid="stStatusWidget"] {
            visibility: hidden;
            height: 0;
        }

        .block-container {
            padding-top: 0.85rem;
            padding-bottom: 8.5rem;
            max-width: 1480px;
        }

        section[data-testid="stSidebar"] {
            background: var(--aurelia-ivory);
            border-right: 1px solid rgba(16, 41, 70, 0.18);
            box-shadow: 14px 0 36px rgba(7, 22, 41, 0.06);
        }

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: var(--aurelia-ink);
            letter-spacing: 0;
        }

        section[data-testid="stSidebar"] > div:first-child {
            padding-top: 1rem;
        }

        section[data-testid="stSidebar"] hr {
            border-color: rgba(16, 41, 70, 0.14);
            margin: 1rem 0;
        }

        .stButton > button {
            border-radius: var(--aurelia-radius);
            border: 1px solid var(--aurelia-line);
            min-height: 2.72rem;
            white-space: normal;
            text-align: left;
            color: var(--aurelia-ink);
            box-shadow: 0 4px 14px rgba(7, 22, 41, 0.04);
            transition: border-color 160ms ease, background-color 160ms ease, transform 160ms ease, box-shadow 160ms ease;
        }

        .stButton > button:hover {
            border-color: rgba(212, 167, 98, 0.72);
            transform: translateY(-1px);
            box-shadow: 0 10px 24px rgba(7, 22, 41, 0.08);
        }

        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, var(--aurelia-gold), var(--aurelia-gold-deep)) !important;
            border-color: rgba(212, 167, 98, 0.78) !important;
            color: #ffffff !important;
            font-weight: 760;
        }

        .stButton > button[kind="primary"] p,
        .stButton > button[kind="primary"] span,
        .stButton > button[kind="primary"] div {
            color: #ffffff !important;
            opacity: 1;
        }

        section[data-testid="stSidebar"] .stButton > button {
            font-weight: 720;
            line-height: 1.35;
        }

        section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #d8b06f, #a8792f) !important;
            border-color: rgba(255, 255, 255, 0.28) !important;
            color: #ffffff !important;
            justify-content: center;
            text-align: center;
        }

        section[data-testid="stSidebar"] .stButton > button[kind="primary"] * {
            color: #ffffff !important;
            opacity: 1 !important;
        }

        section[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
            background: rgba(255, 255, 255, 0.92) !important;
            border-color: rgba(16, 41, 70, 0.12) !important;
            color: var(--aurelia-ink) !important;
        }

        section[data-testid="stSidebar"] .stButton > button[kind="secondary"] * {
            color: var(--aurelia-ink) !important;
            opacity: 1 !important;
        }

        section[data-testid="stSidebar"] .stButton > button[kind="tertiary"] {
            width: 2.5rem !important;
            min-width: 2.5rem !important;
            max-width: 2.5rem !important;
            height: 2.5rem !important;
            min-height: 2.5rem !important;
            padding: 0 !important;
            justify-content: center;
            gap: 0 !important;
            background: rgba(255, 255, 255, 0.92);
            border-color: rgba(16, 41, 70, 0.12);
            box-shadow: 0 4px 14px rgba(7, 22, 41, 0.04);
            overflow: hidden;
        }

        section[data-testid="stSidebar"] .stButton:has(> button[kind="tertiary"]) {
            display: flex;
            justify-content: flex-end;
        }

        section[data-testid="stSidebar"] .stButton > button[kind="tertiary"] span {
            margin: 0 !important;
            font-size: 1.2rem !important;
            line-height: 1 !important;
        }

        div[data-testid="stDialog"] .stButton > button[kind="primary"] {
            background: var(--aurelia-danger) !important;
            border-color: var(--aurelia-danger) !important;
            color: #ffffff !important;
        }

        div[data-testid="stChatMessage"] {
            background: rgba(255, 255, 255, 0.96);
            border: 1px solid var(--aurelia-line);
            border-radius: var(--aurelia-radius);
            padding: 0.46rem 0.86rem;
            color: var(--aurelia-ink);
            box-shadow: var(--aurelia-shadow-soft);
            margin-bottom: 0.65rem;
        }

        div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
            border-left: 3px solid var(--aurelia-sky);
        }

        div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
            border-left: 3px solid var(--aurelia-gold);
        }

        div[data-testid="stChatMessage"] p,
        div[data-testid="stChatMessage"] li,
        div[data-testid="stChatMessage"] span,
        div[data-testid="stChatMessage"] div {
            color: var(--aurelia-ink);
            opacity: 1;
        }

        .human-support-badge {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.38rem;
            width: fit-content;
            margin: 0.3rem auto 0.75rem;
            padding: 0.28rem 0.58rem;
            border: 1px solid rgba(15, 107, 94, 0.24);
            border-radius: 999px;
            background: rgba(15, 107, 94, 0.09);
            color: var(--aurelia-success) !important;
            font-size: 0.78rem;
            font-weight: 720;
            line-height: 1.2;
        }

        .human-support-badge svg {
            width: 0.92rem;
            height: 0.92rem;
            flex: 0 0 auto;
            color: var(--aurelia-success);
        }

        .human-support-badge span {
            color: var(--aurelia-success) !important;
        }

        .human-support-badge.disconnected {
            border-color: rgba(102, 117, 138, 0.28);
            background: rgba(102, 117, 138, 0.09);
            color: var(--aurelia-muted) !important;
        }

        .human-support-badge.disconnected svg,
        .human-support-badge.disconnected span {
            color: var(--aurelia-muted) !important;
        }

        div[data-testid="stChatMessage"]:has(.customer-service-message-marker) {
            background: linear-gradient(135deg, rgba(232, 247, 243, 0.98), rgba(242, 250, 248, 0.98));
            border-color: rgba(15, 107, 94, 0.28);
            border-left: 3px solid var(--aurelia-success);
        }

        div[data-testid="stChatMessage"]:has(.customer-service-message-marker) [data-testid="stChatMessageAvatarAssistant"] {
            background: var(--aurelia-success);
            color: #ffffff;
        }

        .customer-service-message-marker {
            margin-bottom: 0.3rem;
            color: var(--aurelia-success) !important;
            font-size: 0.76rem;
            font-weight: 760;
        }

        div[data-testid="stExpander"] {
            border: 1px solid var(--aurelia-line);
            border-radius: var(--aurelia-radius);
            background: rgba(255, 255, 255, 0.94);
            color: var(--aurelia-ink);
            box-shadow: 0 10px 28px rgba(7, 22, 41, 0.05);
            overflow: hidden;
        }

        div[data-testid="stExpander"] p,
        div[data-testid="stExpander"] span,
        div[data-testid="stExpander"] div {
            color: var(--aurelia-ink);
            opacity: 1;
        }

        div[data-testid="stMarkdownContainer"] p,
        div[data-testid="stMarkdownContainer"] li {
            color: var(--aurelia-ink);
            opacity: 1;
        }

        textarea, input,
        div[data-testid="stChatInput"] textarea {
            color: var(--aurelia-ink) !important;
            caret-color: var(--aurelia-blue) !important;
        }

        textarea::placeholder, input::placeholder,
        div[data-testid="stChatInput"] textarea::placeholder {
            color: #778395 !important;
            opacity: 1;
        }

        div[data-testid="stChatInput"] {
            max-width: 920px;
            margin: 0 auto;
        }

        div[data-testid="stChatInput"] > div {
            background: #ffffff !important;
            border: 1px solid var(--aurelia-line-strong) !important;
            border-radius: var(--aurelia-radius) !important;
            box-shadow: 0 10px 34px rgba(7, 22, 41, 0.14);
        }

        div[data-testid="stChatInput"] textarea {
            background: transparent !important;
            min-height: 3.2rem !important;
        }

        div[data-testid="stBottomBlockContainer"] {
            padding: 0.85rem 1rem 1.05rem;
            background: linear-gradient(
                180deg,
                rgba(248, 250, 252, 0) 0%,
                rgba(248, 250, 252, 0.94) 32%,
                #f8fafc 100%
            );
            backdrop-filter: blur(10px);
        }

        div[data-testid="stForm"] {
            background:
                linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 252, 246, 0.95));
            border: 1px solid var(--aurelia-line);
            border-radius: var(--aurelia-radius);
            padding: 0.95rem;
            margin-bottom: 1.15rem;
            box-shadow: var(--aurelia-shadow-soft);
        }

        div[data-testid="stForm"] input {
            min-height: 2.95rem;
            background: #ffffff !important;
            border: 1px solid rgba(16, 41, 70, 0.22) !important;
            border-radius: var(--aurelia-radius) !important;
            box-shadow: inset 0 1px 2px rgba(7, 22, 41, 0.04);
        }

        div[data-testid="stFormSubmitButton"] button {
            background: linear-gradient(135deg, #0f2946, #2e78a8) !important;
            border: 1px solid rgba(46, 120, 168, 0.72) !important;
            color: #ffffff !important;
            font-weight: 760;
            min-height: 2.72rem;
            justify-content: center;
        }

        div[data-testid="stFormSubmitButton"] button * {
            color: #ffffff !important;
            opacity: 1 !important;
        }

        .app-header {
            position: relative;
            overflow: hidden;
            background-image:
                linear-gradient(90deg, rgba(7, 22, 41, 0.94) 0%, rgba(7, 22, 41, 0.83) 42%, rgba(7, 22, 41, 0.34) 70%, rgba(7, 22, 41, 0.16) 100%),
                linear-gradient(180deg, rgba(7, 22, 41, 0.05), rgba(7, 22, 41, 0.38)),
                __HERO_IMAGE_LAYER__;
            background-size: cover;
            background-position: center;
            border: 1px solid rgba(255, 255, 255, 0.54);
            border-radius: var(--aurelia-radius);
            min-height: 18.2rem;
            padding: 1.45rem 1.55rem;
            margin-bottom: 0.9rem;
            box-shadow: var(--aurelia-shadow);
        }

        .app-header::before {
            content: "";
            position: absolute;
            inset: 0;
            background:
                linear-gradient(116deg, transparent 0 57%, rgba(212, 167, 98, 0.34) 57% 57.35%, transparent 57.35% 100%),
                radial-gradient(circle at 79% 28%, rgba(255, 255, 255, 0.76) 0 2px, transparent 3px),
                radial-gradient(circle at 70% 61%, rgba(212, 167, 98, 0.62) 0 2px, transparent 3px);
            pointer-events: none;
        }

        .app-header::after {
            content: "";
            position: absolute;
            left: 1.55rem;
            right: 1.55rem;
            bottom: 1.1rem;
            height: 1px;
            background: linear-gradient(90deg, rgba(212, 167, 98, 0.8), rgba(255, 255, 255, 0.34), transparent);
            pointer-events: none;
        }

        .header-grid {
            position: relative;
            display: grid;
            grid-template-columns: minmax(0, 1.22fr) minmax(18rem, 0.58fr);
            gap: 1.25rem;
            align-items: end;
            min-height: 15rem;
            z-index: 1;
        }

        .brand-mark {
            display: inline-flex;
            align-items: center;
            gap: 0.65rem;
            margin-bottom: 1.35rem;
        }

        .brand-mark > span:last-child {
            display: flex;
            flex-direction: column;
        }

        .brand-monogram {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 2.45rem;
            height: 2.45rem;
            border: 1px solid rgba(255, 255, 255, 0.55);
            border-radius: 50%;
            color: #ffffff !important;
            font-weight: 840;
            background: rgba(255, 255, 255, 0.10);
            box-shadow: inset 0 0 0 1px rgba(212, 167, 98, 0.34);
        }

        .brand-name {
            display: block;
            color: #ffffff !important;
            font-size: 0.98rem;
            font-weight: 820;
        }

        .brand-subline {
            display: block;
            color: rgba(255, 255, 255, 0.74) !important;
            font-size: 0.74rem;
            font-weight: 640;
            margin-top: 0.1rem;
        }

        .brand-kicker {
            color: #f2d59d !important;
            font-size: 0.75rem;
            font-weight: 780;
            letter-spacing: 0.10em;
            text-transform: uppercase;
            margin-bottom: 0.45rem;
        }

        .app-title {
            font-size: clamp(2.25rem, 4.8vw, 4.85rem);
            line-height: 0.98;
            font-weight: 820;
            color: #ffffff !important;
            margin: 0 0 0.7rem 0;
            max-width: 44rem;
        }

        .app-subtitle {
            font-size: 1.02rem;
            line-height: 1.65;
            color: rgba(255, 255, 255, 0.84) !important;
            margin: 0;
            overflow-wrap: anywhere;
            max-width: 45rem;
        }

        .route-board {
            background: rgba(255, 255, 255, 0.14);
            border: 1px solid rgba(255, 255, 255, 0.36);
            border-radius: var(--aurelia-radius);
            padding: 1rem;
            backdrop-filter: blur(12px);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.16);
        }

        .route-label {
            color: rgba(255, 255, 255, 0.76) !important;
            font-size: 0.72rem;
            font-weight: 780;
            letter-spacing: 0.10em;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }

        .route-code {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            color: #ffffff !important;
            font-size: 1.18rem;
            font-weight: 820;
        }

        .route-code span:not(.route-line) {
            color: #ffffff !important;
        }

        .route-line {
            flex: 1;
            height: 2px;
            background: linear-gradient(90deg, var(--aurelia-sky), #ffffff, var(--aurelia-gold));
            min-width: 4rem;
        }

        .route-meta {
            color: rgba(255, 255, 255, 0.82) !important;
            font-size: 0.8rem;
            margin-top: 0.6rem;
            overflow-wrap: anywhere;
        }

        .status-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 1rem;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            min-height: 1.85rem;
            padding: 0.18rem 0.68rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 760;
            border: 1px solid transparent;
        }

        .status-ready {
            color: #075b50 !important;
            background: rgba(222, 247, 241, 0.94);
            border-color: rgba(15, 107, 94, 0.22);
        }

        .status-info {
            color: #1c587d !important;
            background: rgba(232, 244, 250, 0.94);
            border-color: rgba(46, 120, 168, 0.22);
        }

        .status-warn {
            color: #7d4c08 !important;
            background: rgba(255, 246, 226, 0.96);
            border-color: rgba(212, 167, 98, 0.34);
        }

        .service-strip {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 0.8rem;
            margin: 0 0 1.15rem 0;
        }

        .service-tile {
            position: relative;
            min-height: 6.2rem;
            background:
                linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 252, 246, 0.92));
            border: 1px solid var(--aurelia-line);
            border-top: 3px solid var(--aurelia-gold);
            border-radius: var(--aurelia-radius);
            padding: 0.82rem 0.86rem;
            box-shadow: var(--aurelia-shadow-soft);
            overflow: hidden;
        }

        .service-tile::after {
            content: "";
            position: absolute;
            right: 0.75rem;
            top: 0.95rem;
            width: 2.3rem;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(212, 167, 98, 0.9));
        }

        .service-code {
            color: var(--aurelia-gold-deep) !important;
            font-size: 0.68rem;
            font-weight: 800;
            letter-spacing: 0.10em;
            text-transform: uppercase;
        }

        .service-name {
            color: var(--aurelia-ink) !important;
            font-size: 0.96rem;
            font-weight: 790;
            margin-top: 0.5rem;
            line-height: 1.2;
        }

        .service-detail {
            color: var(--aurelia-muted) !important;
            font-size: 0.76rem;
            line-height: 1.35;
            margin-top: 0.38rem;
        }

        .section-label {
            color: var(--aurelia-muted) !important;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.10em;
            text-transform: uppercase;
            margin: 0 0 0.5rem 0;
        }

        .pane-title {
            color: var(--aurelia-ink) !important;
            font-size: 1.14rem;
            font-weight: 820;
            margin: 0 0 0.42rem 0;
        }

        .pane-caption {
            color: var(--aurelia-muted) !important;
            font-size: 0.86rem;
            margin-bottom: 0.85rem;
            overflow-wrap: anywhere;
        }

        .empty-state {
            border: 1px dashed rgba(16, 41, 70, 0.28);
            background: rgba(255, 255, 255, 0.72);
            color: var(--aurelia-muted) !important;
            border-radius: var(--aurelia-radius);
            padding: 1rem 1.05rem;
            margin-top: 0.5rem;
        }

        .source-meta {
            color: var(--aurelia-muted) !important;
            font-size: 0.82rem;
            margin-bottom: 0.45rem;
            overflow-wrap: anywhere;
        }

        .evidence-ticket {
            position: relative;
            display: grid;
            grid-template-columns: 2.85rem minmax(0, 1fr);
            gap: 0.62rem;
            align-items: center;
            background:
                linear-gradient(90deg, rgba(15, 41, 70, 0.96), rgba(46, 120, 168, 0.86));
            border-radius: var(--aurelia-radius);
            padding: 0.75rem 0.82rem;
            margin-bottom: 0.8rem;
            overflow: hidden;
        }

        .evidence-ticket::after {
            content: "";
            position: absolute;
            top: 0;
            bottom: 0;
            left: 3.58rem;
            border-left: 1px dashed rgba(255, 255, 255, 0.42);
        }

        .ticket-rank {
            color: #ffffff !important;
            font-size: 1.32rem;
            font-weight: 840;
            text-align: center;
        }

        .ticket-label {
            color: rgba(255, 255, 255, 0.62) !important;
            font-size: 0.64rem;
            font-weight: 780;
            letter-spacing: 0.10em;
            text-transform: uppercase;
            margin-bottom: 0.18rem;
        }

        .ticket-value {
            color: #ffffff !important;
            font-size: 0.76rem;
            font-weight: 740;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }

        .ticket-value span {
            display: block;
            color: #ffffff !important;
            overflow-wrap: anywhere;
        }

        .sidebar-brand {
            background:
                linear-gradient(145deg, var(--aurelia-navy), var(--aurelia-navy-2));
            border: 0;
            border-bottom: 1px solid rgba(212, 167, 98, 0.34);
            border-radius: 0;
            padding: 1.4rem 1.5rem 1.25rem;
            margin: -1rem -1.5rem 1rem;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12);
        }

        .sidebar-brand-name {
            color: #ffffff !important;
            font-size: 1.33rem;
            line-height: 1.08;
            font-weight: 850;
        }

        .sidebar-brand-sub {
            color: rgba(255, 255, 255, 0.72) !important;
            font-size: 0.76rem;
            font-weight: 680;
            margin-top: 0.45rem;
        }

        .sidebar-brand-rule {
            height: 1px;
            background: linear-gradient(90deg, var(--aurelia-gold), transparent);
            margin-top: 0.85rem;
        }

        .sidebar-section {
            color: var(--aurelia-ink-soft) !important;
            font-size: 0.75rem;
            font-weight: 820;
            letter-spacing: 0.10em;
            text-transform: uppercase;
            margin: 0.6rem 0 0.45rem 0;
        }

        section[data-testid="stSidebar"] .sidebar-section.light {
            color: var(--aurelia-muted) !important;
        }

        .sidebar-meta {
            color: var(--aurelia-muted) !important;
            font-size: 0.78rem;
            margin: 0.1rem 0 0.85rem 0;
            overflow-wrap: anywhere;
        }

        .manifest {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.6rem;
            margin-top: 0.4rem;
        }

        .manifest-cell {
            background: rgba(255, 255, 255, 0.86);
            border: 1px solid var(--aurelia-line);
            border-radius: var(--aurelia-radius);
            padding: 0.65rem;
        }

        .manifest-label {
            color: var(--aurelia-muted) !important;
            font-size: 0.7rem;
            font-weight: 780;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .manifest-value {
            color: var(--aurelia-ink) !important;
            font-size: 0.95rem;
            font-weight: 790;
            margin-top: 0.2rem;
            overflow-wrap: anywhere;
        }

        @media (max-width: 980px) {
            .header-grid,
            .service-strip,
            .manifest {
                grid-template-columns: 1fr;
            }

            .app-title {
                font-size: 2.25rem;
            }

            .app-header {
                min-height: 21rem;
                padding: 1.2rem;
                background-position: 58% center;
            }

            .header-grid {
                min-height: 18rem;
            }
        }

        @media (max-width: 520px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
                padding-top: 0.85rem;
            }

            .app-title {
                font-size: 2rem;
            }

            .app-subtitle {
                font-size: 0.92rem;
                line-height: 1.55;
            }

            .status-badge {
                font-size: 0.72rem;
                min-height: 1.72rem;
            }

            .service-tile {
                min-height: 5.4rem;
            }

            .evidence-ticket {
                grid-template-columns: 2.85rem minmax(0, 1fr);
            }
        }
        </style>
        """

    st.markdown(
        css.replace("__HERO_IMAGE_LAYER__", hero_image_layer),
        unsafe_allow_html=True,
    )


def load_frontend_config() -> dict[str, str]:
    """Load display-safe configuration values for the Streamlit sidebar."""
    load_dotenv(ENV_PATH)
    return {
        "chat_key_set": "Yes" if is_configured("LLM_API_KEY", "DASHSCOPE_API_KEY") else "No",
        "embedding_key_set": "Yes" if is_configured("EMBEDDING_API_KEY", "DASHSCOPE_API_KEY") else "No",
        "chat_model": configured_model_name(
            "LLM_CHAT_MODEL",
            default=DEFAULT_DASHSCOPE_CHAT_MODEL,
        ),
        "embedding_model": configured_model_name(
            "EMBEDDING_MODEL",
            default=DEFAULT_DASHSCOPE_EMBEDDING_MODEL,
        ),
        "top_k": os.getenv("TOP_K", "3").strip() or "3",
    }


def validate_question(question: str) -> str:
    """Return a stripped question or raise a user-facing validation error."""
    cleaned = question.strip()
    if not cleaned:
        raise ValueError("Please enter a passenger service request before dispatch.")
    return cleaned


def validate_runtime_ready() -> None:
    """Check local files and configuration before calling the RAG pipeline."""
    load_dotenv(ENV_PATH)

    if not ENV_PATH.exists():
        raise FileNotFoundError("Missing .env file. Copy .env.example to .env and fill in the required values.")

    has_chat_key = is_configured("LLM_API_KEY", "DASHSCOPE_API_KEY")
    has_embedding_key = is_configured("EMBEDDING_API_KEY", "DASHSCOPE_API_KEY")
    if not has_chat_key:
        raise ValueError("LLM_API_KEY or DASHSCOPE_API_KEY is missing in .env.")
    if not has_embedding_key:
        raise ValueError("EMBEDDING_API_KEY or DASHSCOPE_API_KEY is missing in .env.")

    if not INDEX_PATH.exists() or not CHUNKS_PATH.exists():
        raise FileNotFoundError(
            "Missing saved service index files. Run python3 src/embed_index.py before using Policy Concierge."
        )


def ensure_current_conversation() -> str:
    """Load the active conversation or create one if no history exists."""
    init_db()
    conversations = list_conversations()
    current_id = st.session_state.get("current_conversation_id")
    conversation_ids = {conversation["id"] for conversation in conversations}

    if current_id in conversation_ids:
        return current_id

    if conversations:
        current_id = conversations[0]["id"]
    else:
        current_id = create_conversation()

    st.session_state.current_conversation_id = current_id
    return current_id


def create_new_conversation() -> None:
    """Start a blank conversation and make it active."""
    st.session_state.current_conversation_id = create_conversation()
    st.rerun()


def select_conversation(conversation_id: str) -> None:
    """Switch the active conversation in the Streamlit session."""
    st.session_state.current_conversation_id = conversation_id
    st.rerun()


def remove_conversation(conversation_id: str) -> None:
    """Delete a conversation and select the next available one."""
    delete_conversation(conversation_id)
    st.session_state.pop("pending_delete_conversation", None)
    remaining = list_conversations()
    if remaining:
        st.session_state.current_conversation_id = remaining[0]["id"]
    else:
        st.session_state.current_conversation_id = create_conversation()
    st.rerun()


def request_conversation_deletion(conversation_id: str, title: str) -> None:
    """Store a pending deletion request for the confirmation dialog."""
    st.session_state.pending_delete_conversation = {
        "id": conversation_id,
        "title": title,
    }
    st.rerun()


def request_conversation_rename(conversation_id: str, title: str) -> None:
    """Store a pending rename request for the edit dialog."""
    st.session_state.pending_rename_conversation = {
        "id": conversation_id,
        "title": title,
    }
    st.rerun()


@st.dialog("Rename conversation")
def show_conversation_rename_dialog(conversation_id: str, title: str) -> None:
    """Collect and persist a new conversation title."""
    with st.form(f"rename_conversation_{conversation_id}"):
        new_title = st.text_input(
            "Conversation name",
            value=title,
            max_chars=50,
            placeholder="Enter a conversation name",
        )
        cancel_col, save_col = st.columns(2)
        cancel = cancel_col.form_submit_button("Cancel", use_container_width=True)
        save = save_col.form_submit_button(
            "Save",
            type="primary",
            icon=":material/check:",
            use_container_width=True,
        )

    if cancel:
        st.session_state.pop("pending_rename_conversation", None)
        st.rerun()

    if save:
        try:
            rename_conversation(conversation_id, new_title)
        except ValueError as exc:
            st.error(str(exc))
            return
        st.session_state.pop("pending_rename_conversation", None)
        st.rerun()


@st.dialog("Delete conversation?")
def confirm_conversation_deletion(conversation_id: str, title: str) -> None:
    """Confirm a destructive conversation deletion."""
    st.write(f'Permanently delete "{title}" and all of its messages?')
    st.caption("This action cannot be undone.")
    cancel_col, delete_col = st.columns(2)
    with cancel_col:
        if st.button("Cancel", use_container_width=True):
            st.session_state.pop("pending_delete_conversation", None)
            st.rerun()
    with delete_col:
        if st.button(
            "Delete",
            type="primary",
            icon=":material/delete:",
            use_container_width=True,
        ):
            remove_conversation(conversation_id)


def format_timestamp(raw_timestamp: str) -> str:
    """Format an ISO timestamp for compact UI display."""
    if not raw_timestamp:
        return "Unknown time"

    try:
        parsed = datetime.fromisoformat(raw_timestamp)
    except ValueError:
        return raw_timestamp

    return parsed.strftime("%Y-%m-%d %H:%M")


def format_case_title(raw_title: Any) -> str:
    """Normalize legacy conversation titles into the concierge language."""
    title = (raw_title or "").strip()
    if not title or title == "New conversation":
        return "New concierge case"
    return title


def get_status_badges() -> list[tuple[str, str]]:
    """Return display badges for the current app readiness state."""
    config = load_frontend_config()
    badges: list[tuple[str, str]] = []

    index_ready = INDEX_PATH.exists() and CHUNKS_PATH.exists()
    chat_ready = config["chat_key_set"] == "Yes"
    embedding_ready = config["embedding_key_set"] == "Yes"

    if index_ready:
        badges.append(("Index Ready", "status-ready"))
    else:
        badges.append(("Index Missing", "status-warn"))

    if chat_ready:
        badges.append((f"Chat: {config['chat_model']}", "status-ready"))
    else:
        badges.append(("Chat Missing", "status-warn"))

    if embedding_ready:
        badges.append((f"Embedding: {config['embedding_model']}", "status-ready"))
    else:
        badges.append(("Embedding Missing", "status-warn"))

    badges.append((f"Evidence Top {config['top_k']}", "status-info"))
    return badges


def render_badges(badges: list[tuple[str, str]]) -> str:
    """Render status badges as safe HTML."""
    return "".join(
        f'<span class="status-badge {escape(css_class)}">{escape(label)}</span>'
        for label, css_class in badges
    )


def render_header(conversation: dict[str, Any]) -> None:
    """Render the premium airline hero with status badges."""
    title = escape(format_case_title(conversation.get("title")))
    turn_count = len(conversation.get("turns", []))
    badge_html = render_badges(get_status_badges())

    st.markdown(
        f"""
        <div class="app-header">
            <div class="header-grid">
                <div>
                    <div class="brand-mark">
                        <span class="brand-monogram">A</span>
                        <span>
                            <span class="brand-name">Aurelia Airways</span>
                            <span class="brand-subline">Premium passenger support</span>
                        </span>
                    </div>
                    <div class="brand-kicker">Policy-grounded service intelligence</div>
                    <div class="app-title">Policy Concierge</div>
                    <p class="app-subtitle">Premium passenger support for fares, baggage,
                    check-in, disruption care, and refunds with grounded policy evidence.</p>
                    <div class="status-row">{badge_html}</div>
                </div>
                <div class="route-board">
                    <div class="route-label">Active service route</div>
                    <div class="route-code">
                        <span>AUR</span>
                        <span class="route-line"></span>
                        <span>CON</span>
                    </div>
                    <div class="route-meta">{title} | {turn_count} turn(s)</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_service_strip() -> None:
    """Render the premium passenger service area strip."""
    service_areas = [
        ("RES", "Reservations", "Fare rules and booking changes"),
        ("CKI", "Check-in", "Deadlines, documents, boarding"),
        ("BAG", "Baggage", "Allowance, special items, claims"),
        ("REF", "Refunds", "Eligibility and processing"),
        ("IRR", "Disruption Care", "Delays, cancellations, support"),
    ]
    tiles = "".join(
        f'<div class="service-tile"><div class="service-code">{escape(code)}</div>'
        f'<div class="service-name">{escape(name)}</div>'
        f'<div class="service-detail">{escape(detail)}</div></div>'
        for code, name, detail in service_areas
    )

    st.markdown(f'<div class="service-strip">{tiles}</div>', unsafe_allow_html=True)


def render_sidebar_brand() -> None:
    """Render the Aurelia Airways sidebar identity panel."""
    st.sidebar.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-brand-name">Aurelia Airways</div>
            <div class="sidebar-brand-sub">Policy Concierge console</div>
            <div class="sidebar-brand-rule"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_project_status() -> None:
    """Render project health details without exposing secrets."""
    st.sidebar.markdown('<div class="sidebar-section light">System Readiness</div>', unsafe_allow_html=True)
    for label, css_class in get_status_badges():
        st.sidebar.markdown(
            f'<span class="status-badge {escape(css_class)}">{escape(label)}</span>',
            unsafe_allow_html=True,
        )

    index_state = "Available" if INDEX_PATH.exists() else "Missing"
    chunk_state = "Available" if CHUNKS_PATH.exists() else "Missing"
    st.sidebar.markdown(
        f'<div class="sidebar-meta">FAISS index: {escape(index_state)}</div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f'<div class="sidebar-meta">Chunk metadata: {escape(chunk_state)}</div>',
        unsafe_allow_html=True,
    )


def render_conversation_list(current_conversation_id: str) -> None:
    """Render saved conversations in the sidebar."""
    st.sidebar.markdown('<div class="sidebar-section">Case History</div>', unsafe_allow_html=True)

    if st.sidebar.button("Open New Case", type="primary", use_container_width=True):
        create_new_conversation()

    conversations = list_conversations()
    if not conversations:
        st.sidebar.info("No saved concierge cases yet.")
        return

    for conversation in conversations:
        title = format_case_title(conversation["title"])
        turn_count = conversation["turn_count"]
        updated_at = conversation["updated_at"]
        is_active = conversation["id"] == current_conversation_id
        label = f"Active - {title}" if is_active else title
        label = f"{label} ({turn_count})"
        button_type = "primary" if is_active else "secondary"

        conversation_col, rename_col, delete_col = st.sidebar.columns(
            [0.72, 0.14, 0.14],
            gap="small",
        )
        with conversation_col:
            if st.button(
                label,
                key=f"conversation_{conversation['id']}",
                type=button_type,
                use_container_width=True,
            ):
                select_conversation(conversation["id"])

        with rename_col:
            if st.button(
                " ",
                key=f"conversation_rename_{conversation['id']}",
                type="tertiary",
                icon=":material/edit:",
                help=f"Rename {title}",
                use_container_width=True,
            ):
                request_conversation_rename(conversation["id"], title)

        with delete_col:
            if st.button(
                " ",
                key=f"conversation_delete_{conversation['id']}",
                type="tertiary",
                icon=":material/delete:",
                help=f"Delete {title}",
                use_container_width=True,
            ):
                request_conversation_deletion(conversation["id"], title)

        st.sidebar.markdown(
            f'<div class="sidebar-meta">Updated {escape(format_timestamp(updated_at))}</div>',
            unsafe_allow_html=True,
        )


def render_sidebar(current_conversation_id: str) -> None:
    """Render navigation and system status."""
    render_sidebar_brand()
    render_conversation_list(current_conversation_id)
    st.sidebar.divider()
    render_project_status()


def render_sources(
    chunks: list[dict[str, Any]],
    heading: str = "Policy Evidence",
    compact: bool = False,
) -> None:
    """Render retrieved chunks as expandable source panels."""
    if compact:
        st.markdown(f'<div class="section-label">{escape(heading)}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="pane-title">{escape(heading)}</div>', unsafe_allow_html=True)

    if not chunks:
        st.markdown(
            '<div class="empty-state">No policy evidence has been retrieved.</div>',
            unsafe_allow_html=True,
        )
        return

    for rank, chunk in enumerate(chunks, start=1):
        source = chunk.get("source", "unknown")
        chunk_id = chunk.get("chunk_id", "unknown")
        policy_area = chunk.get("policy_area", "general")
        retrieval_distance = chunk.get("retrieval_distance")
        text = chunk.get("text", "")

        with st.expander(f"Boarding Pass {rank}: {source} | {chunk_id}"):
            distance_text = (
                f" | distance {retrieval_distance:.3f}"
                if isinstance(retrieval_distance, (int, float))
                else ""
            )
            st.markdown(
                f"""
                <div class="evidence-ticket">
                    <div class="ticket-rank">{rank}</div>
                    <div>
                        <div class="ticket-label">Policy Source</div>
                        <div class="ticket-value">
                            <span>{escape(source)}</span>
                            <span>{escape(chunk_id)}</span>
                        </div>
                    </div>
                </div>
                <div class="source-meta">Evidence rank {rank} | {escape(policy_area)}{escape(distance_text)} | {escape(source)} | {escape(chunk_id)}</div>
                """,
                unsafe_allow_html=True,
            )
            st.write(text)


def render_decision_context(decision: dict[str, Any], verification: Any = None) -> None:
    """Render reliability action details below an assistant response."""
    action = decision.get("action", "answer")
    if action == "escalate":
        return

    reason = decision.get("confidence_reason", "")
    missing = decision.get("missing_info", {}).get("missing_fields", [])
    if not missing:
        missing = decision.get("missing_fields", [])
    verification = verification or decision.get("verification") or {}

    st.caption(f"Reliability action: {action}")
    if reason:
        st.caption(reason)
    if missing:
        st.caption("Missing fields: " + ", ".join(missing))
    if verification:
        st.caption(
            "Verification: "
            + str(verification.get("verdict", "unknown"))
            + " / "
            + str(verification.get("citation_quality", "unknown"))
        )


def render_handoff_status(status: str) -> None:
    """Render a standalone customer-service connection event."""
    if status == "connected":
        css_class = ""
        label = "Connected to customer service"
        icon = """
            <path d="M4 13v-1a8 8 0 0 1 16 0v1" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <path d="M4 13a2 2 0 0 1 2-2h1v6H6a2 2 0 0 1-2-2v-2Zm16 0a2 2 0 0 0-2-2h-1v6h1a2 2 0 0 0 2-2v-2Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <path d="M17 18c-.8 1.2-2.1 2-4 2h-1" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        """
    else:
        css_class = " disconnected"
        label = "Disconnected from customer service"
        icon = """
            <path d="M4 13v-1a8 8 0 0 1 13.7-5.6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <path d="M4 13a2 2 0 0 1 2-2h1v6H6a2 2 0 0 1-2-2v-2Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <path d="m16 10 5 5m0-5-5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        """

    st.markdown(
        f"""
        <div class="human-support-badge{css_class}" role="status" aria-label="{label}">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">{icon}</svg>
            <span>{label}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_human_support_replies(turn: dict[str, Any]) -> None:
    """Render customer-service replies associated with an escalated turn."""
    support = turn.get("human_support") or {}
    for reply in support.get("messages", []):
        sender = escape(str(reply.get("sender_name") or "Customer Service"))
        with st.chat_message("assistant", avatar="🎧"):
            st.markdown(
                f'<div class="customer-service-message-marker">Customer service · {sender}</div>',
                unsafe_allow_html=True,
            )
            st.write(str(reply.get("message") or ""))


def _turn_occurred_during_handoff(
    turn: dict[str, Any],
    handoff_turns: list[dict[str, Any]],
) -> bool:
    """Identify legacy AI turns created while a human handoff controlled the chat."""
    turn_index = int(turn.get("turn_index") or 0)
    turn_created_at = str(turn.get("created_at") or "")
    for handoff_turn in handoff_turns:
        if turn_index <= int(handoff_turn.get("turn_index") or 0):
            continue
        support = handoff_turn.get("human_support") or {}
        if support.get("status") in {"pending", "in_progress"}:
            return True
        if support.get("status") == "resolved":
            resolved_at = str(support.get("updated_at") or "")
            if turn_created_at and resolved_at and turn_created_at <= resolved_at:
                return True
    return False


def build_chat_timeline(conversation: dict[str, Any]) -> list[dict[str, Any]]:
    """Merge AI turns and human-support messages into one chronological stream."""
    turns = conversation.get("turns", [])
    handoff_turns = [turn for turn in turns if turn.get("human_support")]
    timeline: list[dict[str, Any]] = []

    for turn in turns:
        created_at = str(turn.get("created_at") or "")
        turn_index = int(turn.get("turn_index") or 0)
        timeline.append(
            {
                "kind": "customer",
                "created_at": created_at,
                "order": (turn_index, 0),
                "text": str(turn.get("question") or ""),
            }
        )
        if not _turn_occurred_during_handoff(turn, handoff_turns):
            timeline.append(
                {
                    "kind": "ai",
                    "created_at": created_at,
                    "order": (turn_index, 1),
                    "turn": turn,
                }
            )

        support = turn.get("human_support") or {}
        if support:
            timeline.append(
                {
                    "kind": "handoff_connected",
                    "created_at": str(support.get("created_at") or created_at),
                    "order": (turn_index, 2),
                }
            )
        for message_index, message in enumerate(support.get("messages", [])):
            timeline.append(
                {
                    "kind": (
                        "customer"
                        if message.get("sender_type") == "customer"
                        else "agent"
                    ),
                    "created_at": str(message.get("created_at") or ""),
                    "order": (turn_index, 3 + message_index),
                    "text": str(message.get("message") or ""),
                    "sender_name": str(
                        message.get("sender_name") or "Customer Service"
                    ),
                }
            )
        if support.get("status") == "resolved":
            timeline.append(
                {
                    "kind": "handoff_disconnected",
                    "created_at": str(support.get("updated_at") or ""),
                    "order": (turn_index, 3 + len(support.get("messages", []))),
                }
            )

    timeline.sort(key=lambda event: (event["created_at"], event["order"]))
    return timeline


def render_turn(turn: dict[str, Any]) -> None:
    """Render one saved user/assistant turn."""
    with st.chat_message("user"):
        st.write(turn.get("question", ""))

    with st.chat_message("assistant"):
        st.write(turn.get("answer", ""))
        render_decision_context(turn, turn.get("verification_result"))
        source_count = len(turn.get("sources", []))
        with st.expander(f"Sources ({source_count})", expanded=False):
            render_sources(turn.get("sources", []), heading="Evidence", compact=True)

    if turn.get("human_support"):
        render_handoff_status("connected")
    render_human_support_replies(turn)
    if (turn.get("human_support") or {}).get("status") == "resolved":
        render_handoff_status("disconnected")


def render_chat_pane(conversation: dict[str, Any]) -> None:
    """Render the central chat pane."""
    st.markdown('<div class="section-label">Concierge Response</div>', unsafe_allow_html=True)

    turns = conversation.get("turns", [])
    if not turns:
        st.markdown(
            '<div class="empty-state">Ready for the next passenger service request.</div>',
            unsafe_allow_html=True,
        )
        return

    for event in build_chat_timeline(conversation):
        if event["kind"] == "handoff_connected":
            render_handoff_status("connected")
            continue

        if event["kind"] == "handoff_disconnected":
            render_handoff_status("disconnected")
            continue

        if event["kind"] == "customer":
            with st.chat_message("user"):
                st.write(event["text"])
            continue

        if event["kind"] == "agent":
            with st.chat_message("assistant", avatar="🎧"):
                sender = escape(event["sender_name"])
                st.markdown(
                    f'<div class="customer-service-message-marker">Customer service · {sender}</div>',
                    unsafe_allow_html=True,
                )
                st.write(event["text"])
            continue

        turn = event["turn"]
        with st.chat_message("assistant"):
            st.write(turn.get("answer", ""))
            render_decision_context(turn, turn.get("verification_result"))
            source_count = len(turn.get("sources", []))
            with st.expander(f"Sources ({source_count})", expanded=False):
                render_sources(turn.get("sources", []), heading="Evidence", compact=True)


def render_question_intake() -> str:
    """Render the persistent bottom chat composer."""
    return st.chat_input(
        "Ask a passenger policy question",
        key="passenger_question_input",
    ) or ""


def get_latest_sources(conversation: dict[str, Any]) -> list[dict[str, Any]]:
    """Return sources for the latest assistant answer."""
    turns = conversation.get("turns", [])
    if not turns:
        return []
    return turns[-1].get("sources", [])


def render_evidence_pane(conversation: dict[str, Any]) -> None:
    """Render the right evidence and session summary pane."""
    latest_sources = get_latest_sources(conversation)
    turns = conversation.get("turns", [])

    st.markdown('<div class="section-label">Policy Evidence</div>', unsafe_allow_html=True)
    st.markdown('<div class="pane-title">Latest Policy Evidence</div>', unsafe_allow_html=True)

    if turns:
        latest_turn = turns[-1]
        st.markdown(
            f'<div class="pane-caption">Turn {latest_turn.get("turn_index", len(turns))} | '
            f'{len(latest_sources)} source(s)</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="pane-caption">No retrieved evidence yet.</div>', unsafe_allow_html=True)

    render_sources(latest_sources, heading="Retrieved Evidence", compact=True)

    st.divider()
    st.markdown('<div class="pane-title">Service Manifest</div>', unsafe_allow_html=True)
    manifest_html = f"""
    <div class="manifest">
        <div class="manifest-cell">
            <div class="manifest-label">Case</div>
            <div class="manifest-value">{escape(format_case_title(conversation.get('title')))}</div>
        </div>
        <div class="manifest-cell">
            <div class="manifest-label">Turns</div>
            <div class="manifest-value">{len(turns)}</div>
        </div>
        <div class="manifest-cell">
            <div class="manifest-label">Updated</div>
            <div class="manifest-value">{escape(format_timestamp(conversation.get('updated_at', '')))}</div>
        </div>
        <div class="manifest-cell">
            <div class="manifest-label">Carrier</div>
            <div class="manifest-value">Aurelia Airways</div>
        </div>
    </div>
    """
    st.markdown(manifest_html, unsafe_allow_html=True)


def handle_user_question(conversation_id: str, question: str) -> None:
    """Run retrieval, generate a conversation-aware answer, and persist the turn."""
    cleaned_question = validate_question(question)
    if add_handoff_customer_message(conversation_id, cleaned_question):
        st.rerun()

    validate_runtime_ready()
    history_turns = get_recent_turns(conversation_id, limit=6)

    with st.chat_message("user"):
        st.write(cleaned_question)

    with st.chat_message("assistant"):
        with st.spinner("Checking policy evidence and reliability gates..."):
            result = generate_reliable_answer(cleaned_question, history_turns)

        retrieved_chunks = result["retrieved_chunks"]
        final_answer = result["answer"]
        decision = result["decision"]
        st.write(final_answer or "No answer was returned.")
        render_decision_context(decision, result.get("verification"))
        with st.expander(f"Sources ({len(retrieved_chunks)})", expanded=True):
            render_sources(retrieved_chunks, heading="Evidence", compact=True)

    add_turn(
        conversation_id,
        cleaned_question,
        final_answer,
        retrieved_chunks,
        decision_result=decision,
    )
    st.rerun()


@st.fragment(run_every="2s")
def render_live_conversation(conversation_id: str) -> None:
    """Refresh shared conversation data without reloading the page composer."""
    conversation = get_conversation(conversation_id)

    render_header(conversation)
    render_service_strip()

    chat_col, evidence_col = st.columns([0.64, 0.36], gap="large")
    with chat_col:
        render_chat_pane(conversation)
    with evidence_col:
        render_evidence_pane(conversation)


def main() -> None:
    st.set_page_config(
        page_title="Aurelia Airways Policy Concierge",
        page_icon="A",
        layout="wide",
    )
    apply_theme()

    current_conversation_id = ensure_current_conversation()
    render_sidebar(current_conversation_id)
    pending_rename = st.session_state.get("pending_rename_conversation")
    if pending_rename:
        show_conversation_rename_dialog(
            pending_rename["id"],
            pending_rename["title"],
        )
    pending_delete = st.session_state.get("pending_delete_conversation")
    if pending_delete:
        confirm_conversation_deletion(
            pending_delete["id"],
            pending_delete["title"],
        )
    render_live_conversation(current_conversation_id)

    # Keep the composer in the main page container. Streamlit renders a
    # chat_input nested inside a fragment inline, which pushes it below the
    # initial viewport. At the page root it is pinned to the viewport bottom.
    question = render_question_intake()
    if not question:
        return

    try:
        handle_user_question(current_conversation_id, question)
    except Exception as exc:
        st.error(str(exc))
        if question.strip():
            st.write("Question preserved:")
            st.code(question.strip())


if __name__ == "__main__":
    main()
