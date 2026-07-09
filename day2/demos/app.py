"""
app.py — Day 2 LIVE DEMO entry point: all six RAG demos in one app, navigated by
horizontal SUB-TABS across the top (same feel as Day 1's slide tabs).

Run from the repo root (venv active):

    streamlit run day2/demos/app.py

Each page is ALSO a standalone app (streamlit run day2/demos/demo_04_...py) —
share any single file and it runs by itself, silently filling in the earlier
pipeline stages with the lab defaults.
"""

from __future__ import annotations

import streamlit as st

import rag_demo_common as rc  # sys.path bootstrap + the classroom stylesheet

# Set the page config here (once), before st.navigation renders the top tab strip.
st.set_page_config(page_title="Day 2 · RAG live demo", page_icon="🔎", layout="wide")
rc.inject_css()  # style the native top-nav as gradient pill sub-tabs

pages = [
    st.Page("demo_00_pipeline.py", title="Overview", icon="🗺️", default=True),
    st.Page("demo_01_load.py", title="1 · Load", icon="📂"),
    st.Page("demo_02_chunking.py", title="2 · Chunk", icon="✂️"),
    st.Page("demo_03_embed_store.py", title="3 · Embed", icon="🧠"),
    st.Page("demo_04_retrieval.py", title="4 · Retrieve", icon="🔍"),
    st.Page("demo_05_answer.py", title="5 · Answer", icon="💬"),
    st.Page("demo_06_break_it.py", title="6 · Break it", icon="💥"),
]

# position="top" → horizontal sub-tabs; only the active page's code runs (lazy).
st.navigation(pages, position="top").run()
