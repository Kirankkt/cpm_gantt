"""
Light-weight CPM network diagram (no pygraphviz needed)

• x = Early-Start layer  → clear left→right time flow
• y = automatic “lane” assignment to avoid overlap
• Critical-path edges drawn in red
"""

import networkx as nx
import pandas as pd
import plotly.graph_objects as go


# ------------------------------------------------------------------ #
#  1. Helpers                                                        #
# ------------------------------------------------------------------ #
def build_network(df: pd.DataFrame) -> nx.DiGraph:
    g = nx.DiGraph()
    for _, r in df.iterrows():
        g.add_node(r["Task ID"], label=r["Task Description"])
        for p in str(r["Predecessors"]).split(","):
            p = p.strip()
            if p:
                g.add_edge(p, r["Task ID"])
    return g


def layered_positions(
    df: pd.DataFrame,
    x_gap: float = 1.4,
    y_gap: float = 1.0,
) -> dict[str, tuple[float, float]]:
    """
    Deterministic left→right layout:
      x = ES * x_gap
      y = first free lane (stacked) * -y_gap
    """
    df = df.sort_values(["ES", "Task ID"])
    lane_rightmost_x: list[float] = []
    pos = {}

    for _, r in df.iterrows():
        x = r["ES"] * x_gap
        dur_width = r["Duration"] * x_gap
        # find topmost lane that is free at this x
        for lane, right_x in enumerate(lane_rightmost_x):
            if right_x < x:
                break
        else:
            lane = len(lane_rightmost_x)
            lane_rightmost_x.append(0)

        lane_rightmost_x[lane] = x + dur_width
        # slight jitter to reduce perfectly straight overlaps
        jitter = (hash(r["Task ID"]) % 7) * 0.07
        y = -(lane * y_gap + jitter)
        pos[r["Task ID"]] = (x, y)

    return pos


# ------------------------------------------------------------------ #
#  2. Public figure builder                                          #
# ------------------------------------------------------------------ #
def create_network_figure(df: pd.DataFrame) -> go.Figure:
    g   = build_network(df)
    pos = layered_positions(df)

    # Critical-path set
    crit_tasks = set(df.loc[df["On Critical Path?"] == "Yes", "Task ID"])

    # Edges
    edge_x, edge_y, edge_col, edge_w = [], [], [], []
    for u, v in g.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
        is_crit = u in crit_tasks and v in crit_tasks
        edge_col.append("red" if is_crit else "#888")
        edge_w.append(3 if is_crit else 1)

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(color="#888", width=1),
        hoverinfo="none",
    )
    # Width & color arrays can't be set per-segment in one trace,
    # but redrawing critical edges in an overlay trace works:
    if any(c == "red" for c in edge_col):
        crit_x = [x for x, c in zip(edge_x, edge_col) if c == "red"] + [None]
        crit_y = [y for y, c in zip(edge_y, edge_col) if c == "red"] + [None]
        crit_trace = go.Scatter(
            x=crit_x, y=crit_y,
            mode="lines",
            line=dict(color="red", width=3),
            hoverinfo="none",
        )
    else:
        crit_trace = None

    # Nodes
    node_x, node_y, hover = [], [], []
    for n in g.nodes():
        x, y = pos[n]
        node_x.append(x)
        node_y.append(y)
        hover.append(f"{n}: {g.nodes[n]['label']}")

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=list(g.nodes()),
        textposition="bottom center",
        marker=dict(size=10, color="#0047AB"),
        hovertext=hover,
        hoverinfo="text",
    )

    data = [edge_trace, node_trace]
    if crit_trace:
        data.insert(1, crit_trace)

    fig = go.Figure(data=data)
    fig.update_layout(
        title="CPM Network Diagram",
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=40),
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
    )
    return fig
