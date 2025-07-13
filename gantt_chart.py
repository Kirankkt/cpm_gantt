# gantt_chart.py  – v2 with dependencies & critical-path styling
import plotly.graph_objects as go
import pandas as pd

# Colour palette
STATUS_COLOURS = {
    "Finished":   "#4CAF50",   # green
    "In Progress":"#FFC107",   # amber
    "Not Started":"#2196F3",   # blue
}

def create_gantt_chart(
    df: pd.DataFrame,
    start_date="2025-01-01",
    progress_col: str | None = None,
) -> go.Figure:
    """
    df must already contain CPM results (ES, EF, LS, LF, Float, On Critical Path?).
    Required columns: Task ID, Task Description, Predecessors, Duration
    Optional column: progress_col (0-100) for percent complete.
    """
    project_start = pd.to_datetime(start_date)

    # 1 — prep bar endpoints
    gdf = df.copy()
    gdf["Start"]  = project_start + pd.to_timedelta(gdf["ES"] - 1, unit="D")
    gdf["Finish"] = project_start + pd.to_timedelta(gdf["EF"] - 1, unit="D")

    # 2 — figure skeleton
    fig = go.Figure()

    # 3 — draw task bars
    for idx, row in gdf.iterrows():
        colour = "red" if row["On Critical Path?"] == "Yes" else "#3F51B5"
        outline = "red" if row["On Critical Path?"] == "Yes" else colour
        fig.add_trace(
            go.Bar(
                x=[row["Duration"]],
                y=[row["Task Description"]],
                base=row["Start"],
                orientation="h",
                name=row["Task ID"],
                marker=dict(
                    color=colour,
                    line=dict(color=outline, width=1.5),
                ),
                hovertemplate=(
                    f"<b>{row['Task ID']} – {row['Task Description']}</b><br>"
                    f"Start: {row['Start']:%Y-%m-%d}<br>"
                    f"Finish: {row['Finish']:%Y-%m-%d}<br>"
                    f"Duration: {row['Duration']} days<br>"
                    f"Float: {row['Float']}<extra></extra>"
                ),
                showlegend=False,
            )
        )

        # 3a — progress overlay (optional)
        if progress_col and progress_col in gdf.columns:
            pct = row[progress_col] / 100.0
            if pct > 0:
                fig.add_trace(
                    go.Bar(
                        x=[row["Duration"] * pct],
                        y=[row["Task Description"]],
                        base=row["Start"],
                        orientation="h",
                        marker=dict(color="#9E9E9E"),
                        hoverinfo="skip",
                        showlegend=False,
                    )
                )

    # 4 — dependency arrows (Finish-to-Start only)
    arrows = []
    for _, row in gdf.iterrows():
        succ_start_x = row["Finish"]
        succ_start_y = row["Task Description"]
        preds = [p.strip() for p in str(row["Predecessors"]).split(",") if p.strip()]
        for p in preds:
            if p not in gdf["Task ID"].values:
                continue
            pred_y = gdf.loc[gdf["Task ID"] == p, "Task Description"].iloc[0]
            pred_x = gdf.loc[gdf["Task ID"] == p, "Finish"].iloc[0]

            arrows.append(
                dict(
                    type="line",
                    x0=pred_x,
                    y0=pred_y,
                    x1=row["Start"],
                    y1=succ_start_y,
                    line=dict(
                        color="red" if (
                            row["On Critical Path?"] == "Yes"
                            and gdf.loc[gdf['Task ID'] == p, 'On Critical Path?'].iloc[0] == "Yes"
                        ) else "#666",
                        width=2,
                    ),
                    arrowhead=2,
                    axref="x",
                    ayref="y",
                    xref="x",
                    yref="y",
                    layer="below",
                )
            )

    fig.update_layout(
        shapes=arrows,
        barmode="overlay",
        xaxis=dict(
            title="Timeline",
            tickformat="%b %d\n%Y",
            showgrid=True,
            gridcolor="#eee",
        ),
        yaxis=dict(autorange="reversed"),
        height=450 + 25 * len(gdf),
        margin=dict(l=20, r=20, t=40, b=40),
        title="Project Gantt Chart (with Dependencies)",
    )
    return fig
