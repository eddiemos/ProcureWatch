from __future__ import annotations

import networkx as nx
import pandas as pd


def build_buyer_supplier_graph(procurement_df: pd.DataFrame) -> nx.Graph:
    graph = nx.Graph()
    if procurement_df.empty:
        return graph

    for row in procurement_df.to_dict(orient="records"):
        buyer = row.get("buyer_id") or row.get("buyer_name") or "Unknown buyer"
        supplier = row.get("supplier_id") or row.get("supplier_name") or "Unknown supplier"
        value = float(row.get("award_value") or row.get("contract_value") or 0.0)
        if buyer not in graph:
            graph.add_node(buyer, kind="buyer")
        if supplier not in graph:
            graph.add_node(supplier, kind="supplier")
        if graph.has_edge(buyer, supplier):
            graph[buyer][supplier]["weight"] += 1
            graph[buyer][supplier]["total_value"] += value
        else:
            graph.add_edge(buyer, supplier, weight=1, total_value=value)
    return graph


def summarise_network(graph: nx.Graph) -> dict:
    if graph.number_of_nodes() == 0:
        return {"nodes": 0, "edges": 0, "top_connections": []}

    top_connections = sorted(
        (
            {"source": u, "target": v, "weight": d.get("weight", 0), "total_value": d.get("total_value", 0.0)}
            for u, v, d in graph.edges(data=True)
        ),
        key=lambda item: item["weight"],
        reverse=True,
    )[:10]
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "top_connections": top_connections,
    }
