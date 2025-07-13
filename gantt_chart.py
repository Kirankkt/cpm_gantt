"""
Plotly Gantt with:
• Blue bars (red outline if critical)
• Grey overlay = % complete (optional)
• Milestones: any zero-duration task is shown as a diamond
• FS dependency connectors with arrowheads
"""

import pandas as pd
import plotly.graph_objects as go


def create_gantt_chart(df: pd.DataFrame,
                       start_date="2025-01-01",
                       progress_col: str | None = None) -> go.Figure:
    anchor = pd.to_datetime(start_date)

    gdf = df.copy()
    gdf["Start"]  = anchor + pd.to_timedelta(gdf["ES"] - 1, unit="D")
    gdf["Finish"] = anchor + pd.to_timedelta(gdf["EF"] - 1, unit="D")
    gdf["IsMilestone"] = gdf["Duration"].astype(float).lt(0.01)   # ← FIX

    fig = go.Figure()

    # 1. Bars & milestones
    for _, r in gdf.iterrows():
        if r["IsMilestone"]:
            fig.add_trace(
                go.Scatter(
                    x=[r["Start"]],
                    y=[r["Task Description"]],
                    mode="markers",
                    marker=dict(symbol="diamond-wide", size=14,
                                color="red" if r["On Critical Path?"] == "Yes" else "#3F51B5"),
                    name=r["Task ID"],
                    hovertemplate=f"{r['Task ID']} – {r['Task Description']}<extra></extra>",
                    showlegend=False,
                )
            )
            continue

        base_color = "#3F51B5"
        outline    = "red" if r["On Critical Path?"] == "Yes" else base_color

        fig.add_trace(
            go.Bar(
                x=[r["Duration"]],
                y=[r["Task Description"]],
                base=r["Start"],
                orientation="h",
                marker=dict(color=base_color, line=dict(color=outline, width=1.8)),
                hovertemplate=(
                    f"<b>{r['Task ID']} – {r['Task Description']}</b><br>"
                    f"Start: {r['Start']:%Y-%m-%d}<br>"
                    f"Finish: {r['Finish']:%Y-%m-%d}<br>"
                    f"Duration: {r['Duration']} d<br>"
                    f"Float: {r['Float']}<extra></extra>"
                ),
                showlegend=False,
            )
        )

        if progress_col and progress_col in gdf.columns and r[progress_col] > 0:
            pct = min(100, max(0, r[progress_col])) / 100
            fig.add_trace(
                go.Bar(
                    x=[r["Duration"] * pct],
                    y=[r["Task Description"]],
                    base=r["Start"],
                    orientation="h",
                    marker=dict(color="#9E9E9E"),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

    # 2. FS arrows
    annotations = []
    for _, r in gdf.iterrows():
        succ_start = r["Start"]
        succ_y     = r["Task Description"]
        for p in str(r["Predecessors"]).split(","):
            p = p.strip()
            if not p or p not in gdf["Task ID"].values:
                continue
            pred = gdf[gdf["Task ID"] == p].iloc[0]
            color = "red" if (pred["On Critical Path?"] == "Yes"
                              and r["On Critical Path?"] == "Yes") else "#666"
            annotations.append(
                dict(
                    x=succ_start, y=succ_y,
                    ax=pred["Finish"], ay=pred["Task Description"],
                    xref="x", yref="y", axref="x", ayref="y",
                    showarrow=True, arrowhead=3, arrowsize=1, arrowwidth=2,
                    arrowcolor=color, opacity=0.8,
                )
            )

    # 3. Layout
    fig.update_layout(
        annotations=annotations,
        barmode="overlay",
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
