"""
Activity-on-Node CPM network – clear red critical path

• Critical nodes = red, others = blue, START/END = black
• Critical edges = red, others = grey
• Arrowheads on all edges
• x coordinate = Early Start  → straight time flow
• Non-critical branches drop in tiers below critical rail
"""

import networkx as nx
import pandas as pd
import plotly.graph_objects as go


# ------------------------------------------------------------------ #
#  Helpers                                                           #
# ------------------------------------------------------------------ #
def _build_graph(df: pd.DataFrame) -> nx.DiGraph:
    g = nx.DiGraph()
    for _, r in df.iterrows():
        g.add_node(r["Task ID"], label=r["Task Description"])
        for p in str(r["Predecessors"]).split(","):
            p = p.strip()
            if p:
                g.add_edge(p, r["Task ID"])
    return g


def _positions(df: pd.DataFrame,
               x_gap: float = 1.5,
               crit_y: float = 0,
               noncrit_gap: float = 1.6) -> dict:
    """Critical nodes stay on y=0; others stacked downward."""
    crit = set(df.loc[df["On Critical Path?"] == "Yes", "Task ID"])
    lanes_end: list[float] = []
    pos = {}

    df = df.sort_values(["ES", "Task ID"])
    for _, r in df.iterrows():
        x = r["ES"] * x_gap
        dur = max(1, r["Duration"]) * x_gap
        if r["Task ID"] in crit:
            y = crit_y
        else:
            # first lane whose rightmost x < this x
            for lane, rightmost in enumerate(lanes_end):
                if rightmost < x:
                    break
            else:
                lane = len(lanes_end)
                lanes_end.append(0)
            lanes_end[lane] = x + dur
            y = -(lane + 1) * noncrit_gap
        pos[r["Task ID"]] = (x, y)
    return pos


def _add_dummy_nodes(df: pd.DataFrame) -> pd.DataFrame:
    """Insert START / END rows to get neat book-ends."""
    first_es = df["ES"].min()
    last_ef  = df["EF"].max()

    start = {
        "Task ID": "START", "Task Description": "Start", "Predecessors": "",
        "Duration": 0, "ES": first_es - 1, "EF": first_es - 1,
        "LS": first_es - 1, "LF": first_es - 1,
        "Float": 0, "On Critical Path?": "Yes",
    }
    end = start | {
        "Task ID": "END", "Task Description": "End",
        "ES": last_ef + 1, "EF": last_ef + 1,
    }
    df2 = pd.concat([pd.DataFrame([start]), df, pd.DataFrame([end])],
                    ignore_index=True)
    end_preds = ",".join(df.loc[df["EF"] == last_ef, "Task ID"])
    df2.loc[df2["Task ID"] == "END", "Predecessors"] = end_preds
    return df2


# ------------------------------------------------------------------ #
#  Public function                                                   #
# ------------------------------------------------------------------ #
def create_network_figure(df: pd.DataFrame) -> go.Figure:
    df_net = _add_dummy_nodes(df)
    g      = _build_graph(df_net)
    pos    = _positions(df_net)
    crit   = set(df_net.loc[df_net["On Critical Path?"] == "Yes", "Task ID"])

    # Nodes ----------------------------------------------------------
    node_trace = go.Scatter(
        x=[pos[n][0] for n in g.nodes()],
        y=[pos[n][1] for n in g.nodes()],
        mode="markers+text",
        text=list(g.nodes()),
        textposition="bottom center",
        marker=dict(
            size=12,
            color=[
                "#000000" if n in ("START", "END")
                else ("red" if n in crit else "#1f77b4")
                for n in g.nodes()
            ],
        ),
        hovertext=[g.nodes[n]["label"] for n in g.nodes()],
        hoverinfo="text",
    )

    # Edges (each as its own scatter so colour is per-edge) ----------
    edge_traces = []
    annotations = []
    for u, v in g.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        is_crit = u in crit and v in crit
        colour  = "red" if is_crit else "#888"
        width   = 3 if is_crit else 1

        edge_traces.append(
            go.Scatter(
                x=[x0, x1],
                y=[y0, y1],
                mode="lines",
                line=dict(color=colour, width=width),
                hoverinfo="none",
                showlegend=False,
            )
        )
        # arrow head
        annotations.append(
            dict(
                x=x1, y=y1, ax=x0, ay=y0,
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True, arrowhead=2, arrowsize=1,
                arrowwidth=width, arrowcolor=colour,
            )
        )

    # Assemble figure
    fig = go.Figure(edge_traces + [node_trace])
    fig.update_layout(
        title="CPM Network Diagram",
        annotations=annotations,
        margin=dict(l=20, r=20, t=40, b=40),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig
