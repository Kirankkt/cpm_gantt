import streamlit as st
import pandas as pd
from gantt_chart import create_gantt_chart
from database import get_project_data_from_db, save_project_data_to_db
from cpm_logic import calculate_cpm
from utils import get_sample_data
from network_diagram import create_network_figure



def show_project_view(project_id: int = 1) -> None:
    """Render the main construction-schedule workspace."""
    st.header("1. Manage Construction Tasks")

    start_date = st.date_input("Construction Start Date", value=pd.Timestamp("2025-01-01"))

    # ------------------------------------------------------------------ #
    #  File upload: Excel OR CSV                                         #
    # ------------------------------------------------------------------ #
    uploaded_file = st.file_uploader(
        "Import schedule (Excel .xlsx / .xls or CSV)",
        type=["csv", "xls", "xlsx"],
        help=(
            "Required columns ➜ Task ID, Task Description, "
            "Predecessors, Duration, Start Date"
        ),
    )

    if uploaded_file is not None:
        import_df = (
            pd.read_excel(uploaded_file)
            if uploaded_file.name.lower().endswith(("xls", "xlsx"))
            else pd.read_csv(uploaded_file)
        )
        save_project_data_to_db(import_df, project_id=project_id)
        st.success(
            f"Imported {len(import_df)} tasks. "
            "Press **Save Schedule and Calculate Critical Path** below."
        )

    # ------------------------------------------------------------------ #
    #  Load tasks (DB → editable grid)                                   #
    # ------------------------------------------------------------------ #
    df_tasks = get_project_data_from_db(project_id=project_id)
    if df_tasks.empty:
        df_tasks = get_sample_data()

    edited_df = st.data_editor(
        df_tasks,
        use_container_width=True,
        num_rows="dynamic",
        key="task_editor",
    )


    # ------------------------------------------------------------------ #
    #  Save + CPM + Gantt                                                #
    # ------------------------------------------------------------------ #
    if st.button("Save Schedule and Calculate Critical Path", type="primary"):
        save_project_data_to_db(edited_df, project_id=project_id)

        cpm_df = calculate_cpm(edited_df)
        st.subheader("2. CPM Results")
        st.dataframe(cpm_df, use_container_width=True)

        st.subheader("3. CPM Network Diagram")
        net_fig = create_network_figure(cpm_df)
        st.plotly_chart(net_fig, use_container_width=True)

        st.subheader("4. Project Gantt Chart")
        fig = create_gantt_chart(cpm_df, start_date=start_date)
        st.plotly_chart(fig, use_container_width=True)

        

