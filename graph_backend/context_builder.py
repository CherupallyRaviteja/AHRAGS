from __future__ import annotations
import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


def build_context(ranked_results: List[Dict[str, Any]]) -> Tuple[List[str], str, Dict[str, int], List[Dict[str, Any]]]:
    """
    Args:
        ranked_results: output of hybrid_ranker.merge() — already sorted by score.

    Returns:
        (contexts, graph_context_text, sources, provenance)
    """
    contexts: List[str] = []
    sources: Dict[str, int] = {}
    provenance: List[Dict[str, Any]] = []
    path_lines: List[str] = []
    seen_paths = set()

    for result in ranked_results:
        content = result.get("content") or ""
        if content:
            contexts.append(content)

        source = result.get("source")
        page = result.get("page")
        if source is not None:
            sources[source] = page

        prov = dict(result.get("provenance", {}))
        prov.update({"source": source, "page": page, "final_score": result.get("score", 0.0)})
        provenance.append(prov)

        prov = result.get("provenance", {})

        path = prov.get("graph_path") or []
        relationship_types = prov.get("relationship_types") or []

        if len(path) > 1:
            if relationship_types and len(relationship_types) == len(path) - 1:
                parts = []

                for i, relationship in enumerate(relationship_types):
                    parts.append(path[i])
                    parts.append(f"--{relationship}-->")

                parts.append(path[-1])

                path_str = " ".join(parts)
            else:
                path_str = " -> ".join(path)

            if path_str not in seen_paths:
                seen_paths.add(path_str)
                path_lines.append(path_str)

    graph_context_text = ""
    if path_lines:
        graph_context_text = (
            "Related knowledge graph connections (for additional context, "
            "not a substitute for the passages above):\n" + "\n".join(f"- {p}" for p in path_lines)
        )

    logger.debug(
        "Context built: %d chunks, %d graph paths, %d sources",
        len(contexts), len(path_lines), len(sources),
    )
    return contexts, graph_context_text, sources, provenance


if __name__ == "__main__":
    demo = [{
        "content": "FastAPI is a web framework.",
        "source": "doc.pdf", "page": 1, "score": 0.91,
        "provenance": {"graph_path": ["FastAPI", "uses", "Pydantic"], "retrieved_because": ["vector similarity 0.90"]},
    }]
    print(build_context(demo))
