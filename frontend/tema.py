"""Anayasa 8.1 — her sayfanin ILK cagrisi.
tema.kur(sayfa_basligi) -> st.set_page_config + styles.css enjeksiyonu."""
from __future__ import annotations
import streamlit as st
from pathlib import Path


def kur(sayfa_basligi: str):
    st.set_page_config(
        page_title=f"PVQuant — {sayfa_basligi}",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    css = Path("assets/styles.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
