"""
Enhanced Plotly Gantt chart

• Bar colour reflects status (done / in-progress / not-started)
• Critical-path tasks outlined *and* filled red
• % complete label over each bar
• Today line, weekend shading, weekly grid
• Milestone diamonds
• Arrow-headed Finish-to-Start connectors
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# ──────────────────────────────────────────────────────────────────────
#  Palette helpers
# ──────────────────────────────────────────────────────────────────────
COLORS = {
    "done":        "#4CAF50",
    "progress":    "#FF9800",
    "notstarted":  "#3F51B5",
    "critical":    "#E53935",
}


def _status_colour(pct: float | None, critical: bool) -> str:
    if critical:
        return COLORS["critical"]
    if pct is None:
        return COLORS["notstarted"]
    if pct >= 100:
        return COLORS["done"]
    if pct > 0:
        return COLORS["progress"]
    return COLORS["notstarted"]


# ──────────────────────────────────────────────────────────────────────
#  Main entry point
# ──────────────────────────────────────────────────────────────────────
def create_gantt_chart(
    df: pd.DataFrame,
    start_date="2025-01-01",
    progress_col: str = "Percent Complete",
) -> go.Figure:
    anchor = pd.to_datetime(start_date)

    gdf = df.copy()
    gdf["Start"]  = anchor + pd.to_timedelta(gdf["ES"] - 1, unit="D")
    gdf["Finish"] = anchor + pd.to_timedelta(gdf["EF"] - 1, unit="D")
    gdf["IsMilestone"] = gdf["Duration"].astype(float).lt(0.01)
    gdf["IsCritical"]  = gdf["On Critical Path?"].eq("Yes")
    if progress_col not in gdf.columns:
        gdf[progress_col] = 0

    # -- colour per row
    gdf["_colour"] = [
        _status_colour(p, crit)
        for p, crit in zip(gdf[progress_col], gdf["IsCritical"])
    ]

    # ── 1. Bars via px.timeline ─────────────────────────────────────
    bars = gdf.loc[~gdf["IsMilestone"]]
    fig = px.timeline(
        bars,
        x_start="Start",
        x_end="Finish",
        y="Task Description",
        color="_colour",
        color_discrete_map="identity",
    )

    # outline critical
    for trace, crit in zip(fig.data, bars["IsCritical"]):
        if crit:
            trace.update(marker=dict(line=dict(color="red", width=2)))

    # % label
    for trace, pct in zip(fig.data, bars[progress_col]):
        text = f"{pct:.0f} %" if pct else ""
        trace.update(text=[text], textposition="inside", textfont_color="white")

    # ── 2. Milestones ───────────────────────────────────────────────
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
                        COLORS["critical"] if c else COLORS["notstarted"]
                        for c in mile_df["IsCritical"]
                    ],
                    line=dict(width=1, color="black"),
                ),
                hovertext=mile_df["Task ID"] + " – " + mile_df["Task Description"],
                hoverinfo="text",
                showlegend=False,
            )
        )

    # ── 3. FS arrows ────────────────────────────────────────────────
    ann = []
    id_to_row = gdf.set_index("Task ID")
    for _, succ in gdf.iterrows():
        succ_y = succ["Task Description"]
        succ_x = succ["Start"]
        for p in str(succ["Predecessors"]).split(","):
            p = p.strip()
            if not p or p not in id_to_row.index:
                continue
            pred = id_to_row.loc[p]
            colour = (
                COLORS["critical"]
                if pred["IsCritical"] and succ["IsCritical"]
                else "#666"
            )
            ann.append(
                dict(
                    x=succ_x,
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
                    arrowcolor=colour,
                )
            )

    # ── 4. Weekend shading & today line ─────────────────────────────
    shapes = []
    # weekend stripes
    cal = pd.date_range(gdf["Start"].min(), gdf["Finish"].max(), freq="D")
    for d in cal:
        if d.weekday() >= 5:  # Saturday/Sunday
            shapes.append(
                dict(
                    type="rect",
                    xref="x",
                    yref="paper",
                    x0=d,
                    x1=d + pd.Timedelta(days=1),
                    y0=0,
                    y1=1,
                    fillcolor="#F9F9F9",
                    line_width=0,
                    layer="below",
                )
            )
    # today line
    today = pd.Timestamp.today().normalize()
    shapes.append(
        dict(
            type="line",
            xref="x",
            yref="paper",
            x0=today,
            x1=today,
            y0=0,
            y1=1,
            line=dict(color="black", width=1, dash="dash"),
        )
    )

    # ── 5. Layout polish ────────────────────────────────────────────
    fig.update_layout(
        annotations=ann,
        shapes=shapes,
        title="Project Gantt Chart",
        height=500 + 22 * len(gdf),
        margin=dict(l=120, r=40, t=50, b=40),
        legend_title="Task Status",
        xaxis=dict(
            title="Timeline",
            tickformat="%b %d\n%Y",
            showgrid=True,
            gridcolor="#ECECEC",
        ),
        yaxis=dict(autorange="reversed"),
    )

    # custom legend entries
    for name, col in [
        ("Not started", COLORS["notstarted"]),
        ("In progress", COLORS["progress"]),
        ("Done", COLORS["done"]),
        ("Critical path", COLORS["critical"]),
    ]:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color=col),
                legendgroup=name,
                showlegend=True,
                name=name,
            )
        )

    return fig
