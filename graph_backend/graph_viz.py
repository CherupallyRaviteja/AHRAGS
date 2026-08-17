from __future__ import annotations
import logging
from typing import Optional
import config
from graph_db import GraphStore, graph_store as default_graph_store

logger = logging.getLogger(__name__)

try:
    from pyvis.network import Network
    _PYVIS_AVAILABLE = True
except ImportError:
    Network = None  # type: ignore
    _PYVIS_AVAILABLE = False


_TYPE_COLORS = {
    "Entity": "#4C9AFF",
    "Chunk": "#FFAB00",
}


def build_subgraph_html(
    entity_name: Optional[str] = None,
    max_nodes: int = 100,
    store: Optional[GraphStore] = None,
) -> str:
    """
    Build a self-contained HTML page visualizing a subgraph.

    If `entity_name` is given, renders the neighborhood (up to
    config.GRAPH_MAX_HOPS) around matching entities. Otherwise renders a
    sample of the whole graph, capped at `max_nodes`.

    Returns HTML as a string. Returns a small HTML error page (not an
    exception) if PyVis isn't installed or the graph store is unavailable,
    so the debug endpoint always renders something.
    """
    store = store or default_graph_store

    if not _PYVIS_AVAILABLE:
        return _error_html("PyVis is not installed. Run `pip install pyvis` to enable this view.")
    if not store.available:
        return _error_html("Graph store is unavailable — Neo4j may be offline.")

    net = Network(height="750px", width="100%", directed=True, notebook=False, cdn_resources="in_line")

    try:
        nodes, edges = _fetch_subgraph(store, entity_name, max_nodes)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to fetch subgraph for visualization: %s", exc)
        return _error_html(f"Failed to load graph data: {exc}")

    if not nodes:
        return _error_html("No matching graph data found.")

    for node in nodes:
        label = node.get("name") or node.get("content", "")[:40] or node["id"]
        color = _TYPE_COLORS.get(node["label"], "#8993A4")
        title = node.get("type") or node["label"]
        net.add_node(node["id"], label=str(label)[:40], color=color, title=str(title))

    for edge in edges:
        net.add_edge(edge["source"], edge["target"], label=edge.get("type", ""))

    try:
        return net.generate_html()
    except Exception as exc:  # noqa: BLE001
        logger.error("PyVis HTML generation failed: %s", exc)
        return _error_html(f"Visualization rendering failed: {exc}")


def _fetch_subgraph(store: GraphStore, entity_name: Optional[str], max_nodes: int):
    nodes = {}
    edges = []

    if entity_name:
        rows = store.run_read(
            f"""
            MATCH (start:Entity) WHERE toLower(start.name) CONTAINS toLower($name)
            MATCH path = (start)-[*0..{config.GRAPH_MAX_HOPS}]-(n)
            UNWIND nodes(path) AS node
            WITH DISTINCT node LIMIT $limit
            OPTIONAL MATCH (node)-[r]->(m) WHERE m IN [x IN nodes(node) | x]
            RETURN node
            """,
            {"name": entity_name, "limit": max_nodes},
        )
        node_rows = [r["node"] for r in rows if r.get("node")]
    else:
        node_rows = [r["n"] for r in store.run_read("MATCH (n) RETURN n LIMIT $limit", {"limit": max_nodes})]

    node_ids = []
    for n in node_rows:
        node_id = n.get("id")
        if not node_id or node_id in nodes:
            continue
        label = "Entity" if "type" in n and "content" not in n else "Chunk"
        nodes[node_id] = {"id": node_id, "label": label, **n}
        node_ids.append(node_id)

    if node_ids:
        rel_rows = store.run_read(
            """
            MATCH (a)-[r]->(b)
            WHERE a.id IN $ids AND b.id IN $ids
            RETURN a.id AS source, b.id AS target, type(r) AS type
            LIMIT 500
            """,
            {"ids": node_ids},
        )
        edges = rel_rows

    return list(nodes.values()), edges


def _error_html(message: str) -> str:
    return f"<html><body><h3>Graph visualization unavailable</h3><p>{message}</p></body></html>"


if __name__ == "__main__":
    html = build_subgraph_html()
    print(html[:200], "...")
