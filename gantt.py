# gantt.py
import plotly.express as px
import pandas as pd

def create_gantt_chart(df):
    """
    Creates an interactive Gantt chart using Plotly.
    """
    # Plotly expects dates, so we'll create start and end dates from our day numbers
    # We'll use a dummy start date for the project
    project_start_date = pd.to_datetime('2025-01-01')

    df_gantt = df.copy()
    df_gantt['start'] = project_start_date + pd.to_timedelta(df_gantt['ES'] - 1, unit='D')
    df_gantt['finish'] = project_start_date + pd.to_timedelta(df_gantt['EF'] - 1, unit='D')

    fig = px.timeline(
        df_gantt,
        x_start="start",
        x_end="finish",
        y="Task Description",
        color="On Critical Path?",
        hover_data=['Task ID', 'Duration', 'ES', 'EF', 'LS', 'LF', 'Float'],
        color_discrete_map={"Yes": "red", "No": "blue"},
        title="Project Timeline (Gantt Chart)"
    )

    fig.update_yaxes(autorange="reversed") # To display tasks from top to bottom
    fig.update_layout(
        xaxis_title="Timeline",
        yaxis_title="Tasks",
        font=dict(size=12)
    )

    return fig