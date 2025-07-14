# views/project_view.py
from __future__ import annotations
import pandas as pd
import streamlit as st

from database import get_project_data_from_db, save_project_data_to_db
from cpm_logic import calculate_cpm
from utils import get_sample_data
from gantt_chart import create_gantt_chart
from network_diagram import create_network_figure

REQUIRED = ["Task ID", "Task Description", "Predecessors", "Duration"]


# ─────────────────────────── helpers ─────────────────────────────
def guarantee_percent(df: pd.DataFrame) -> pd.DataFrame:
    if "Percent Complete" not in df.columns:
        df["Percent Complete"] = 0
    return df


# ─────────────────────────── main view ───────────────────────────
def show_project_view(project_id: int = 1) -> None:
    st.header("🏗️ Collaborative Renovation Project Hub")

    start_date = st.date_input(
        "Construction Start Date", value=pd.Timestamp("2025-01-01")
    )

    # --------- always load latest tasks from DB -------------------
    df_tasks = get_project_data_from_db(project_id)
    if df_tasks.empty:
        df_tasks = get_sample_data()
    df_tasks = guarantee_percent(df_tasks)

    # put initial data in session_state (first load only)
    if "task_grid" not in st.session_state:
        st.session_state["task_grid"] = df_tasks.copy()

    st.subheader("1 · Editable Task Table")
    st.data_editor(
        st.session_state["task_grid"],
        use_container_width=True,
        num_rows="dynamic",
        key="task_grid",
    )

    # --------- Save button ----------------------------------------
    if st.button("💾 Save to DB & Re-calculate", type="primary"):
        edited_df = pd.DataFrame(st.session_state["task_grid"])
        edited_df = guarantee_percent(edited_df)
        edited_df["Percent Complete"] = (
            pd.to_numeric(edited_df["Percent Complete"], errors="coerce")
            .fillna(0)
            .clip(0, 100)
        )
        save_project_data_to_db(edited_df, project_id)
        st.success("Saved to database.")

        # replace working copy with what we just saved
        st.session_state["task_grid"] = edited_df.copy()

    # --------- CPM & charts built from current grid ---------------
    working_df = pd.DataFrame(st.session_state["task_grid"])
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
