"""
Activity-on-Node (AoN) CPM network – clean left→right layout

• Adds dummy “Start” and “End” nodes
• x-position  = Early Start * x_gap  (so it flows in time order)
• y-position  = lane number (top-down)  – no zig-zag
• Critical-path edges drawn bold red
"""

import networkx as nx
import pandas as pd
import plotly.graph_objects as go


def _add_start_end(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with START/END rows inserted."""
    df2 = df.copy()
    first_es = df2["ES"].min()
    last_ef  = df2["EF"].max()

    start_row = {
        "Task ID":      "START",
        "Task Description": "Start",
        "Predecessors": "",
        "Duration":     0,
        "ES":           first_es - 1,
        "EF":           first_es - 1,
        "LS":           first_es - 1,
        "LF":           first_es - 1,
        "Float":        0,
        "On Critical Path?": "Yes",
    }
    end_row = start_row | {
        "Task ID":      "END",
        "Task Description": "End",
        "ES":           last_ef + 1,
        "EF":           last_ef + 1,
    }
    df2 = pd.concat([pd.DataFrame([start_row]), df2, pd.DataFrame([end_row])],
                    ignore_index=True)
    # wire predecessors
    df2.loc[df2["Task ID"] == "START", "Predecessors"] = ""
    df2.loc[df2["Task ID"] == "END",   "Predecessors"] = ",".join(
        df.query("EF == @last_ef")["Task ID"]
    )
    return df2


def _lane_positions(df: pd.DataFrame,
                    x_gap: float = 1.5,
                    crit_y: float = 0,
                    noncrit_y_gap: float = 1.2):
    """
    • Critical tasks live on y = 0 (straight line)
    • Non-critical tasks stack downward in tidy tiers
    """
    crit_set = set(df.loc[df["On Critical Path?"] == "Yes", "Task ID"])
    lane_right: list[float] = []
    pos = {}

    df = df.sort_values(["ES", "Task ID"])
    for _, r in df.iterrows():
        x = r["ES"] * x_gap
        duration = max(1, r["Duration"]) * x_gap

        if r["Task ID"] in crit_set:          # ------- critical lane (y=0)
            y = crit_y
        else:                                 # ------- find next free lane
            for lane, right_x in enumerate(lane_right):
                if right_x < x:
                    break
            else:
                lane = len(lane_right)
                lane_right.append(0)
            lane_right[lane] = x + duration
            y = -(lane + 1) * noncrit_y_gap   # start at −1 * gap

        pos[r["Task ID"]] = (x, y)
    return pos



def _build_graph(df: pd.DataFrame) -> nx.DiGraph:
    g = nx.DiGraph()
    for _, r in df.iterrows():
        g.add_node(r["Task ID"], label=r["Task Description"])
        for p in str(r["Predecessors"]).split(","):
            p = p.strip()
            if p:
                g.add_edge(p, r["Task ID"])
    return g


def create_network_figure(df: pd.DataFrame) -> go.Figure:
    df_net = _add_start_end(df)
    g      = _build_graph(df_net)
    pos    = _lane_positions(df_net)

    crit   = set(df_net.loc[df_net["On Critical Path?"] == "Yes", "Task ID"])

    # edges
    edge_x, edge_y, edge_c, edge_w = [], [], [], []
    for u, v in g.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
        is_crit = u in crit and v in crit
        edge_c.append("red" if is_crit else "#999")
        edge_w.append(3 if is_crit else 1)

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=1, color="#999"),
        hoverinfo="none",
    )
    if any(c == "red" for c in edge_c):
        crit_x = [x for x, c in zip(edge_x, edge_c) if c == "red"] + [None]
        crit_y = [y for y, c in zip(edge_y, edge_c) if c == "red"] + [None]
        crit_trace = go.Scatter(
            x=crit_x, y=crit_y,
            mode="lines",
            line=dict(width=3, color="red"),
            hoverinfo="none",
        )
    else:
        crit_trace = None

    # nodes
    node_x, node_y, hover, colors = [], [], [], []
    for n in g.nodes():
        x, y = pos[n]
        node_x.append(x); node_y.append(y)
        hover.append(g.nodes[n]["label"])
        colors.append("#000000" if n in ("START", "END") else "#0047AB")

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=list(g.nodes()),
        textposition="bottom center",
        marker=dict(size=12, color=colors),
        hovertext=hover,
        hoverinfo="text",
    )

    data = [edge_trace, node_trace] if crit_trace is None else [edge_trace, crit_trace, node_trace]

    fig = go.Figure(data)
    fig.update_layout(
        title="CPM Network Diagram",
        margin=dict(l=20, r=20, t=40, b=40),
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig
