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


# ───────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────
REQUIRED = ["Task ID", "Task Description", "Predecessors", "Duration"]


def ensure_percent(df: pd.DataFrame) -> pd.DataFrame:
    if "Percent Complete" not in df.columns:
        df["Percent Complete"] = 0
    return df


def clean_upload(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df.columns = df.columns.str.strip()

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        st.error("Missing column(s): " + ", ".join(missing))
        st.stop()

    df = df.dropna(how="all")
    df["Task ID"] = df["Task ID"].astype(str).str.strip()
    if df["Task ID"].eq("").any() or df["Task ID"].duplicated().any():
        st.error("Blank or duplicate Task IDs detected.")
        st.stop()

    df["Duration"] = pd.to_numeric(df["Duration"], errors="coerce")
    if df["Duration"].isna().any() or (df["Duration"] < 0).any():
        st.error("Duration must be numeric and ≥ 0.")
        st.stop()

    if "Start Date" not in df.columns:
        df["Start Date"] = None
    return ensure_percent(df)


def check_predecessors(df: pd.DataFrame) -> None:
    ids = set(df["Task ID"])
    bad = []
    for tid, preds in zip(df["Task ID"], df["Predecessors"]):
        for p in str(preds).split(","):
            p = p.strip()
            if p and p not in ids:
                bad.append(f"{tid} → {p}")
    if bad:
        st.error(
            "Predecessor references to non-existent IDs:\n• "
            + "\n• ".join(bad)
        )
        st.stop()


# ───────────────────────────────────────────────────────────────
# Main view
# ───────────────────────────────────────────────────────────────
def show_project_view(project_id: int = 1) -> None:
    st.header("1 · Manage Construction Tasks")

    start_date = st.date_input(
        "Construction Start Date", value=pd.Timestamp("2025-01-01")
    )

    # ── Optional file import ─────────────────────────────────────
    up = st.file_uploader(
        "Import schedule (Excel or CSV)",
        type=["csv", "xls", "xlsx"],
        help="Required columns: " + ", ".join(REQUIRED),
    )

    if up is not None:
        raw = (
            pd.read_excel(up)
            if up.name.lower().endswith(("xls", "xlsx"))
            else pd.read_csv(up)
        )
        cleaned = clean_upload(raw)
        check_predecessors(cleaned)

        st.info("Preview of uploaded data:")
        st.dataframe(cleaned, use_container_width=True)

        if st.button("Overwrite project with this file", key="import_btn"):
            save_project_data_to_db(cleaned, project_id)
            st.success("Imported and saved to database.")
            st.rerun()              # reload UI with new data

    # ── Always load current tasks from DB (or sample) ────────────
    df_tasks = get_project_data_from_db(project_id)
    if df_tasks.empty:
        df_tasks = get_sample_data()
    df_tasks = ensure_percent(df_tasks)

    st.subheader("Editable Task Table")
    edited_df = st.data_editor(
        df_tasks,
        use_container_width=True,
        num_rows="dynamic",
        key="task_grid",
    )

    # —— Save button ————————————————————————————————
    if st.button("Save to DB + Re-calculate", type="primary", key="save_btn"):
        edited_df = ensure_percent(edited_df)
        edited_df["Percent Complete"] = (
            pd.to_numeric(edited_df["Percent Complete"], errors="coerce")
            .fillna(0)
            .clip(0, 100)
        )
        save_project_data_to_db(edited_df, project_id)
        st.success("Saved!")
        st.rerun()                  # load fresh data + charts

    # —— Display CPM & charts if DB has tasks —————————————
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
