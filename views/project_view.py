import streamlit as st
import pandas as pd
from io import StringIO
from database import get_project_data_from_db, save_project_data_to_db, import_df_to_db
from cpm_logic import calculate_cpm
from gantt import create_gantt_chart
from utils import get_sample_data

def show_project_view():
    """
    Displays the UI for managing tasks, calculating CPM, and viewing the Gantt chart.
    Now includes Import and Export functionality.
    """
    st.header("1. Manage Your Project Tasks")
    # Allow the user to specify the project's start date
    start_date = st.date_input(
        "Select Project Start Date",
        value=pd.to_datetime("2025-01-01").date(),
        key="project_start_date"
    )

    # --- NEW: IMPORT SECTION ---
    with st.expander("Import Project from CSV File"):
        uploaded_file = st.file_uploader(
            "Choose a CSV file to upload. This will overwrite the current project.",
            type=['csv']
        )
        if uploaded_file is not None:
            try:
                # Read the uploaded file as a DataFrame
                stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
                uploaded_df = pd.read_csv(stringio)
                
                # Use our new database function to import the data
                import_df_to_db(uploaded_df)
                st.success("File imported successfully! The task list below has been updated.")
                # We add a button to let the user clear the uploader and prevent re-uploading
                st.button("Clear Uploaded File", on_click=lambda: st.experimental_rerun())
            except Exception as e:
                st.error(f"Error processing file: {e}")
    # --- END OF NEW SECTION ---

    # Load data from database
    try:
        project_df = get_project_data_from_db()
        if project_df.empty:
            st.info("Your project is empty. Using sample data. Modify it or upload a new file.")
            project_df = get_sample_data()
    except Exception as e:
        st.error(f"Could not load data. Error: {e}")
        project_df = pd.DataFrame() # Start with an empty df on error
    
    st.caption("Edit data in the table below. When done, click 'Save and Calculate'.")
    edited_df = st.data_editor(
        project_df,
        num_rows="dynamic",
        use_container_width=True,
        key="data_editor" # Assign a key to maintain state
    )

    if st.button("Save and Calculate Critical Path", type="primary"):
        if edited_df.empty:
            st.warning("Cannot calculate an empty project. Please add tasks or upload a file.")
        elif 'Duration' not in edited_df.columns or edited_df['Duration'].isnull().any() or not pd.api.types.is_numeric_dtype(edited_df['Duration']):
            st.error("Please ensure all tasks have a valid numeric Duration.")
        elif 'Task ID' not in edited_df.columns or edited_df['Task ID'].isnull().any():
            st.error("Please ensure every task has a 'Task ID'.")
        else:
            with st.spinner("Saving and calculating..."):
                edited_df['Predecessors'] = edited_df['Predecessors'].astype(str).fillna('')
                save_project_data_to_db(edited_df)
                st.success("Project data has been saved!")

                result_df = calculate_cpm(edited_df)
                st.session_state.result_df = result_df # Save result to session state for download

                st.header("2. CPM Analysis Results")
                st.dataframe(result_df, use_container_width=True)

                st.header("3. Project Summary")
                col1, col2 = st.columns(2)
                project_duration = result_df['EF'].max()
                col1.metric("Total Project Duration (days)", f"{project_duration:.0f}")
                critical_path_tasks = result_df[result_df['On Critical Path?'] == 'Yes']['Task ID'].tolist()
                col2.metric("Number of Critical Tasks", len(critical_path_tasks))
                st.info(f"**Critical Path:** {' → '.join(critical_path_tasks)}")

                st.header("4. Project Gantt Chart")
                gantt_fig = create_gantt_chart(result_df, start_date=start_date)
                st.plotly_chart(gantt_fig, use_container_width=True)

    # --- NEW: DOWNLOAD SECTION ---
    # Check if results exist in the session state before showing the button
    if 'result_df' in st.session_state:
        st.header("5. Export Results")
        # Convert DataFrame to CSV format in memory
        csv_export = st.session_state.result_df.to_csv(index=False).encode('utf-8')
        st.download_button(
           label="Download Full Schedule as CSV",
           data=csv_export,
           file_name='cpm_project_schedule.csv',
           mime='text/csv',
        )
    # --- END OF NEW SECTION ---
