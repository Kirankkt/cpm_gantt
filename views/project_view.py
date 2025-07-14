# views/project_view.py
# ==============================================================
# Streamlit “Construction Hub” main workspace
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
REQUIRED_COLS = ["Task ID", "Task Description", "Predecessors", "Duration"]


def ensure_percent_column(df: pd.DataFrame) -> pd.DataFrame:
    """Guarantee a `Percent Complete` column (0 – 100)."""
    if "Percent Complete" not in df.columns:
        df["Percent Complete"] = 0
    return df


def clean_task_df(raw: pd.DataFrame) -> pd.DataFrame:
    """Standardise headers, enforce types, add missing cols."""
    df = raw.copy()
    df.columns = df.columns.str.strip()

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        st.error(f"Uploaded file is missing column(s): {', '.join(missing)}")
        st.stop()

    df = df.dropna(how="all")                      # drop blank rows
    df["Task ID"] = df["Task ID"].astype(str).str.strip()
    df = df[df["Task ID"] != ""]                   # no empty IDs

    # Duplicate IDs?
    if df["Task ID"].duplicated().any():
        dups = ", ".join(df.loc[df["Task ID"].duplicated(), "Task ID"].unique())
        st.error(f"Duplicate Task ID(s): {dups}")
        st.stop()

    # Duration must be numeric & ≥0
    df["Duration"] = pd.to_numeric(df["Duration"], errors="coerce")
    bad = df["Duration"].isna() | (df["Duration"] < 0)
    if bad.any():
        st.error(
            "Invalid Duration for task(s): "
            + ", ".join(df.loc[bad, "Task ID"])
        )
        st.stop()

    # Optional columns
    if "Start Date" not in df.columns:
        df["Start Date"] = None

    df = ensure_percent_column(df)
    return df


def validate_predecessors(df: pd.DataFrame) -> None:
    """Ensure every predecessor ID exists in the Task-ID column."""
    ids = set(df["Task ID"])
    issues: dict[str, list[str]] = {}

    for t_id, preds in zip(df["Task ID"], df["Predecessors"]):
        bad_refs = [
            p.strip()
            for p in str(preds).split(",")
            if p.strip() and p.strip() not in ids
        ]
        if bad_refs:
            issues[t_id] = bad_refs

    if issues:
        msg_lines = [f"{k} → {', '.join(v)}" for k, v in issues.items()]
        st.error(
            "The following tasks reference predecessor IDs that do not exist:\n• "
            + "\n• ".join(msg_lines)
        )
        st.stop()


# ───────────────────────────────────────────────────────────────
# Main Streamlit page
# ───────────────────────────────────────────────────────────────
def show_project_view(project_id: int = 1) -> None:
    """Render the schedule-management UI."""
    st.header("1. Manage Construction Tasks")

    start_date = st.date_input(
        "Construction Start Date", value=pd.Timestamp("2025-01-01")
    )

    # ── File uploader (optional import) ──────────────────────────
    uploaded_file = st.file_uploader(
        "Import schedule (Excel .xlsx / .xls or CSV)",
        type=["csv", "xls", "xlsx"],
        help="Required columns: " + ", ".join(REQUIRED_COLS),
    )

    if uploaded_file is not None:
        raw_df = (
            pd.read_excel(uploaded_file)
            if uploaded_file.name.lower().endswith(("xls", "xlsx"))
            else pd.read_csv(uploaded_file)
        )

        cleaned = clean_task_df(raw_df)
        validate_predecessors(cleaned)

        st.info("Preview of uploaded data:")
        st.dataframe(cleaned.head(), use_container_width=True)

        if st.checkbox("Overwrite existing schedule with this file?"):
            # simple CSV backup of current data
            current = get_project_data_from_db(project_id)
            if not current.empty:
                ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
                current.to_csv(
                    f"backup_project{project_id}_{ts}.csv", index=False
                )
            save_project_data_to_db(cleaned, project_id=project_id)
            st.success("Imported and saved to database.")

    # ── Load current tasks for editing ───────────────────────────
    df_tasks = get_project_data_from_db(project_id)
    if df_tasks.empty:
        df_tasks = get_sample_data()
    df_tasks = ensure_percent_column(df_tasks)

    # ── Editable grid + Save button (single form) ────────────────
    with st.form(key="schedule_form", clear_on_submit=False):
        edited_df = st.data_editor(
            df_tasks,
            use_container_width=True,
            num_rows="dynamic",
            key="task_editor",
        )
        submitted = st.form_submit_button(
            "Save Schedule and Calculate Critical Path",
            type="primary",
        )

    # ── Run CPM + graphics when user clicks button ───────────────
    if submitted:
        edited_df = ensure_percent_column(edited_df)
        edited_df["Percent Complete"] = (
            pd.to_numeric(edited_df["Percent Complete"], errors="coerce")
            .fillna(0)
            .clip(0, 100)
        )

        save_project_data_to_db(edited_df, project_id=project_id)

        cpm_df = calculate_cpm(edited_df)
        st.subheader("2. CPM Results")
        st.dataframe(cpm_df, use_container_width=True)

        st.subheader("3. CPM Network Diagram")
        st.plotly_chart(
            create_network_figure(cpm_df), use_container_width=True
        )

        st.subheader("4. Project Gantt Chart")
        st.plotly_chart(
            create_gantt_chart(cpm_df, start_date=start_date),
            use_container_width=True,
        )
