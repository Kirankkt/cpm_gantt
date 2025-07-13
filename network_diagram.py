# network_diagram.py  – v2 (remove pygraphviz requirement)
import networkx as nx
import pandas as pd
import plotly.graph_objects as go

def build_network(df: pd.DataFrame) -> nx.DiGraph:
    g = nx.DiGraph()
    for _, r in df.iterrows():
        g.add_node(r["Task ID"], label=r["Task Description"])
        for p in str(r["Predecessors"]).split(","):
            p = p.strip()
            if p:
                g.add_edge(p, r["Task ID"])
    return g

def layered_positions(df: pd.DataFrame, x_gap=1.3, y_gap=1.0):
    """
    x  = Early Start day (so time flows left→right)
    y  = vertical rank to keep nodes from overlapping.
    """
    df_sorted = df.sort_values(["ES", "Task ID"])
    rows = []
    lane_tracker = []        # keeps latest x occupied in each "lane"

    for _, row in df_sorted.iterrows():
        x = row["ES"]
        lane = 0
        # find first lane that is free at this x
        while lane < len(lane_tracker) and lane_tracker[lane] >= x:
            lane += 1
        if lane == len(lane_tracker):
            lane_tracker.append(x + row["Duration"])
        else:
            lane_tracker[lane] = x + row["Duration"]
        rows.append((row["Task ID"], x * x_gap, -lane * y_gap))
    return {task: (x, y) for task, x, y in rows}

def create_network_figure(df: pd.DataFrame) -> go.Figure:
    g = build_network(df)
    pos = layered_positions(df)

    edge_x, edge_y = [], []
    for u, v in g.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(width=1, color="#888"),
        hoverinfo="none",
    )

    node_x, node_y, hover = [], [], []
    for node in g.nodes():
        x, y = pos[node]
        node_x.append(x); node_y.append(y)
        hover.append(f"{node}: {g.nodes[node]['label']}")

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=list(g.nodes()),
        textposition="bottom center",
        marker=dict(size=10, color="#0047AB"),
        hovertext=hover,
        hoverinfo="text",
    )

    fig = go.Figure([edge_trace, node_trace])
    fig.update_layout(
        title="CPM Network Diagram",
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=40),
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
    )
    return fig
