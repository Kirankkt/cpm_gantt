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


# ───────────────────────── helpers ───────────────────────────────
def guarantee_percent(df: pd.DataFrame) -> pd.DataFrame:
    if "Percent Complete" not in df.columns:
        df["Percent Complete"] = 0
    return df


def validate_predecessors(df: pd.DataFrame) -> list[str]:
    ids = set(df["Task ID"])
    bad_links: list[str] = []
    for tid, preds in zip(df["Task ID"], df["Predecessors"]):
        for p in str(preds).split(","):
            p = p.strip()
            if p and p not in ids:
                bad_links.append(f"{tid} → {p}")
    return bad_links


# ───────────────────────── main view ─────────────────────────────
def show_project_view(project_id: int = 1) -> None:
    st.header("🏗️ Collaborative Renovation Project Hub")

    start_date = st.date_input(
        "Construction Start Date", value=pd.Timestamp("2025-01-01")
    )

    # ---- 1 · load latest tasks from DB on every run --------------
    db_df = get_project_data_from_db(project_id)
    if db_df.empty:
        db_df = get_sample_data()
    db_df = guarantee_percent(db_df)

    # initialise working copy once per session
    if "grid_df" not in st.session_state:
        st.session_state["grid_df"] = db_df.copy()

    # ---- 2 · editable grid (widget manages its own key) ----------
    st.subheader("1 · Editable Task Table")
    edited_df = st.data_editor(
        st.session_state["grid_df"],
        use_container_width=True,
        num_rows="dynamic",
        key="task_editor",        # widget key (never written to)
    )

    # keep working copy in sync on every rerun
    st.session_state["grid_df"] = edited_df.copy()

    # ---- 3 · save button -----------------------------------------
    if st.button("💾 Save to DB & Re-calculate", type="primary"):
        save_df = guarantee_percent(pd.DataFrame(st.session_state["grid_df"]))
        save_df["Percent Complete"] = (
            pd.to_numeric(save_df["Percent Complete"], errors="coerce")
            .fillna(0)
            .clip(0, 100)
        )

        # validate predecessors
        bad_links = validate_predecessors(save_df)
        if bad_links:
            st.error(
                "Predecessor references to non-existent IDs:\n• "
                + "\n• ".join(bad_links)
            )
            st.stop()

        save_project_data_to_db(save_df, project_id)
        st.success("Saved to database.")

        # refresh session cache from canonical DB copy
        st.session_state["grid_df"] = save_df.copy()

    # ---- 4 · build CPM & charts from working copy ----------------
    view_df = pd.DataFrame(st.session_state["grid_df"])
    if not view_df.empty:
        cpm_df = calculate_cpm(view_df)

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
