"""
Gantt chart (Plotly Express timeline base)

• Blue bars, red outline if on critical path
• Grey inner bar shows % complete (if column supplied)
• Zero-duration tasks become diamonds
• FS dependency arrows with arrowheads
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def create_gantt_chart(
    df: pd.DataFrame,
    start_date="2025-01-01",
    progress_col: str | None = None,
) -> go.Figure:
    anchor = pd.to_datetime(start_date)
    gdf = df.copy()

    # Real calendar dates for plotting
    gdf["Start"]  = anchor + pd.to_timedelta(gdf["ES"] - 1, unit="D")
    gdf["Finish"] = anchor + pd.to_timedelta(gdf["EF"] - 1, unit="D")
    gdf["IsMilestone"] = gdf["Duration"].astype(float).lt(0.01)

    # 1 — main bars via px.timeline
    bar_df = gdf.loc[~gdf["IsMilestone"]].copy()
    fig = px.timeline(
        bar_df,
        x_start="Start",
        x_end="Finish",
        y="Task Description",
        color_discrete_sequence=["#3F51B5"],
    )

    # 1a — critical outline
    for d, row in zip(fig.data, bar_df.itertuples()):
        if row._asdict()["On Critical Path?"] == "Yes":
            d.update(marker=dict(line=dict(color="red", width=2)))

    # 2 — progress overlay
    if progress_col and progress_col in gdf.columns:
        prog_shapes = []
        for r in bar_df.itertuples():
            pct = max(0, min(100, getattr(r, progress_col))) / 100
            if pct == 0:
                continue
            prog_shapes.append(
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
        fig.update_layout(shapes=prog_shapes)

    # 3 — milestone diamonds
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
                    color=[
                        "red" if c == "Yes" else "#3F51B5"
                        for c in mile_df["On Critical Path?"]
                    ],
                ),
                hovertext=(
                    mile_df["Task ID"] + " – " + mile_df["Task Description"]
                ),
                hoverinfo="text",
                showlegend=False,
            )
        )

    # 4 — FS arrows
    ann = []
    for r in gdf.itertuples():
        succ_y = r._asdict()["Task Description"]
        for p in str(r.Predecessors).split(","):
            p = p.strip()
            if not p or p not in gdf["Task ID"].values:
                continue
            pred = gdf.loc[gdf["Task ID"] == p].iloc[0]
            color = (
                "red"
                if pred["On Critical Path?"] == "Yes"
                and r._asdict()["On Critical Path?"] == "Yes"
                else "#666"
            )
            ann.append(
                dict(
                    x=r.Start,
                    y=succ_y,
                    ax=pred["Finish"],
                    ay=pred["Task Description"],
                    xref="x",
                    yref="y",
                    axref="x",
                    ayref="y",
                    showarrow=True,
                    arrowhead=3,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor=color,
                )
            )
    fig.update_layout(annotations=ann)

    # 5 — general layout polish
    fig.update_layout(
        xaxis=dict(
            title="Timeline",
            tickformat="%b %d\n%Y",
            showgrid=True,
            gridcolor="#EEE",
        ),
        yaxis=dict(autorange="reversed"),
        title="Project Gantt Chart",
        height=400 + 24 * len(gdf),
        margin=dict(l=20, r=20, t=40, b=40),
        showlegend=False,
    )
    return fig
