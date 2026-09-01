"""
Chat with your reports — Streamlit app.

Run with: streamlit run app.py
"""

import os
import streamlit as st
from dotenv import load_dotenv
import anthropic

from db import get_engine, get_schema_summary, run_query
from excel_loader import load_excel, summarize_sheets, query_sheet
from agent import ask_agent

load_dotenv()

st.set_page_config(page_title="Chat with your reports", layout="wide")
st.title("Chat with your reports")

# --- Sidebar: connections & uploads ---
with st.sidebar:
    st.header("Data sources")

    sql_status = st.empty()
    if "engine" not in st.session_state:
        try:
            st.session_state.engine = get_engine()
            allowed = os.environ.get("SQL_ALLOWED_TABLES", "")
            allowed_tables = [t.strip() for t in allowed.split(",") if t.strip()] or None
            st.session_state.sql_schema_summary = get_schema_summary(
                st.session_state.engine, allowed_tables
            )
            sql_status.success("Connected to SQL Server")
        except Exception as e:
            st.session_state.engine = None
            st.session_state.sql_schema_summary = "(SQL Server not connected)"
            sql_status.error(f"SQL Server connection failed: {e}")

    st.divider()
    st.subheader("Excel report")
    uploaded = st.file_uploader("Upload your Excel report (.xlsx)", type=["xlsx"])
    if uploaded is not None:
        st.session_state.sheets = load_excel(uploaded)
        st.session_state.excel_summary = summarize_sheets(st.session_state.sheets)
        st.success(f"Loaded {len(st.session_state.sheets)} sheet(s)")
    elif "sheets" not in st.session_state:
        st.session_state.sheets = {}
        st.session_state.excel_summary = "(no Excel file uploaded yet)"

# --- Main chat interface ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []       # Claude API message history
if "display_history" not in st.session_state:
    st.session_state.display_history = []    # what's shown on screen

for turn in st.session_state.display_history:
    with st.chat_message(turn["role"]):
        st.markdown(turn["content"])

question = st.chat_input("Ask a question about your data...")

if question:
    st.session_state.display_history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("Set ANTHROPIC_API_KEY in your .env file.")
    else:
        client = anthropic.Anthropic(api_key=api_key)

        def run_sql_fn(sql):
            if st.session_state.engine is None:
                raise RuntimeError("SQL Server is not connected.")
            return run_query(st.session_state.engine, sql)

        def get_sheet_fn(sheet_name):
            if sheet_name not in st.session_state.sheets:
                raise RuntimeError(f"No sheet named '{sheet_name}' was uploaded.")
            return query_sheet(st.session_state.sheets, sheet_name, "")

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    answer, updated_history = ask_agent(
                        client=client,
                        question=question,
                        sql_schema_summary=st.session_state.sql_schema_summary,
                        excel_summary=st.session_state.excel_summary,
                        run_sql_fn=run_sql_fn,
                        get_sheet_fn=get_sheet_fn,
                        history=st.session_state.chat_history,
                    )
                    st.session_state.chat_history = updated_history
                    st.markdown(answer)
                    st.session_state.display_history.append(
                        {"role": "assistant", "content": answer}
                    )
                except Exception as e:
                    st.error(f"Something went wrong: {e}")
