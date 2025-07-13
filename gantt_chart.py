import plotly.express as px
import pandas as pd


def create_gantt_chart(df: pd.DataFrame, start_date="2025-01-01"):
    """Return a Plotly Gantt figure with the critical path highlighted."""
    project_start = pd.to_datetime(start_date)

    _df = df.copy()
    _df["start"]  = project_start + pd.to_timedelta(_df["ES"] - 1, unit="D")
    _df["finish"] = project_start + pd.to_timedelta(_df["EF"] - 1, unit="D")

    fig = px.timeline(
        _df,
        x_start="start",
        x_end="finish",
        y="Task Description",
        color="On Critical Path?",
        hover_data=["Task ID", "Duration", "ES", "EF", "LS", "LF", "Float"],
        color_discrete_map={"Yes": "red", "No": "blue"},
        title="Project Timeline (Gantt Chart)",
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(xaxis_title="Timeline", yaxis_title="Tasks", font=dict(size=12))
    return fig
