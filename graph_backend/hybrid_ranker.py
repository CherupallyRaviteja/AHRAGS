from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple
import config

logger = logging.getLogger(__name__)


def _new_entry(content: str, source: str, page: int) -> Dict[str, Any]:
    return {
        "content": content,
        "source": source,
        "page": page,
        "vector_score": 0.0,
        "keyword_score": 0.0,
        "graph_distance_score": 0.0,
        "relationship_relevance": 0.0,
        "node_importance": 0.0,
        "entity_frequency": 0,
        "score": 0.0,
        "provenance": {},
    }


def _make_key(source: Any, page: Any, content: str) -> Tuple[Any, Any, str]:
    return (source, page, (content or "").strip())


def _explain(entry: Dict[str, Any]) -> List[str]:
    """Human-readable reasons this chunk was retrieved."""
    reasons = []

    if entry["vector_score"] > 0:
        reasons.append(
            f"vector similarity {entry['vector_score']:.2f}"
        )

    if entry["keyword_score"] > 0:
        reasons.append("keyword match")

    prov = entry["provenance"]

    # Only graph-retrieved chunks should show graph information.
    if prov.get("retrieval_type") == "graph":

        if prov.get("hop_distance") is not None:
            reasons.append(
                f"graph hop distance {prov['hop_distance']}"
            )

        if prov.get("matched_entities"):
            reasons.append(
                f"entity match: {', '.join(prov['matched_entities'])}"
            )

        if prov.get("graph_path"):
            reasons.append(
                "graph path: " + " -> ".join(prov["graph_path"])
            )

    if not reasons:
        reasons.append("unscored")

    return reasons


def merge(
    vector_rows: Sequence[Sequence[Any]],
    graph_results: Sequence[Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None,
    top_k: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Merge vector+keyword results (from RAGIndex.retrieve) and graph results
    (from GraphRetriever.search) into one ranked, explainable list.

    Never raises: malformed rows are skipped and logged so a merge failure
    degrades gracefully instead of blocking the response.
    """
    weights = weights or config.HYBRID_WEIGHTS
    combined: Dict[Tuple[Any, Any, str], Dict[str, Any]] = {}

    text_scores = [row[4] for row in vector_rows if len(row) > 4 and row[4] is not None]
    max_text_score = max(text_scores) if text_scores else 1.0
    max_text_score = max_text_score or 1.0

    for row in vector_rows:
        try:
            content, source, page, vec_score, text_score = row[0], row[1], row[2], row[3], row[4]
        except (IndexError, ValueError) as exc:
            logger.warning("Skipping malformed vector result row %r: %s", row, exc)
            continue

        key = _make_key(source, page, content)
        entry = combined.setdefault(key, _new_entry(content, source, page))
        entry["vector_score"] = float(vec_score or 0.0)
        entry["keyword_score"] = float(text_score or 0.0) / max_text_score
        entry["provenance"]["vector_score"] = float(vec_score or 0.0)
        entry["provenance"]["keyword_score_raw"] = float(text_score or 0.0)
        entry["provenance"]["retrieval_type"] = "vector"
        entry["provenance"]["hop_distance"] = None
        entry["provenance"]["matched_entities"] = []

    for gr in graph_results:
        try:
            key = _make_key(
                gr["source"],
                gr["page"],
                gr["content"],
            )
        except KeyError as exc:
            logger.warning(
                "Skipping malformed graph result %r: %s",
                gr,
                exc,
            )
            continue

        entry = combined.setdefault(
            key,
            _new_entry(
                gr["content"],
                gr["source"],
                gr["page"],
            ),
        )

        retrieval_type = gr.get("retrieval_type", "graph")

        # ------------------------------------------------------------
        # Vector result
        # ------------------------------------------------------------
        if retrieval_type == "vector":
            score = float(gr.get("score") or 0.0)

            entry["vector_score"] = max(
                entry["vector_score"],
                score,
            )

            entry["provenance"]["vector_score"] = score

            continue

        # ------------------------------------------------------------
        # Graph result
        # ------------------------------------------------------------
        if retrieval_type == "graph":

            hop = gr.get(
                "hop_distance",
                config.GRAPH_MAX_HOPS + 1,
            )

            try:
                hop = int(hop)
            except (TypeError, ValueError):
                hop = config.GRAPH_MAX_HOPS + 1

            # --------------------------------------------------------
            # Graph distance
            # --------------------------------------------------------
            graph_distance_score = 1.0 / (1 + hop)

            entry["graph_distance_score"] = max(
                entry["graph_distance_score"],
                graph_distance_score,
            )

            # --------------------------------------------------------
            # Relationship relevance
            # --------------------------------------------------------
            relationship_types = gr.get(
                "relationship_types",
                [],
            )

            if hop == 0:
                relationship_score = 1.0
            elif relationship_types:
                relationship_score = 0.75
            else:
                relationship_score = 0.5

            entry["relationship_relevance"] = max(
                entry["relationship_relevance"],
                relationship_score,
            )

            # --------------------------------------------------------
            # Entity frequency
            # --------------------------------------------------------
            matched_entity = gr.get("matched_entity")

            if matched_entity:
                entry["entity_frequency"] += 1

            # --------------------------------------------------------
            # Node importance
            # --------------------------------------------------------
            node_importance = float(
                gr.get("node_importance") or 0.0
            )

            entry["node_importance"] = max(
                entry["node_importance"],
                node_importance,
            )

            # --------------------------------------------------------
            # Provenance
            # --------------------------------------------------------
            entry["provenance"]["hop_distance"] = hop

            entry["provenance"]["retrieval_type"] = "graph"

            entry["provenance"]["starting_chunk_id"] = (
                gr.get("starting_chunk_id")
            )

            entry["provenance"]["relationship_types"] = (
                relationship_types
            )

            if matched_entity:
                entry["provenance"].setdefault(
                    "matched_entities",
                    [],
                )

                if matched_entity not in entry["provenance"]["matched_entities"]:
                    entry["provenance"]["matched_entities"].append(
                        matched_entity
                    )

            # Preserve graph path if available
            graph_path = gr.get("graph_path") or gr.get("path")

            if graph_path:
                entry["provenance"]["graph_path"] = graph_path

    for entry in combined.values():
        entity_freq_norm = min(entry["entity_frequency"] / 5.0, 1.0)
        entry["score"] = (
            weights.get("vector", 0) * entry["vector_score"]
            + weights.get("keyword", 0) * entry["keyword_score"]
            + weights.get("graph_distance", 0) * entry["graph_distance_score"]
            + weights.get("relationship_relevance", 0) * entry["relationship_relevance"]
            + weights.get("node_importance", 0) * entry["node_importance"]
            + weights.get("entity_frequency", 0) * entity_freq_norm
        )
        entry["provenance"]["retrieved_because"] = _explain(entry)

    ranked = sorted(combined.values(), key=lambda e: e["score"], reverse=True)
    if top_k:
        ranked = ranked[:top_k]

    logger.debug("Hybrid ranking merged %d vector rows + %d graph results into %d results",
                 len(vector_rows), len(graph_results), len(ranked))
    return ranked


if __name__ == "__main__":
    demo_vector = [("FastAPI is a web framework.", "doc.pdf", 1, 0.9, 0.4)]
    demo_graph = [{
        "content": "FastAPI is a web framework.", "source": "doc.pdf", "page": 1,
        "hop_distance": 0, "matched_entities": ["FastAPI"], "path": ["FastAPI"],
        "node_importance": 0.8,
    }]
    for r in merge(demo_vector, demo_graph):
        print(r["score"], r["provenance"]["retrieved_because"])
