# views/project_view.py
# ==============================================================
# Collaborative CPM Tool – main Streamlit workspace
# ==============================================================

from __future__ import annotations
import pandas as pd
import streamlit as st

from database import get_project_data_from_db, save_project_data_to_db
from cpm_logic import calculate_cpm
from utils import get_sample_data
from gantt_chart import create_gantt_chart
from network_diagram import create_network_figure

REQUIRED = ["Task ID", "Task Description", "Predecessors", "Duration"]


# ─────────────────────────── helpers ────────────────────────────
def guarantee_percent(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure a Percent Complete column (default 0)."""
    if "Percent Complete" not in df.columns:
        df["Percent Complete"] = 0
    return df


# ─────────────────────────── main view ───────────────────────────
def show_project_view(project_id: int = 1) -> None:
    st.header("🏗️ Collaborative Renovation Project Hub")

    start_date = st.date_input(
        "Construction Start Date", value=pd.Timestamp("2025-01-01")
    )

    # -------- 1 · always load latest tasks from persistent DB -----
    df_tasks = get_project_data_from_db(project_id)
    if df_tasks.empty:
        df_tasks = get_sample_data()
    df_tasks = guarantee_percent(df_tasks)

    # put initial data into session (first run only)
    if "grid_df" not in st.session_state:
        st.session_state["grid_df"] = df_tasks.copy()

    # -------- 2 · editable grid -----------------------------------
    st.subheader("1 · Editable Task Table")
    edited_df = st.data_editor(
        st.session_state["grid_df"],          # current working copy
        use_container_width=True,
        num_rows="dynamic",
        key="task_grid",                      # widget key
    )
    # keep cache in sync on every rerun
    st.session_state["grid_df"] = edited_df.copy()

    # -------- 3 · save button -------------------------------------
    if st.button("💾 Save to DB & Re-calculate", type="primary"):
        to_save = guarantee_percent(pd.DataFrame(st.session_state["grid_df"]))
        to_save["Percent Complete"] = (
            pd.to_numeric(to_save["Percent Complete"], errors="coerce")
            .fillna(0)
            .clip(0, 100)
        )
        save_project_data_to_db(to_save, project_id)
        st.success("Saved to database.")

        # update cache so charts below use the saved, canonical data
        st.session_state["grid_df"] = to_save.copy()

    # -------- 4 · build CPM & charts from working copy ------------
    working_df = pd.DataFrame(st.session_state["grid_df"])
    if not working_df.empty:
        cpm_df = calculate_cpm(working_df)

        st.subheader("2 · CPM Results")
        st.dataframe(cpm_df, use_container_width=True)

        st.subheader("3 · CPM Network Diagram")
        st.plotly_chart(
            create_network_figure(cpm_df), use_container_width=True
        )

        st.subheader("4 · Project Gantt Chart")
        st.plotly_chart(
            create_gantt_chart(cpm_df, start_date=start_date),
            use_container_width=True,
        )
