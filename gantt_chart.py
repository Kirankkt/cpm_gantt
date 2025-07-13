"""
Gantt chart (Plotly Express timeline base)

• Blue bars, red outline if critical
• Grey inner bar = % complete (optional)
• Milestones (0-duration) drawn as diamonds
• Finish-to-Start arrows with arrowheads
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def create_gantt_chart(
    df: pd.DataFrame,
    start_date="2025-01-01",
    progress_col: str | None = None,
) -> go.Figure:
    # ------------------------------------------------------------------ #
    #  0. Prep dates & helper flags                                       #
    # ------------------------------------------------------------------ #
    anchor = pd.to_datetime(start_date)

    gdf = df.copy()
    gdf["Start"] = anchor + pd.to_timedelta(gdf["ES"] - 1, unit="D")
    gdf["Finish"] = anchor + pd.to_timedelta(gdf["EF"] - 1, unit="D")
    gdf["IsMilestone"] = gdf["Duration"].astype(float).lt(0.01)
    gdf["IsCritical"] = gdf["On Critical Path?"].eq("Yes")

    # ------------------------------------------------------------------ #
    #  1. Main bars via px.timeline                                       #
    # ------------------------------------------------------------------ #
    bar_df = gdf.loc[~gdf["IsMilestone"]].copy()

    fig = px.timeline(
        bar_df,
        x_start="Start",
        x_end="Finish",
        y="Task Description",
        color_discrete_sequence=["#3F51B5"],
    )

    # -- red outline for critical tasks
    for trace, iscrit in zip(fig.data, bar_df["IsCritical"]):
        if iscrit:
            trace.update(marker=dict(line=dict(color="red", width=2)))

    # ------------------------------------------------------------------ #
    #  2. Progress overlay                                                #
    # ------------------------------------------------------------------ #
    if progress_col and progress_col in gdf.columns:
        shapes = []
        for r in bar_df.itertuples():
            pct = max(0, min(100, getattr(r, progress_col))) / 100
            if pct == 0:
                continue
            shapes.append(
                dict(
                    type="rect",
                    xref="x", yref="y",
                    x0=r.Start,
                    x1=r.Start + (r.Finish - r.Start) * pct,
                    y0=r._asdict()["Task Description"] + ":bottom",
                    y1=r._asdict()["Task Description"] + ":top",
                    fillcolor="#9E9E9E",
                    line_width=0,
                    opacity=0.6,
                    layer="below",
                )
            )
        if shapes:
            fig.update_layout(shapes=shapes)

    # ------------------------------------------------------------------ #
    #  3. Milestone diamonds                                              #
    # ------------------------------------------------------------------ #
    mile_df = gdf.loc[gdf["IsMilestone"]]
    if not mile_df.empty:
        fig.add_trace(
            go.Scatter(
                x=mile_df["Start"],
                y=mile_df["Task Description"],
                mode="markers",
                marker=dict(
                    symbol="diamond-wide",
                    size=14,
                    color=["red" if c else "#3F51B5" for c in mile_df["IsCritical"]],
                ),
                hovertext=mile_df["Task ID"] + " – " + mile_df["Task Description"],
                hoverinfo="text",
                showlegend=False,
            )
        )

    # ------------------------------------------------------------------ #
    #  4. FS dependency arrows                                            #
    # ------------------------------------------------------------------ #
    annotations = []
    id_to_row = gdf.set_index("Task ID")

    for _, succ in gdf.iterrows():
        succ_y   = succ["Task Description"]
        succ_x   = succ["Start"]
        succ_crit = succ["IsCritical"]

        for p in str(succ["Predecessors"]).split(","):
            p = p.strip()
            if not p or p not in id_to_row.index:
                continue
            pred = id_to_row.loc[p]
            color = "red" if (pred["IsCritical"] and succ_crit) else "#666"

            annotations.append(
                dict(
                    x=succ_x, y=succ_y,
                    ax=pred["Finish"], ay=pred["Task Description"],
                    xref="x", yref="y", axref="x", ayref="y",
                    showarrow=True, arrowhead=3, arrowsize=1, arrowwidth=2,
                    arrowcolor=color,
                )
            )



    # ------------------------------------------------------------------ #
    #  5. Layout                                                         #
    # ------------------------------------------------------------------ #
    fig.update_layout(
        annotations=annotations,
        xaxis=dict(title="Timeline",
                   tickformat="%b %d\n%Y",
                   showgrid=True, gridcolor="#EEE"),
        yaxis=dict(autorange="reversed"),
        title="Project Gantt Chart",
        height=400 + 24 * len(gdf),
        margin=dict(l=20, r=20, t=40, b=40),
        showlegend=False,
    )
    return fig
