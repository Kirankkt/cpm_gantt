"""
Gantt chart generator (v3)
• Bars = tasks (red outline = critical)
• Grey overlay = % complete  (optional)
• Finish-to-Start arrows drawn with Plotly annotations
"""

import pandas as pd
import plotly.graph_objects as go


def create_gantt_chart(
    df: pd.DataFrame,
    start_date: str | pd.Timestamp = "2025-01-01",
    progress_col: str | None = None,
) -> go.Figure:
    """
    Parameters
    ----------
    df : DataFrame
        Must already contain CPM results:
        ES, EF, Duration, Float, On Critical Path?, Predecessors, Task ID, Task Description
    start_date : str | Timestamp
        Project anchor date used to translate ES/EF numbers to real dates.
    progress_col : str | None
        Name of a 0-100 numeric column for percent complete.  If None, no overlay shown.
    """
    anchor = pd.to_datetime(start_date)

    gdf = df.copy()
    gdf["Start"] = anchor + pd.to_timedelta(gdf["ES"] - 1, unit="D")
    gdf["Finish"] = anchor + pd.to_timedelta(gdf["EF"] - 1, unit="D")

    fig = go.Figure()

    # ------------------------------------------------------------------ #
    #  1. Task bars (blue or critical red outline)                       #
    # ------------------------------------------------------------------ #
    for _, row in gdf.iterrows():
        bar_color = "#3F51B5"
        outline   = "red" if row["On Critical Path?"] == "Yes" else bar_color

        fig.add_trace(
            go.Bar(
                x=[row["Duration"]],
                y=[row["Task Description"]],
                base=row["Start"],
                orientation="h",
                name=row["Task ID"],
                marker=dict(color=bar_color, line=dict(color=outline, width=1.5)),
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

        # Optional grey overlay for % complete
        if progress_col and progress_col in gdf.columns:
            pct = max(0, min(100, row[progress_col])) / 100
            if pct:
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

    # ------------------------------------------------------------------ #
    #  2. Dependency arrows (Finish-to-Start)                            #
    # ------------------------------------------------------------------ #
    annotations: list[dict] = []
    for _, row in gdf.iterrows():
        succ_start = row["Start"]
        succ_y     = row["Task Description"]
        preds = [p.strip() for p in str(row["Predecessors"]).split(",") if p.strip()]

        for p in preds:
            if p not in gdf["Task ID"].values:
                continue
            pred_row   = gdf[gdf["Task ID"] == p].iloc[0]
            pred_finish = pred_row["Finish"]
            pred_y      = pred_row["Task Description"]

            is_crit = (row["On Critical Path?"] == "Yes"
                       and pred_row["On Critical Path?"] == "Yes")

            annotations.append(
                dict(
                    x=succ_start,
                    y=succ_y,
                    ax=pred_finish,
                    ay=pred_y,
                    xref="x", yref="y",
                    axref="x", ayref="y",
                    showarrow=True,
                    arrowhead=3,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor="red" if is_crit else "#666",
                    opacity=0.8,
                )
            )

    # ------------------------------------------------------------------ #
    #  3. Layout                                                         #
    # ------------------------------------------------------------------ #
    fig.update_layout(
        annotations=annotations,
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
