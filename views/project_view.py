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


# ───────────────────────────────────────── helpers ────────────────
def guarantee_percent(df: pd.DataFrame) -> pd.DataFrame:
    if "Percent Complete" not in df.columns:
        df["Percent Complete"] = 0
    return df


def validate_upload(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        st.error("Missing column(s): " + ", ".join(missing))
        st.stop()
    if df["Task ID"].eq("").any() or df["Task ID"].duplicated().any():
        st.error("Blank or duplicate Task IDs detected.")
        st.stop()
    dur = pd.to_numeric(df["Duration"], errors="coerce")
    if dur.isna().any() or (dur < 0).any():
        st.error("Duration must be numeric and ≥ 0.")
        st.stop()


# ───────────────────────────────────────── main view ──────────────
def show_project_view(project_id: int = 1) -> None:
    st.header("🏗️ Collaborative Renovation Project Hub")

    start_date = st.date_input(
        "Construction Start Date", value=pd.Timestamp("2025-01-01")
    )

    # ---------- optional file import ---------------------------------
    upl = st.file_uploader(
        "Import schedule (Excel or CSV)",
        type=["csv", "xls", "xlsx"],
        help="Required columns: " + ", ".join(REQUIRED),
    )

    if upl:
        raw = (
            pd.read_excel(upl)
            if upl.name.lower().endswith(("xls", "xlsx"))
            else pd.read_csv(upl)
        )
        validate_upload(raw)
        raw = guarantee_percent(raw)

        st.info("File preview:")
        st.dataframe(raw, use_container_width=True)

        if st.button("Overwrite current project with this file"):
            save_project_data_to_db(raw, project_id)
            st.success("Imported and saved to database.")
            st.experimental_rerun()   # reload UI with new data

    # ---------- always load latest tasks from DB ---------------------
    df_tasks = get_project_data_from_db(project_id)
    if df_tasks.empty:
        df_tasks = get_sample_data()
    df_tasks = guarantee_percent(df_tasks)

    st.subheader("1 · Editable Task Table")
    edited_df = st.data_editor(
        df_tasks,
        num_rows="dynamic",
        use_container_width=True,
        key="task_grid",
    )

    # ---------- save button ------------------------------------------
    if st.button("Save to DB & Re-calculate", type="primary"):
        edited_df = guarantee_percent(edited_df)
        edited_df["Percent Complete"] = (
            pd.to_numeric(edited_df["Percent Complete"], errors="coerce")
            .fillna(0)
            .clip(0, 100)
        )
        save_project_data_to_db(edited_df, project_id)
        st.success("Saved to database.")
        st.experimental_rerun()       # show fresh CPM & Gantt

    # ---------- CPM + charts (if tasks exist) ------------------------
    if not df_tasks.empty:
        cpm_df = calculate_cpm(df_tasks)

        st.subheader("2 · CPM Results")
        st.dataframe(cpm_df, use_container_width=True)

        st.subheader("3 · CPM Network Diagram")
        st.plotly_chart(create_network_figure(cpm_df), use_container_width=True)

        st.subheader("4 · Project Gantt Chart")
        st.plotly_chart(
            create_gantt_chart(cpm_df, start_date=start_date),
            use_container_width=True,
        )
