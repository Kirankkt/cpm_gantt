# network_diagram.py
import networkx as nx
import pandas as pd
import plotly.graph_objects as go

def build_network(df: pd.DataFrame) -> nx.DiGraph:
    """Return a directed graph from the CPM DataFrame."""
    g = nx.DiGraph()
    for _, row in df.iterrows():
        g.add_node(row["Task ID"], label=row["Task Description"])
        preds = [p.strip() for p in str(row["Predecessors"]).split(",") if p.strip()]
        for p in preds:
            g.add_edge(p, row["Task ID"])
    return g

def create_network_figure(df: pd.DataFrame) -> go.Figure:
    """Convert the NetworkX graph into an interactive Plotly figure."""
    g = build_network(df)

    # simple spring-layout for clarity
    pos = nx.spring_layout(g, seed=42)

    edge_x = []
    edge_y = []
    for u, v in g.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(width=1, color="#888"),
        hoverinfo="none"
    )

    node_x = []
    node_y = []
    hover_text = []
    for node in g.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        hover_text.append(f"{node}: {g.nodes[node]['label']}")

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=list(g.nodes()),
        textposition="bottom center",
        marker=dict(size=10, color="#0047AB"),
        hovertext=hover_text,
        hoverinfo="text"
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        showlegend=False,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
        title="CPM Network Diagram"
    )
    return fig
