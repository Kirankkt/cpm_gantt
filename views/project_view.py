import streamlit as st
import pandas as pd

from database import (
    get_project_data_from_db,
    save_project_data_to_db,
)
from cpm_logic import calculate_cpm
from utils import get_sample_data
from gantt_chart import create_gantt_chart
from network_diagram import create_network_figure


# ──────────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────────
def clean_task_df(raw: pd.DataFrame) -> pd.DataFrame:
    """Standardise column names, enforce types, drop blank rows."""
    df = raw.copy()
    df.columns = df.columns.str.strip()

    required = [
        "Task ID",
        "Task Description",
        "Predecessors",
        "Duration",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"Missing required column(s): {', '.join(missing)}")
        st.stop()

    df = df.dropna(how="all")

    df["Task ID"] = df["Task ID"].astype(str).str.strip()
    df = df[df["Task ID"] != ""]
    if df["Task ID"].duplicated().any():
        dups = df.loc[df["Task ID"].duplicated(), "Task ID"].unique()
        st.error(f"Duplicate Task ID(s): {', '.join(dups)}")
        st.stop()

    df["Duration"] = pd.to_numeric(df["Duration"], errors="coerce")
    bad_dur = df["Duration"].isna() | (df["Duration"] < 0)
    if bad_dur.any():
        bad_rows = ", ".join(df.loc[bad_dur, "Task ID"])
        st.error(f"Invalid Duration for task(s): {bad_rows}")
        st.stop()

    if "Start Date" not in df.columns:
        df["Start Date"] = None

    return df


def validate_predecessors(df: pd.DataFrame) -> None:
    """Ensure every predecessor ID exists in the Task-ID column."""
    ids = set(df["Task ID"])
    issues = {}
    for t_id, preds in zip(df["Task ID"], df["Predecessors"]):
        missing = [
            p.strip()
            for p in str(preds).split(",")
            if p.strip() and p.strip().lower() != "nan" and p.strip() not in ids
        ]
        if missing:
            issues[t_id] = missing

    if issues:
        msgs = [f"{k} → {', '.join(v)}" for k, v in issues.items()]
        st.error(
            "The following tasks reference predecessor IDs that do not "
            f"exist in the table:\n• " + "\n• ".join(msgs)
        )
        st.stop()



# ──────────────────────────────────────────────────────────────────────
#  Main view
# ──────────────────────────────────────────────────────────────────────
def show_project_view(project_id: int = 1) -> None:
    """Render the construction-schedule workspace."""
    st.header("1. Manage Construction Tasks")

    start_date = st.date_input(
        "Construction Start Date",
        value=pd.Timestamp("2025-01-01"),
    )

    # ── File upload ────────────────────────────────────────────────
    uploaded_file = st.file_uploader(
        "Import schedule (Excel .xlsx / .xls or CSV)",
        type=["csv", "xls", "xlsx"],
        help="Required columns: Task ID, Task Description, Predecessors, Duration",
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
            # simple CSV backup before destructive write
            current = get_project_data_from_db(project_id)
            if not current.empty:
                ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
                current.to_csv(f"backup_project{project_id}_{ts}.csv", index=False)
            save_project_data_to_db(cleaned, project_id=project_id)
            st.success("Imported and saved to database.")

    # ── Editable grid ──────────────────────────────────────────────
    df_tasks = get_project_data_from_db(project_id)
    if df_tasks.empty:
        df_tasks = get_sample_data()

    edited_df = st.data_editor(
        df_tasks,
        use_container_width=True,
        num_rows="dynamic",
        key="task_editor",
    )

    # ── Save + CPM --------------------------------------------------
    if st.button("Save Schedule and Calculate Critical Path", type="primary"):
        save_project_data_to_db(edited_df, project_id=project_id)

        cpm_df = calculate_cpm(edited_df)
        st.subheader("2. CPM Results")
        st.dataframe(cpm_df, use_container_width=True)

        st.subheader("3. CPM Network Diagram")
        net_fig = create_network_figure(cpm_df)
        st.plotly_chart(net_fig, use_container_width=True)

        st.subheader("4. Project Gantt Chart")
        gantt_fig = create_gantt_chart(cpm_df, start_date=start_date)
        st.plotly_chart(gantt_fig, use_container_width=True)
